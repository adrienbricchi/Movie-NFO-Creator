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

from ..utils import are_roughly_equals


def parse_letterboxd_csv(filepath):
    """Parse Letterboxd CSV export file."""
    movies = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)  # Skip header
        for row in reader:
            if len(row) != 4:
                print(f"Invalid row skipped: {row}")
                continue
            date, title, year, url = row
            movies.append({
                'title': title,
                'year': int(year),
            })
    return movies


def is_movie_in_letterboxd_list(letterboxd_data, title, year):
    """Check if a movie is in the Letterboxd watched list."""
    for letterboxd_movie in letterboxd_data:
        if are_roughly_equals(letterboxd_movie['title'], title) and letterboxd_movie['year'] == year:
            return True
    return False


def parse_movie_id_csv_into_id_array(csv_path):
    """Parse a CSV file containing movie titles and IMDB IDs into an ID array."""
    result = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)  # Skip header
        for row in reader:
            title, imdb_id = row
            result.append(imdb_id)
    return result


def parse_awards():
    """Parse all award CSV files and return a dictionary of awards."""
    result = {}
    for award_source in [
        ('Oscar du meilleur film', 'oscar_best_picture.csv'),
        ('Oscar du meilleur film - Nomination', 'oscar_best_picture_nominee.csv'),
        ('Oscar du meilleur film international', 'oscar_best_international_picture.csv'),
        ("Oscar du meilleur film d'animation", 'oscar_best_animated_picture.csv'),
        ('César du meilleur film', 'cesar_best_picture.csv'),
        ("Palme d'Or", 'palme_d_or.csv'),
    ]:
        result[award_source[0]] = parse_movie_id_csv_into_id_array("./awards/" + award_source[1])

    return result


def append_movie_to_csv(csv_path, title, imdb_id):
    """Append a movie to a CSV file."""
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
