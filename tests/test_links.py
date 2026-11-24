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
import unittest
from contextlib import redirect_stdout

from movie_nfo_creator.links import FileHeader, folder_uri, with_folder_link


class FolderUriTest(unittest.TestCase):

    def test_spaces_and_accents_are_encoded(self):
        self.assertEqual('file:///films/Le%20Bal%20%281983%29/', folder_uri('/films/Le Bal (1983)'))
        self.assertEqual('file:///films/%C3%89t%C3%A9/', folder_uri('/films/Été'))

    def test_link_points_to_the_movie_folder(self):
        self.assertEqual('/films/Le Bal/Le Bal.mkv  file:///films/Le%20Bal/', with_folder_link('/films/Le Bal/Le Bal.mkv'))


class FileHeaderTest(unittest.TestCase):

    def test_prints_once(self):
        header = FileHeader('/films/Dune/Dune.mkv')
        output = io.StringIO()

        with redirect_stdout(output):
            header.print()
            header.print()

        self.assertEqual('/films/Dune/Dune.mkv  file:///films/Dune/\n', output.getvalue())


if __name__ == '__main__':
    unittest.main()
