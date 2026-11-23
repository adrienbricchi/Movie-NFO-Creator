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

import json
import os
import sqlite3
import time

CACHE_TTL_SECONDS = 30 * 24 * 60 * 60

TABLE_SCHEMA = '''
    CREATE TABLE IF NOT EXISTS mkv_analysis_cache (
        filepath TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        mtime_ns INTEGER NOT NULL,
        cached_at REAL NOT NULL,
        mkv_info_json TEXT,
        chapter_starts_json TEXT,
        PRIMARY KEY (filepath, size_bytes, mtime_ns)
    )
'''


def _connect(db_path):
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.execute(TABLE_SCHEMA)
    return conn


def _fingerprint(filepath):
    stat = os.stat(filepath)
    return stat.st_size, stat.st_mtime_ns


def load_cached_deep_analysis(db_path, filepath):
    size_bytes, mtime_ns = _fingerprint(filepath)
    conn = _connect(db_path)
    try:
        row = conn.execute(
            'SELECT cached_at, mkv_info_json, chapter_starts_json FROM mkv_analysis_cache '
            'WHERE filepath = ? AND size_bytes = ? AND mtime_ns = ?',
            (filepath, size_bytes, mtime_ns),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    cached_at, mkv_info_json, chapter_starts_json = row
    if time.time() - cached_at > CACHE_TTL_SECONDS:
        return None

    mkv_info = json.loads(mkv_info_json) if mkv_info_json is not None else None
    if mkv_info is not None:
        mkv_info['audio_languages'] = set(mkv_info['audio_languages'])
    chapter_starts = json.loads(chapter_starts_json) if chapter_starts_json is not None else None
    return mkv_info, chapter_starts


def store_deep_analysis_cache(db_path, filepath, mkv_info, chapter_starts):
    size_bytes, mtime_ns = _fingerprint(filepath)

    serializable_mkv_info = None
    if mkv_info is not None:
        serializable_mkv_info = dict(mkv_info)
        serializable_mkv_info['audio_languages'] = sorted(serializable_mkv_info['audio_languages'])

    conn = _connect(db_path)
    try:
        conn.execute(
            '''
            INSERT INTO mkv_analysis_cache
                (filepath, size_bytes, mtime_ns, cached_at, mkv_info_json, chapter_starts_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(filepath, size_bytes, mtime_ns) DO UPDATE SET
                cached_at = excluded.cached_at,
                mkv_info_json = excluded.mkv_info_json,
                chapter_starts_json = excluded.chapter_starts_json
            ''',
            (
                filepath,
                size_bytes,
                mtime_ns,
                time.time(),
                json.dumps(serializable_mkv_info) if serializable_mkv_info is not None else None,
                json.dumps(chapter_starts) if chapter_starts is not None else None,
            ),
        )
        conn.commit()
    finally:
        conn.close()
