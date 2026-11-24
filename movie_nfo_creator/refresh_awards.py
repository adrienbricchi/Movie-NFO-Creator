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
from dataclasses import dataclass, field
from typing import Optional

import requests

from .awards import AWARD_SOURCES, AWARDS_DIR

WIKIDATA_SPARQL_URL = 'https://query.wikidata.org/sparql'
USER_AGENT = 'movie-nfo-creator/0.1 (award list refresh)'
IMDB_URL = 'https://www.imdb.com/title/'
CSV_HEADER = ('original_title', 'imdb_id')

# Ceremony year from the award statement, falling back to the film's earliest release year.
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


@dataclass
class WikidataFilm:
    imdb_ids: set = field(default_factory=set)
    title: Optional[str] = None
    year: Optional[int] = None

    @property
    def imdb_id(self):
        return sorted(self.imdb_ids)[0]


@dataclass
class MergeResult:
    rows: list
    added: list
    missing_from_wikidata: list


def build_query(source):
    if source.nominees_only:
        return QUERY_TEMPLATE.format(property='P1411', award=source.wikidata_award, exclusion=WINNER_EXCLUSION.format(award=source.wikidata_award))
    return QUERY_TEMPLATE.format(property='P166', award=source.wikidata_award, exclusion='')


def _year(binding, key):
    value = binding.get(key, {}).get('value', '')
    return int(value[:4]) if len(value) >= 4 and value[:4].isdigit() else None


def parse_sparql_response(data):
    films = {}
    for binding in data['results']['bindings']:
        film = films.setdefault(binding['film']['value'], WikidataFilm())
        film.imdb_ids.add(binding['imdb']['value'])

        title = next((binding[key]['value'] for key in ('title', 'labelFr', 'labelEn') if key in binding), None)
        film.title = film.title or title

        year = _year(binding, 'ceremony') or _year(binding, 'released')
        if year is not None and (film.year is None or year < film.year):
            film.year = year

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


def merge_rows(existing_rows, wikidata_films, false_positives=()):
    existing_ids = {imdb_id for _, imdb_id in existing_rows}
    new_films = [film for film in wikidata_films if not film.imdb_ids & (existing_ids | set(false_positives))]
    new_films.sort(key=lambda film: (film.year or 9999, film.title or ''))
    added = [(film.title or film.imdb_id, film.imdb_id) for film in new_films]

    wikidata_ids = set().union(*(film.imdb_ids for film in wikidata_films))
    missing = [row for row in existing_rows if row[1] not in wikidata_ids]

    return MergeResult(rows=list(existing_rows) + added, added=added, missing_from_wikidata=missing)


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


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Add award winners/nominees found on Wikidata to the local award CSVs. Existing rows are never removed.')
    parser.add_argument('--write', action='store_true', help='write the additions to the CSV files (default: dry run)')
    parser.add_argument('--show-missing', action='store_true', help='list the local rows Wikidata does not know about')
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    total_added = 0

    for source in AWARD_SOURCES:
        csv_path = AWARDS_DIR / source.filename
        result = merge_rows(read_rows(csv_path), fetch_wikidata_films(source), source.wikidata_false_positives)
        total_added += len(result.added)

        print(f"{source.filename}: {len(result.added)} to add, {len(result.missing_from_wikidata)} local rows not on Wikidata (kept)")
        for title, imdb_id in result.added:
            print(f"  + {title} {IMDB_URL}{imdb_id}")
        if args.show_missing:
            for title, imdb_id in result.missing_from_wikidata:
                print(f"  ? {title} {IMDB_URL}{imdb_id}")

        if args.write and result.added:
            write_rows(csv_path, result.rows)

    if not args.write and total_added:
        print("Dry run, nothing written. Re-run with --write to apply.")


if __name__ == '__main__':
    main()
