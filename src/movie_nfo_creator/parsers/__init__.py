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

from .csv_parser import (
    parse_letterboxd_csv,
    parse_movie_id_csv_into_id_array,
    parse_awards,
    is_movie_in_letterboxd_list,
    append_movie_to_csv,
)
from .nfo_parser import (
    parse_movie_nfo_imdb,
    parse_movie_nfo_xml,
    get_movie_element,
    get_movie_elements,
)

__all__ = [
    'parse_letterboxd_csv',
    'parse_movie_id_csv_into_id_array',
    'parse_awards',
    'is_movie_in_letterboxd_list',
    'append_movie_to_csv',
    'parse_movie_nfo_imdb',
    'parse_movie_nfo_xml',
    'get_movie_element',
    'get_movie_elements',
]
