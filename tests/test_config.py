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

from movie_nfo_creator.config import load_config

BASE = "[paths]\nroot_dir = ./\n[tmdb]\napi_key = key\n[letterboxd]\nwatched_file = ./watched.csv\n"


class TagsToRemoveTest(unittest.TestCase):

    def load(self, content):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        config_path = Path(directory.name) / 'config.ini'
        config_path.write_text(content, encoding='utf-8')
        return load_config(config_path)

    def test_missing_section_means_no_tag(self):
        self.assertEqual([], self.load(BASE).tags_to_remove)

    def test_empty_value_means_no_tag(self):
        self.assertEqual([], self.load(BASE + "[tags]\nremove =\n").tags_to_remove)

    def test_tags_are_split_and_trimmed_with_their_case_kept(self):
        self.assertEqual(['Vu au cinéma', 'IMAX'], self.load(BASE + "[tags]\nremove = Vu au cinéma ; IMAX;\n").tags_to_remove)


if __name__ == '__main__':
    unittest.main()
