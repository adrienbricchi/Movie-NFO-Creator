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
import csv
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import requests

AWARDS_DIR = Path(__file__).resolve().parents[4] / 'movie_nfo_creator' / 'awards'
FETCHED_YEARS_PATH = Path(__file__).resolve().parent / 'fetched_years.json'
WIKIDATA_SPARQL_URL = 'https://query.wikidata.org/sparql'
USER_AGENT = 'movie-nfo-creator/0.1 (award list refresh)'
IMDB_URL = 'https://www.imdb.com/title/'
CSV_HEADER = ('original_title', 'imdb_id')

QUERY_TEMPLATE = '''
SELECT ?film ?imdb ?title ?labelFr ?labelEn ?ceremony ?released WHERE {{
  ?film p:{property} ?statement .
  ?statement ps:{property} wd:{award} .
  OPTIONAL {{ ?statement pq:P585 ?ceremony . }}
  ?film wdt:P345 ?imdb .
  FILTER(STRSTARTS(?imdb, "tt"))
  {exclusion}
  OPTIONAL {{ ?film wdt:P1476 ?title . }}
  OPTIONAL {{ ?film rdfs:label ?labelFr . FILTER(LANG(?labelFr) = "fr") }}
  OPTIONAL {{ ?film rdfs:label ?labelEn . FILTER(LANG(?labelEn) = "en") }}
  OPTIONAL {{ ?film wdt:P577 ?released . }}
}}
'''
WINNER_EXCLUSION = 'FILTER NOT EXISTS {{ ?film p:P166/ps:P166 wd:{award} . }}'


@dataclass(frozen=True)
class AwardSource:
    filename: str
    wikidata_award: str
    nominees_only: bool = False
    wikidata_false_positives: tuple = ()


AWARD_SOURCES = [
    AwardSource('oscar_best_picture.csv', 'Q102427'),
    AwardSource('oscar_best_picture_nominee.csv', 'Q102427', nominees_only=True),
    AwardSource('oscar_best_international_picture.csv', 'Q105304'),
    AwardSource('oscar_best_animated_picture.csv', 'Q106800'),
    # tt0102609 is Other People's Money (1991), mixed up on Wikidata with L'Argent des autres (1978).
    AwardSource('cesar_best_picture.csv', 'Q645595', wikidata_false_positives=('tt0102609',)),
    AwardSource('palme_d_or.csv', 'Q179808'),
    AwardSource('cesar_best_picture_nominee.csv', 'Q645595', nominees_only=True),
    AwardSource('goya_best_picture.csv', 'Q1467554'),
    AwardSource('bafta_best_film.csv', 'Q139184'),
    AwardSource('golden_globe_best_drama.csv', 'Q1011509'),
    AwardSource('golden_globe_best_musical_comedy.csv', 'Q670282'),
]


@dataclass
class WikidataFilm:
    imdb_ids: set = field(default_factory=set)
    title: Optional[str] = None
    ceremony_year: Optional[int] = None
    release_year: Optional[int] = None

    @property
    def imdb_id(self):
        return sorted(self.imdb_ids)[0]

    @property
    def year(self):
        if self.ceremony_year is not None:
            return self.ceremony_year
        # Ceremonies reward the previous year's releases.
        return self.release_year + 1 if self.release_year is not None else None


@dataclass
class MergeResult:
    rows: list
    added: list
    added_years: list
    missing_from_wikidata: list
    skipped_without_year: int = 0


def build_query(source):
    if source.nominees_only:
        return QUERY_TEMPLATE.format(property='P1411', award=source.wikidata_award, exclusion=WINNER_EXCLUSION.format(award=source.wikidata_award))
    return QUERY_TEMPLATE.format(property='P166', award=source.wikidata_award, exclusion='')


def _year(binding, key):
    value = binding.get(key, {}).get('value', '')
    return int(value[:4]) if len(value) >= 4 and value[:4].isdigit() else None


def _min_year(current, candidate):
    return candidate if current is None or (candidate is not None and candidate < current) else current


def parse_sparql_response(data):
    films = {}
    for binding in data['results']['bindings']:
        film = films.setdefault(binding['film']['value'], WikidataFilm())
        film.imdb_ids.add(binding['imdb']['value'])

        title = next((binding[key]['value'] for key in ('title', 'labelFr', 'labelEn') if key in binding), None)
        film.title = film.title or title

        film.ceremony_year = _min_year(film.ceremony_year, _year(binding, 'ceremony'))
        film.release_year = _min_year(film.release_year, _year(binding, 'released'))

    return list(films.values())


def fetch_wikidata_films(source, session=requests):
    response = session.get(
        WIKIDATA_SPARQL_URL,
        params={'query': build_query(source), 'format': 'json'},
        headers={'User-Agent': USER_AGENT, 'Accept': 'application/sparql-results+json'},
        timeout=60,
    )
    response.raise_for_status()
    return parse_sparql_response(response.json())


def merge_rows(existing_rows, wikidata_films, false_positives=(), fetched_until=None):
    existing_ids = {imdb_id for _, imdb_id in existing_rows}
    new_films = [film for film in wikidata_films if not film.imdb_ids & (existing_ids | set(false_positives))]
    skipped_without_year = 0
    if fetched_until is not None:
        skipped_without_year = sum(1 for film in new_films if film.year is None)
        new_films = [film for film in new_films if film.year is not None and film.year > fetched_until]
    new_films.sort(key=lambda film: (film.year or 9999, film.title or ''))
    added = [(film.title or film.imdb_id, film.imdb_id) for film in new_films]

    wikidata_ids = set().union(*(film.imdb_ids for film in wikidata_films))
    missing = [row for row in existing_rows if row[1] not in wikidata_ids]

    return MergeResult(rows=list(existing_rows) + added, added=added, added_years=[film.year for film in new_films],
                       missing_from_wikidata=missing, skipped_without_year=skipped_without_year)


def read_fetched_years(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def write_fetched_years(path, fetched_years):
    path.write_text(json.dumps(dict(sorted(fetched_years.items())), indent=2) + '\n', encoding='utf-8')


def read_rows(csv_path):
    with open(csv_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        next(reader, None)
        return [(title, imdb_id) for title, imdb_id in reader]


def write_rows(csv_path, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator='\n')
    writer.writerow(CSV_HEADER)
    writer.writerows(rows)
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        f.write(buffer.getvalue().rstrip('\n'))


def unmapped_csv_files(awards_dir, sources):
    mapped = {source.filename for source in sources}
    return sorted(path.name for path in awards_dir.glob('*.csv') if path.name not in mapped)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Add award winners/nominees found on Wikidata to the local award CSVs. Existing rows are never removed.')
    parser.add_argument('--write', action='store_true', help='write the additions to the CSV files and move fetched_years.json forward (default: dry run)')
    parser.add_argument('--show-missing', action='store_true', help='list the local rows Wikidata does not know about')
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    total_added = 0

    for filename in unmapped_csv_files(AWARDS_DIR, AWARD_SOURCES):
        print(f"{filename}: no Wikidata award mapped in AWARD_SOURCES, skipped")

    fetched_years = read_fetched_years(FETCHED_YEARS_PATH)

    for source in AWARD_SOURCES:
        csv_path = AWARDS_DIR / source.filename
        fetched_until = fetched_years.get(source.filename)
        result = merge_rows(read_rows(csv_path), fetch_wikidata_films(source), source.wikidata_false_positives, fetched_until)
        total_added += len(result.added)

        after = f"after {fetched_until}" if fetched_until is not None else "all years"
        print(f"{source.filename} ({after}): {len(result.added)} to add, {len(result.missing_from_wikidata)} local rows not on Wikidata (kept)")
        for (title, imdb_id), year in zip(result.added, result.added_years):
            print(f"  + {year or '????'} {title} {IMDB_URL}{imdb_id}")
        if result.skipped_without_year:
            print(f"  {result.skipped_without_year} Wikidata films without any date skipped")
        if args.show_missing:
            for title, imdb_id in result.missing_from_wikidata:
                print(f"  ? {title} {IMDB_URL}{imdb_id}")

        if args.write and result.added:
            write_rows(csv_path, result.rows)
            known_years = [year for year in result.added_years if year is not None]
            if known_years and fetched_until is not None and max(known_years) > fetched_until:
                fetched_years[source.filename] = max(known_years)

    if args.write:
        write_fetched_years(FETCHED_YEARS_PATH, fetched_years)

    if not args.write and total_added:
        print("Dry run, nothing written. Re-run with --write to apply.")


if __name__ == '__main__':
    main()
