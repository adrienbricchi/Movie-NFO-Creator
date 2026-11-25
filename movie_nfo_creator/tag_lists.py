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

import csv
from pathlib import Path

from .csv_utils import parse_movie_id_csv_into_id_array

TAG_LISTS_DIR = Path(__file__).parent / 'tag_lists'
TAG_INDEX_PATH = TAG_LISTS_DIR / 'tags.csv'


def read_tag_index():
    with open(TAG_INDEX_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)  # Skip header
        return [(tag, csv_path) for tag, csv_path in reader]


def parse_tag_lists():
    return {tag: parse_movie_id_csv_into_id_array(TAG_LISTS_DIR / csv_path) for tag, csv_path in read_tag_index()}
