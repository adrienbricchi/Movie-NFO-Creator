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

import sqlite3

TABLE_SCHEMA = '''
    CREATE TABLE IF NOT EXISTS movies (
        imdb_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        letterboxd_id TEXT,
        tmdb_id TEXT,
        watched INTEGER NOT NULL DEFAULT 0
    )
'''


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute(TABLE_SCHEMA)
    return conn


def load_movies_db(db_path):
    movies_db = {}
    conn = _connect(db_path)
    try:
        rows = conn.execute('SELECT imdb_id, title, letterboxd_id, tmdb_id, watched FROM movies')
        for imdb_id, title, letterboxd_id, tmdb_id, watched in rows:
            movies_db[imdb_id] = {
                'title': title,
                'letterboxd_id': letterboxd_id or '',
                'tmdb_id': tmdb_id or '',
                'watched': bool(watched),
            }
    finally:
        conn.close()
    return movies_db


def upsert_movie(db_path, imdb_id, title, letterboxd_id, tmdb_id, watched):
    conn = _connect(db_path)
    try:
        conn.execute(
            '''
            INSERT INTO movies (imdb_id, title, letterboxd_id, tmdb_id, watched)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(imdb_id) DO UPDATE SET
                title = excluded.title,
                letterboxd_id = excluded.letterboxd_id,
                tmdb_id = excluded.tmdb_id,
                watched = excluded.watched
            ''',
            (imdb_id, title, letterboxd_id, tmdb_id, int(watched)),
        )
        conn.commit()
    finally:
        conn.close()
