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

from movie_nfo_creator.tags import find_tag_mismatches

TAG_LISTS = {
    'Palme d\'Or': ['tt0000001'],
    'Star Wars': ['tt0000002', 'tt0000003'],
}


class FindTagMismatchesTest(unittest.TestCase):

    def test_missing_automatic_tag(self):
        mismatches = find_tag_mismatches([], 'tt0000002', TAG_LISTS)

        self.assertEqual(['Star Wars'], mismatches.missing)
        self.assertEqual([], mismatches.irrelevant)
        self.assertEqual([], mismatches.unknown)

    def test_automatic_tag_on_the_wrong_film(self):
        mismatches = find_tag_mismatches(['Palme d\'Or'], 'tt0000002', TAG_LISTS)

        self.assertEqual(['Star Wars'], mismatches.missing)
        self.assertEqual(['Palme d\'Or'], mismatches.irrelevant)
        self.assertEqual([], mismatches.unknown)

    def test_tag_matching_no_automatic_tag(self):
        mismatches = find_tag_mismatches(['Star Wars', 'Univers cinématographique Marvel'], 'tt0000002', TAG_LISTS)

        self.assertEqual([], mismatches.missing)
        self.assertEqual([], mismatches.irrelevant)
        self.assertEqual(['Univers cinématographique Marvel'], mismatches.unknown)

    def test_tmdb_id_matches_a_list_as_well_as_the_imdb_id(self):
        tag_lists = {'Les Guignols de l\'info': ['tt0000004', '396840']}

        by_tmdb_id = find_tag_mismatches([], {'396840'}, tag_lists)
        by_either_id = find_tag_mismatches(['Les Guignols de l\'info'], {'tt0000009', '396840'}, tag_lists)

        self.assertEqual(['Les Guignols de l\'info'], by_tmdb_id.missing)
        self.assertEqual(([], []), (by_either_id.missing, by_either_id.irrelevant))

    def test_no_tags_in_nfo(self):
        mismatches = find_tag_mismatches(None, 'tt0000009', TAG_LISTS)

        self.assertEqual(([], [], []), (mismatches.missing, mismatches.irrelevant, mismatches.unknown))


class TagsToRemoveTest(unittest.TestCase):

    def test_listed_tag_is_removable_and_not_unknown(self):
        mismatches = find_tag_mismatches(['Star Wars', 'Vu au cinéma'], 'tt0000002', TAG_LISTS, ['Vu au cinéma'])

        self.assertEqual(['Vu au cinéma'], mismatches.removable)
        self.assertEqual([], mismatches.unknown)

    def test_match_is_case_sensitive(self):
        mismatches = find_tag_mismatches(['vu au cinéma'], 'tt0000009', TAG_LISTS, ['Vu au cinéma'])

        self.assertEqual([], mismatches.removable)
        self.assertEqual(['vu au cinéma'], mismatches.unknown)

    def test_listed_automatic_tag_is_removed_and_never_added(self):
        present = find_tag_mismatches(['Star Wars'], 'tt0000002', TAG_LISTS, ['Star Wars'])
        absent = find_tag_mismatches([], 'tt0000002', TAG_LISTS, ['Star Wars'])

        self.assertEqual((['Star Wars'], []), (present.removable, present.missing))
        self.assertEqual(([], []), (absent.removable, absent.missing))

    def test_duplicated_tag_is_reported_once(self):
        mismatches = find_tag_mismatches(['Vu au cinéma', 'Vu au cinéma'], 'tt0000009', TAG_LISTS, ['Vu au cinéma'])

        self.assertEqual(['Vu au cinéma'], mismatches.removable)

    def test_nothing_removable_by_default(self):
        self.assertEqual([], find_tag_mismatches(['Star Wars'], 'tt0000002', TAG_LISTS).removable)


if __name__ == '__main__':
    unittest.main()
