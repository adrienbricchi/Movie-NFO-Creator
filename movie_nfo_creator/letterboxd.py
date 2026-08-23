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

from .scanner import are_roughly_equals


def parse_letterboxd_csv(filepath):
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
                'url': url,
            })
    return movies


def letterboxd_id_from_url(url):
    return url.rstrip('/').rsplit('/', 1)[-1]


def resolve_letterboxd_watched(letterboxd_data, movies_db, imdb_id, title, year):
    cached_entry = movies_db.get(imdb_id)
    already_cached_as_watched = cached_entry is not None and cached_entry.get('watched', False)
    if already_cached_as_watched:
        return True, None

    for letterboxd_movie in letterboxd_data:
        year_matches = year is not None and abs(letterboxd_movie['year'] - year) <= 1
        if year_matches and are_roughly_equals(letterboxd_movie['title'], title):
            return True, letterboxd_movie

    return False, None
