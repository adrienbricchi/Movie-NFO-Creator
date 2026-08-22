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
import os


def parse_movie_id_csv_into_id_array(csv_path):
    result = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)  # Skip header
        for row in reader:
            title, imdb_id = row
            result.append(imdb_id)
    return result


def append_movie_to_csv(csv_path, title, imdb_id):
    file_exists = os.path.isfile(csv_path)
    try:
        with open(csv_path, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['title', 'imdb_id'])
            writer.writerow([title, imdb_id])
        print(f"Movie '{title}' ({imdb_id}) added to {csv_path}")
    except Exception as e:
        print(f"Error writing to CSV: {e}")
