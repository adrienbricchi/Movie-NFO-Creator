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

from movie_nfo_creator.tag_lists import TAG_INDEX_PATH, TAG_LISTS_DIR, parse_tag_lists, read_tag_index


class TagIndexTest(unittest.TestCase):

    def test_every_csv_is_indexed_once(self):
        csv_paths = sorted(path.relative_to(TAG_LISTS_DIR).as_posix() for path in TAG_LISTS_DIR.rglob('*.csv') if path != TAG_INDEX_PATH)

        self.assertEqual(csv_paths, sorted(csv_path for _, csv_path in read_tag_index()))

    def test_tag_names_are_unique(self):
        tags = [tag for tag, _ in read_tag_index()]

        self.assertEqual(len(tags), len(set(tags)))

    def test_every_list_holds_imdb_ids(self):
        for tag, imdb_ids in parse_tag_lists().items():
            self.assertTrue(imdb_ids, tag)
            self.assertTrue(all(imdb_id.startswith('tt') for imdb_id in imdb_ids), tag)


if __name__ == '__main__':
    unittest.main()
