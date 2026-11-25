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

import unittest

from refresh_universes import (FETCHED_DATES_PATH, TAG_LISTS_DIR, UNIVERSE_SOURCES, UNIVERSES_DIR, UniverseFilm, UniverseSource, build_query, merge_rows, parse_sparql_response,
                               read_fetched_dates)
from refresh_awards import read_rows, unmapped_csv_files


def binding(film, imdb, **values):
    result = {'film': {'value': film}, 'imdb': {'value': imdb}}
    result.update({key: {'value': value} for key, value in values.items()})
    return result


class ParseSparqlResponseTest(unittest.TestCase):

    def test_keeps_earliest_release_date_per_film(self):
        data = {'results': {'bindings': [
            binding('Q1', 'tt0000001', title='Le Film', released='2024-03-10T00:00:00Z'),
            binding('Q1', 'tt0000002', labelEn='The Movie', released='2023-11-01T00:00:00Z'),
            binding('Q2', 'tt0000003', labelEn='Other'),
        ]}}

        films = parse_sparql_response(data)

        self.assertEqual(2, len(films))
        self.assertEqual({'tt0000001', 'tt0000002'}, films[0].imdb_ids)
        self.assertEqual('Le Film', films[0].title)
        self.assertEqual('2023-11-01', films[0].released)
        self.assertIsNone(films[1].released)


class BuildQueryTest(unittest.TestCase):

    def test_lists_every_universe_item(self):
        query = build_query(UniverseSource('file.csv', ('Q1', 'Q2')))

        self.assertIn('VALUES ?universe { wd:Q1 wd:Q2 }', query)


class MergeRowsTest(unittest.TestCase):

    def test_appends_films_released_after_the_cut_off_sorted_by_date(self):
        films = [
            UniverseFilm({'tt0000003'}, 'Third', '2026-12-17'),
            UniverseFilm({'tt0000002'}, 'Second', '2026-11-25'),
            UniverseFilm({'tt0000009'}, 'Already covered', '2026-11-24'),
        ]

        result = merge_rows([('First', 'tt0000001')], films, '2026-11-24', '2027-01-01')

        self.assertEqual([('Second', 'tt0000002'), ('Third', 'tt0000003')], result.added)
        self.assertEqual(['2026-11-25', '2026-12-17'], result.added_dates)
        self.assertEqual([('First', 'tt0000001'), ('Second', 'tt0000002'), ('Third', 'tt0000003')], result.rows)

    def test_unreleased_films_are_skipped(self):
        result = merge_rows([], [UniverseFilm({'tt0000002'}, 'Upcoming', '2027-05-01')], '2026-11-24', '2026-12-01')

        self.assertEqual([], result.added)

    def test_films_without_date_are_skipped_and_counted(self):
        result = merge_rows([], [UniverseFilm({'tt0000002'}, 'Undated')], '2026-11-24', '2026-12-01')

        self.assertEqual([], result.added)
        self.assertEqual(1, result.skipped_without_date)

    def test_known_films_and_false_positives_are_skipped(self):
        films = [UniverseFilm({'tt0000001', 'tt0000005'}, 'Known', '2026-12-01'), UniverseFilm({'tt0000002'}, 'Short', '2026-12-01')]

        result = merge_rows([('Known', 'tt0000001')], films, '2026-11-24', '2026-12-31', false_positives=('tt0000002',))

        self.assertEqual([], result.added)

    def test_keeps_rows_missing_from_wikidata(self):
        result = merge_rows([('Local', 'tt0000001')], [], '2026-11-24', '2026-12-31')

        self.assertEqual([('Local', 'tt0000001')], result.rows)
        self.assertEqual([('Local', 'tt0000001')], result.missing_from_wikidata)


class UniverseSourcesTest(unittest.TestCase):

    def test_every_universe_csv_is_listed(self):
        self.assertEqual([], unmapped_csv_files(UNIVERSES_DIR, UNIVERSE_SOURCES))

    def test_every_refreshed_universe_has_a_cut_off_date(self):
        refreshed = {source.filename for source in UNIVERSE_SOURCES if not source.closed and source.wikidata_items}
        self.assertEqual(refreshed, set(read_fetched_dates(FETCHED_DATES_PATH)))

    def test_every_universe_csv_has_rows(self):
        for source in UNIVERSE_SOURCES:
            self.assertTrue(read_rows(TAG_LISTS_DIR / source.folder / source.filename), source.filename)


if __name__ == '__main__':
    unittest.main()
