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

import tempfile
import unittest
from pathlib import Path

from refresh_awards import (AWARD_SOURCES, AWARDS_DIR, FETCHED_YEARS_PATH, AwardSource, WikidataFilm, build_query, merge_rows, parse_sparql_response, read_fetched_years,
                            read_rows, unmapped_csv_files, write_fetched_years, write_rows)


def binding(film, imdb, **values):
    result = {'film': {'value': film}, 'imdb': {'value': imdb}}
    result.update({key: {'value': value} for key, value in values.items()})
    return result


class ParseSparqlResponseTest(unittest.TestCase):

    def test_groups_rows_by_film(self):
        data = {'results': {'bindings': [
            binding('Q1', 'tt0000001', title='Le Film', labelEn='The Movie', ceremony='2024-03-10T00:00:00Z'),
            binding('Q1', 'tt0000002', title='Le Film', released='2023-05-01T00:00:00Z'),
            binding('Q2', 'tt0000003', labelEn='Other', released='1999-01-01T00:00:00Z'),
        ]}}

        films = parse_sparql_response(data)

        self.assertEqual(2, len(films))
        self.assertEqual({'tt0000001', 'tt0000002'}, films[0].imdb_ids)
        self.assertEqual('Le Film', films[0].title)
        self.assertEqual(2024, films[0].ceremony_year)
        self.assertEqual(2023, films[0].release_year)
        self.assertEqual('Other', films[1].title)
        self.assertIsNone(films[1].ceremony_year)
        self.assertEqual(1999, films[1].release_year)

    def test_film_without_title_or_date(self):
        films = parse_sparql_response({'results': {'bindings': [binding('Q1', 'tt0000001')]}})

        self.assertIsNone(films[0].title)
        self.assertIsNone(films[0].year)


class WikidataFilmYearTest(unittest.TestCase):

    def test_ceremony_year_wins(self):
        self.assertEqual(2024, WikidataFilm({'tt0000001'}, 'Film', 2024, 2020).year)

    def test_release_year_estimates_next_ceremony(self):
        self.assertEqual(2024, WikidataFilm({'tt0000001'}, 'Film', None, 2023).year)

    def test_no_date(self):
        self.assertIsNone(WikidataFilm({'tt0000001'}, 'Film').year)


class BuildQueryTest(unittest.TestCase):

    def test_winners(self):
        query = build_query(AwardSource('file.csv', 'Q102427'))

        self.assertIn('ps:P166 wd:Q102427', query)
        self.assertNotIn('FILTER NOT EXISTS', query)

    def test_nominees_exclude_winners(self):
        query = build_query(AwardSource('file.csv', 'Q102427', nominees_only=True))

        self.assertIn('ps:P1411 wd:Q102427', query)
        self.assertIn('FILTER NOT EXISTS { ?film p:P166/ps:P166 wd:Q102427 . }', query)


class MergeRowsTest(unittest.TestCase):

    def test_appends_new_films_sorted_by_year(self):
        existing = [('Old', 'tt0000001')]
        films = [
            WikidataFilm({'tt0000003'}, 'Newer', 2025),
            WikidataFilm({'tt0000001'}, 'Old', 1990),
            WikidataFilm({'tt0000002'}, 'New', 2024),
        ]

        result = merge_rows(existing, films)

        self.assertEqual([('Old', 'tt0000001'), ('New', 'tt0000002'), ('Newer', 'tt0000003')], result.rows)
        self.assertEqual([('New', 'tt0000002'), ('Newer', 'tt0000003')], result.added)
        self.assertEqual([], result.missing_from_wikidata)

    def test_keeps_rows_missing_from_wikidata(self):
        result = merge_rows([('Manual', 'tt0000001')], [])

        self.assertEqual([('Manual', 'tt0000001')], result.rows)
        self.assertEqual([('Manual', 'tt0000001')], result.missing_from_wikidata)

    def test_film_known_under_another_imdb_id_is_not_added(self):
        result = merge_rows([('Film', 'tt0000001')], [WikidataFilm({'tt0000001', 'tt0000009'}, 'Film', 2000)])

        self.assertEqual([], result.added)

    def test_false_positives_are_skipped(self):
        result = merge_rows([], [WikidataFilm({'tt0000001'}, 'Wrong', 2000)], false_positives=('tt0000001',))

        self.assertEqual([], result.added)

    def test_fetched_years_are_not_refreshed(self):
        films = [WikidataFilm({'tt0000001'}, 'Old', 1990), WikidataFilm({'tt0000002'}, 'Fetched', 2026), WikidataFilm({'tt0000003'}, 'New', 2027)]

        result = merge_rows([], films, fetched_until=2026)

        self.assertEqual([('New', 'tt0000003')], result.added)
        self.assertEqual([2027], result.added_years)

    def test_films_without_date_are_skipped_after_a_fetched_year(self):
        result = merge_rows([], [WikidataFilm({'tt0000001'}, 'Undated')], fetched_until=2026)

        self.assertEqual([], result.added)
        self.assertEqual(1, result.skipped_without_year)

    def test_all_years_without_a_fetched_year(self):
        result = merge_rows([], [WikidataFilm({'tt0000001'}, 'Old', 1990), WikidataFilm({'tt0000002'}, 'Undated')])

        self.assertEqual([('Old', 'tt0000001'), ('Undated', 'tt0000002')], result.added)

    def test_film_without_title_uses_its_id(self):
        result = merge_rows([], [WikidataFilm({'tt0000001'}, None, None)])

        self.assertEqual([('tt0000001', 'tt0000001')], result.added)


class AwardSourcesTest(unittest.TestCase):

    def test_every_award_csv_is_mapped(self):
        self.assertEqual([], unmapped_csv_files(AWARDS_DIR, AWARD_SOURCES))

    def test_every_mapped_award_has_a_fetched_year(self):
        self.assertEqual({source.filename for source in AWARD_SOURCES}, set(read_fetched_years(FETCHED_YEARS_PATH)))

    def test_fetched_years_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fetched_years.json'

            self.assertEqual({}, read_fetched_years(path))
            write_fetched_years(path, {'b.csv': 2026, 'a.csv': 2025})

            self.assertEqual({'a.csv': 2025, 'b.csv': 2026}, read_fetched_years(path))

    def test_unmapped_csv_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'mapped.csv').touch()
            (Path(directory) / 'new_award.csv').touch()

            self.assertEqual(['new_award.csv'], unmapped_csv_files(Path(directory), [AwardSource('mapped.csv', 'Q1')]))


class CsvRoundTripTest(unittest.TestCase):

    def test_titles_with_commas_survive(self):
        rows = [('Plain', 'tt0000001'), ('Comma, Title', 'tt0000002')]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'award.csv'

            write_rows(path, rows)

            self.assertEqual(rows, read_rows(path))
            self.assertFalse(path.read_text(encoding='utf-8').endswith('\n'))


if __name__ == '__main__':
    unittest.main()
