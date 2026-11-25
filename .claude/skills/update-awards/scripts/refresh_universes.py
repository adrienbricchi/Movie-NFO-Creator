#
# movie NFO creator
# Copyright (C) 2025 Adrien BRICCHI
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-only
#

import argparse
import datetime
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import requests

from refresh_awards import IMDB_URL, USER_AGENT, WIKIDATA_SPARQL_URL, read_rows, unmapped_csv_files, write_rows

TAG_LISTS_DIR = Path(__file__).resolve().parents[4] / 'movie_nfo_creator' / 'tag_lists'
UNIVERSES_DIR = TAG_LISTS_DIR / 'universes'
FETCHED_DATES_PATH = Path(__file__).resolve().parent / 'universe_fetched_dates.json'

QUERY_TEMPLATE = '''
SELECT ?film ?imdb ?title ?labelFr ?labelEn ?released WHERE {{
  VALUES ?universe {{ {items} }}
  ?film (wdt:P179|wdt:P1434|wdt:P8345|wdt:P361)/((wdt:P179|wdt:P361)?) ?universe .
  ?film wdt:P31 ?type .
  ?type wdt:P279* wd:Q11424 .
  FILTER NOT EXISTS {{ ?type wdt:P279* wd:Q24862 . }}
  ?film wdt:P345 ?imdb .
  FILTER(STRSTARTS(?imdb, "tt"))
  OPTIONAL {{ ?film wdt:P1476 ?title . }}
  OPTIONAL {{ ?film rdfs:label ?labelFr . FILTER(LANG(?labelFr) = "fr") }}
  OPTIONAL {{ ?film rdfs:label ?labelEn . FILTER(LANG(?labelEn) = "en") }}
  OPTIONAL {{ ?film wdt:P577 ?released . }}
}}
'''


@dataclass(frozen=True)
class UniverseSource:
    filename: str
    wikidata_items: tuple = ()
    closed: bool = False
    wikidata_false_positives: tuple = ()
    folder: str = 'universes'


UNIVERSE_SOURCES = [
    UniverseSource('alien.csv', ('Q1990792', 'Q2967318')),
    UniverseSource('antoine_doinel.csv', closed=True),
    UniverseSource('apocalypse_trilogy.csv', closed=True),
    UniverseSource('askewniverse.csv', ('Q1140919',)),
    UniverseSource('asterix.csv', ('Q2868647', 'Q97010658')),
    UniverseSource('batman_burtonverse.csv', closed=True),
    UniverseSource('blade.csv', ('Q4923681',)),
    UniverseSource('bourne.csv', ('Q868683',)),
    UniverseSource('candyman.csv', ('Q85750454',)),
    UniverseSource('cars.csv', ('Q5046850', 'Q62846448', 'Q58510929', 'Q123699295')),
    UniverseSource('chucky.csv', ('Q2265493',)),
    UniverseSource('cloverfield.csv', ('Q25136301',)),
    UniverseSource('conjuring.csv', ('Q25339704',)),
    UniverseSource('cornetto.csv', closed=True),
    UniverseSource('dc_animated_standalone.csv', ('Q2405799',)),
    UniverseSource('dc_animated_tomorrowverse.csv', closed=True),
    UniverseSource('dcamu.csv', closed=True),
    UniverseSource('dcau.csv', closed=True),
    UniverseSource('dceu.csv', ('Q18281265',), closed=True),
    UniverseSource('dcu.csv', ('Q116545465',)),
    UniverseSource('department_q.csv', ('Q85756399',)),
    UniverseSource('despicable_me.csv', ('Q5264979', 'Q98114628', 'Q140478058')),
    UniverseSource('die_hard.csv', ('Q2716420',)),
    UniverseSource('disney_attractions.csv'),
    UniverseSource('dollars.csv', closed=True),
    UniverseSource('eastrail_177.csv', closed=True),
    UniverseSource('evil_dead.csv', ('Q921605',)),
    UniverseSource('exorcist.csv', ('Q7732814',)),
    UniverseSource('fast_and_furious.csv', ('Q1576873',)),
    UniverseSource('final_destination.csv', ('Q223261',)),
    UniverseSource('friday_the_13th.csv', ('Q1138878',)),
    UniverseSource('ghostbusters.csv'),
    UniverseSource('godzilla_heisei.csv', closed=True),
    UniverseSource('godzilla_millennium.csv', closed=True),
    UniverseSource('godzilla_reiwa.csv'),
    UniverseSource('godzilla_showa.csv', closed=True),
    UniverseSource('halloween.csv', ('Q1364022',)),
    UniverseSource('hammer_horror.csv', closed=True, folder='studios'),
    UniverseSource('hellraiser.csv'),
    UniverseSource('how_to_train_your_dragon.csv', ('Q98120630', 'Q136714118', 'Q3715071')),
    UniverseSource('hunger_games.csv', ('Q11885031',)),
    UniverseSource('ice_age.csv', ('Q943532', 'Q98831520')),
    UniverseSource('indiana_jones.csv', ('Q98018448',)),
    UniverseSource('james_bond.csv', ('Q26451486',)),
    UniverseSource('john_wick.csv', ('Q29554576',)),
    UniverseSource('jurassic_park.csv', ('Q17862144',)),
    UniverseSource('kingsman.csv', ('Q17018738', 'Q44099631')),
    UniverseSource('kung_fu_panda.csv', ('Q2081372',)),
    UniverseSource('mad_max.csv', ('Q3275141',)),
    UniverseSource('marseille.csv', closed=True),
    UniverseSource('matrix.csv', ('Q1210827',)),
    UniverseSource('maze_runner.csv', ('Q18611408',)),
    UniverseSource('mcu.csv', ('Q642878',)),
    UniverseSource('men_in_black.csv', ('Q3305670',)),
    UniverseSource('middle_earth.csv', ('Q190214', 'Q74331', 'Q26214973')),
    UniverseSource('millennium.csv'),
    UniverseSource('mission_impossible.csv', ('Q1356213',)),
    UniverseSource('miyagiverse.csv', ('Q3987783',)),
    UniverseSource('monsterverse.csv', ('Q21527684',)),
    UniverseSource('mortal_kombat.csv', ('Q106603131',)),
    UniverseSource('nightmare_on_elm_street.csv', ('Q617871', 'Q329434')),
    UniverseSource('oceans.csv', ('Q4463076',)),
    UniverseSource('oss_117.csv', ('Q2008180',)),
    UniverseSource('pirates_of_the_caribbean.csv', ('Q194318',)),
    UniverseSource('planet_of_the_apes.csv', ('Q731663',)),
    UniverseSource('predator.csv', ('Q2138108', 'Q2967318')),
    UniverseSource('rambo.csv', ('Q1621266',)),
    UniverseSource('resident_evil.csv', ('Q1276325',)),
    UniverseSource('rocky.csv', ('Q1078084',)),
    UniverseSource('romero_dead.csv', ('Q2652860',)),
    UniverseSource('scream.csv', ('Q388659',)),
    UniverseSource('shrek.csv', ('Q61946928', 'Q1203222')),
    UniverseSource('ssu.csv', ('Q55537283',), closed=True),
    UniverseSource('star_trek.csv', ('Q1102217',)),
    UniverseSource('star_wars.csv', ('Q462', 'Q22092344')),
    UniverseSource('superman_1978.csv', closed=True),
    UniverseSource('terminator.csv', ('Q98063049',)),
    UniverseSource('texas_chainsaw_massacre.csv', ('Q80981',)),
    UniverseSource('the_mummy.csv', ('Q3823300',)),
    UniverseSource('the_purge.csv', ('Q18393677',)),
    UniverseSource('toy_story.csv', ('Q2316015',)),
    UniverseSource('transformers.csv', ('Q2073466',)),
    UniverseSource('twilight.csv', closed=True),
    UniverseSource('underworld.csv', ('Q82332',)),
    UniverseSource('universal_monsters_classic.csv', closed=True, folder='studios'),
    UniverseSource('universal_monsters_modern.csv', folder='studios'),
    UniverseSource('vengeance.csv', closed=True),
    UniverseSource('walt_disney_animation_studios.csv', ('Q56070713',), folder='studios'),
    UniverseSource('wizarding_world.csv', ('Q216930', 'Q27922181', 'Q30739117')),
    UniverseSource('x.csv', ('Q114451788',)),
    UniverseSource('xmen.csv', ('Q2006869',), closed=True),
]


@dataclass
class UniverseFilm:
    imdb_ids: set = field(default_factory=set)
    title: Optional[str] = None
    released: Optional[str] = None

    @property
    def imdb_id(self):
        return sorted(self.imdb_ids)[0]


@dataclass
class MergeResult:
    rows: list
    added: list
    added_dates: list
    missing_from_wikidata: list
    skipped_without_date: int = 0


def build_query(source):
    return QUERY_TEMPLATE.format(items=' '.join(f'wd:{item}' for item in source.wikidata_items))


def _date(binding):
    value = binding.get('released', {}).get('value', '')
    return value[:10] if len(value) >= 10 and value[:4].isdigit() else None


def parse_sparql_response(data):
    films = {}
    for binding in data['results']['bindings']:
        film = films.setdefault(binding['film']['value'], UniverseFilm())
        film.imdb_ids.add(binding['imdb']['value'])
        film.title = film.title or next((binding[key]['value'] for key in ('title', 'labelFr', 'labelEn') if key in binding), None)
        released = _date(binding)
        if released and (film.released is None or released < film.released):
            film.released = released
    return list(films.values())


def fetch_wikidata_films(source, session=requests):
    response = session.get(
        WIKIDATA_SPARQL_URL,
        params={'query': build_query(source), 'format': 'json'},
        headers={'User-Agent': USER_AGENT, 'Accept': 'application/sparql-results+json'},
        timeout=120,
    )
    response.raise_for_status()
    return parse_sparql_response(response.json())


def merge_rows(existing_rows, wikidata_films, fetched_until, today, false_positives=()):
    existing_ids = {imdb_id for _, imdb_id in existing_rows}
    new_films = [film for film in wikidata_films if not film.imdb_ids & (existing_ids | set(false_positives))]
    skipped_without_date = sum(1 for film in new_films if film.released is None)
    new_films = [film for film in new_films if film.released is not None and fetched_until < film.released <= today]
    new_films.sort(key=lambda film: (film.released, film.title or ''))
    added = [(film.title or film.imdb_id, film.imdb_id) for film in new_films]

    wikidata_ids = set().union(*(film.imdb_ids for film in wikidata_films))
    missing = [row for row in existing_rows if row[1] not in wikidata_ids]

    return MergeResult(rows=list(existing_rows) + added, added=added, added_dates=[film.released for film in new_films],
                       missing_from_wikidata=missing, skipped_without_date=skipped_without_date)


def read_fetched_dates(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def write_fetched_dates(path, fetched_dates):
    path.write_text(json.dumps(dict(sorted(fetched_dates.items())), indent=2) + '\n', encoding='utf-8')


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Add films found on Wikidata to the local cinematic universe CSVs. Existing rows are never removed.')
    parser.add_argument('--write', action='store_true', help='write the additions to the CSV files and move universe_fetched_dates.json forward (default: dry run)')
    parser.add_argument('--show-missing', action='store_true', help='list the local rows Wikidata does not link to the universe')
    return parser.parse_args(argv)


def main(argv=None, today=None):
    args = parse_args(argv)
    today = today or datetime.date.today().isoformat()
    total_added = 0

    for filename in unmapped_csv_files(UNIVERSES_DIR, UNIVERSE_SOURCES):
        print(f"{filename}: not listed in UNIVERSE_SOURCES, skipped")

    fetched_dates = read_fetched_dates(FETCHED_DATES_PATH)

    for source in UNIVERSE_SOURCES:
        if source.closed:
            print(f"{source.filename}: closed, skipped")
            continue
        if not source.wikidata_items:
            print(f"{source.filename}: no Wikidata item, update by hand")
            continue

        csv_path = TAG_LISTS_DIR / source.folder / source.filename
        fetched_until = fetched_dates.get(source.filename, '0000-00-00')
        result = merge_rows(read_rows(csv_path), fetch_wikidata_films(source), fetched_until, today, source.wikidata_false_positives)
        total_added += len(result.added)

        print(f"{source.filename} (released after {fetched_until}): {len(result.added)} to add, {len(result.missing_from_wikidata)} local rows not on Wikidata (kept)")
        for (title, imdb_id), released in zip(result.added, result.added_dates):
            print(f"  + {released} {title} {IMDB_URL}{imdb_id}")
        if result.skipped_without_date:
            print(f"  {result.skipped_without_date} Wikidata films without any release date skipped")
        if args.show_missing:
            for title, imdb_id in result.missing_from_wikidata:
                print(f"  ? {title} {IMDB_URL}{imdb_id}")

        if args.write and result.added:
            write_rows(csv_path, result.rows)
            fetched_dates[source.filename] = max(result.added_dates)

    if args.write:
        write_fetched_dates(FETCHED_DATES_PATH, fetched_dates)

    if not args.write and total_added:
        print("Dry run, nothing written. Re-run with --write to apply.")


if __name__ == '__main__':
    main()
