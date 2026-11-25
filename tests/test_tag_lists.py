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

from movie_nfo_creator.tag_lists import TAG_LISTS_DIR, TAG_SOURCES, parse_tag_lists


class TagSourcesTest(unittest.TestCase):

    def test_every_csv_is_mapped_to_one_tag(self):
        for folder, sources in TAG_SOURCES.items():
            self.assertEqual(sorted(path.name for path in (TAG_LISTS_DIR / folder).glob('*.csv')), sorted(filename for _, filename in sources), folder)

    def test_tag_names_are_unique_across_folders(self):
        tags = [tag for sources in TAG_SOURCES.values() for tag, _ in sources]

        self.assertEqual(len(tags), len(set(tags)))

    def test_every_list_holds_imdb_ids(self):
        for tag, imdb_ids in parse_tag_lists().items():
            self.assertTrue(imdb_ids, tag)
            self.assertTrue(all(imdb_id.startswith('tt') for imdb_id in imdb_ids), tag)


if __name__ == '__main__':
    unittest.main()
