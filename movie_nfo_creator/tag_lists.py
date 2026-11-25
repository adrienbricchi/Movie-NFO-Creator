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

TAG_LISTS_DIR = Path(__file__).parent / 'tag_lists'


def read_tag_list(csv_path):
    with open(csv_path, 'r', encoding='utf-8') as f:
        tag = f.readline().strip()
        reader = csv.reader(f)
        next(reader, None)  # Skip header
        return tag, [imdb_id for _, imdb_id in reader]


def parse_tag_lists():
    result = {}
    for csv_path in sorted(TAG_LISTS_DIR.rglob('*.csv')):
        tag, imdb_ids = read_tag_list(csv_path)
        if tag in result:
            raise ValueError(f"Tag {tag} is declared twice, second time in {csv_path}")
        result[tag] = imdb_ids
    return result
