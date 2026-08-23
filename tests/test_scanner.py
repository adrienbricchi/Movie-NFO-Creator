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

from movie_nfo_creator.scanner import are_roughly_equals


class AreRoughlyEqualsTest(unittest.TestCase):

    def test_are_roughly_equals(self):
        self.assertTrue(are_roughly_equals('Halloween', 'Halloween'))
        self.assertTrue(are_roughly_equals('HALLOWEEN', 'halloween'))

        self.assertTrue(are_roughly_equals('Halloween:', 'Halloween -'))
        self.assertTrue(are_roughly_equals('Halloween -', 'Halloween :'))
        self.assertTrue(are_roughly_equals('Halloween: Resurrection', 'Halloween - Resurrection'))
        self.assertTrue(are_roughly_equals('Halloween : Resurrection', 'Halloween- Resurrection'))
        self.assertTrue(are_roughly_equals('Springsteen: Deliver Me from Nowhere', 'Springsteen - Deliver me from nowhere'))
        self.assertFalse(are_roughly_equals('Halloween-', 'Halloween -'))
        self.assertFalse(are_roughly_equals('Spider-Man', 'Spider - Man'))
        self.assertFalse(are_roughly_equals('Halloween : Resurrection', 'Halloween-Resurrection'))

        self.assertTrue(are_roughly_equals('Cul-de-sac / Dead end', 'Cul-de-sac - Dead end'))

        self.assertTrue(are_roughly_equals('Furiosa — Une saga Mad Max', 'Furiosa - Une saga Mad Max'))
        self.assertTrue(are_roughly_equals('Furiosa – Une saga Mad Max', 'Furiosa - Une saga Mad Max'))

        self.assertTrue(are_roughly_equals('Comment tuer son boss ?', 'Comment tuer son boss'))
        self.assertTrue(are_roughly_equals('Mais qui a re-tue Pamela Rose?', 'Mais qui a re-tue Pamela Rose'))

        self.assertTrue(are_roughly_equals('Mr. & Mrs. Smith', 'Mr. et Mrs. Smith'))
        self.assertTrue(are_roughly_equals('Dumb & Dumber', 'Dumb and Dumber'))

        self.assertFalse(are_roughly_equals('Halloween', 'Halloween II'))
        self.assertFalse(are_roughly_equals('Alien', 'Aliens'))

        self.assertFalse(are_roughly_equals('Halloween: Resurrection', 'Halloween - Resurrection', filename_lenient=False))
        self.assertTrue(are_roughly_equals('Halloween: Resurrection', 'Halloween: Resurrection', filename_lenient=False))


if __name__ == '__main__':
    unittest.main()
