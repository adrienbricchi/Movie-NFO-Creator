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

from movie_nfo_creator.tag_lists import TAG_LISTS_DIR, parse_tag_lists, read_tag_list


class TagListsTest(unittest.TestCase):

    def test_every_csv_declares_a_tag_and_the_header(self):
        for csv_path in TAG_LISTS_DIR.rglob('*.csv'):
            lines = csv_path.read_text(encoding='utf-8').splitlines()
            self.assertTrue(lines[0].strip(), csv_path)
            self.assertEqual('original_title,imdb_id', lines[1], csv_path)

    def test_every_csv_is_loaded_under_its_own_tag(self):
        csv_paths = list(TAG_LISTS_DIR.rglob('*.csv'))

        self.assertEqual(sorted(read_tag_list(csv_path)[0] for csv_path in csv_paths), sorted(parse_tag_lists()))

    def test_every_list_holds_imdb_ids(self):
        for tag, imdb_ids in parse_tag_lists().items():
            self.assertTrue(imdb_ids, tag)
            self.assertTrue(all(imdb_id.startswith('tt') for imdb_id in imdb_ids), tag)


if __name__ == '__main__':
    unittest.main()
