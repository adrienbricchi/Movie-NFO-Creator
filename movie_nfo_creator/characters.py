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

from pathlib import Path

from .csv_utils import parse_movie_id_csv_into_id_array

CHARACTERS_DIR = Path(__file__).parent / 'characters'


def parse_characters():
    result = {}
    for character_source in [
        ('Batman', 'batman.csv'),
        ('Dracula', 'dracula.csv'),
        ('Frankenstein', 'frankenstein.csv'),
        ('Godzilla', 'godzilla.csv'),
        ('King Kong', 'king_kong.csv'),
        ('Spider-Man', 'spider_man.csv'),
        ('Superman', 'superman.csv'),
        ('Tarzan', 'tarzan.csv'),
    ]:
        result[character_source[0]] = parse_movie_id_csv_into_id_array(CHARACTERS_DIR / character_source[1])

    return result
