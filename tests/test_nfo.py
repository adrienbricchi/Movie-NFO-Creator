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

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from movie_nfo_creator.nfo import get_movie_elements, parse_movie_nfo_xml, remove_tag_from_movie_nfo

NFO = """<?xml version='1.0' encoding='utf-8'?>
<movie>
  <title>Dune</title>
  <tag>Vu au cinéma</tag>
  <tag>vu au cinéma</tag>
  <tag>Palme d'Or</tag>
  <tag>Vu au cinéma</tag>
</movie>
https://www.imdb.com/title/tt0087182/
"""


class RemoveTagFromMovieNfoTest(unittest.TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.nfo_path = Path(self.directory.name) / 'movie.nfo'
        self.nfo_path.write_text(NFO, encoding='utf-8')

    def remove(self, tag):
        with redirect_stdout(io.StringIO()):
            return remove_tag_from_movie_nfo(self.nfo_path, tag)

    def test_removes_every_exact_match_and_keeps_the_rest(self):
        self.assertTrue(self.remove('Vu au cinéma'))

        content = self.nfo_path.read_text(encoding='utf-8')
        self.assertEqual(['vu au cinéma', "Palme d'Or"], get_movie_elements(parse_movie_nfo_xml(self.nfo_path), 'tag'))
        self.assertTrue(content.endswith('</movie>\nhttps://www.imdb.com/title/tt0087182/\n'))

    def test_absent_tag_leaves_the_file_untouched(self):
        self.assertFalse(self.remove('Star Wars'))

        self.assertEqual(NFO, self.nfo_path.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
