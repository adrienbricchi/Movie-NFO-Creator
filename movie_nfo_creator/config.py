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

import configparser
from dataclasses import dataclass


@dataclass
class Config:
    root_dirs: list[str]
    tmdb_api_key: str
    letterboxd_watched_file: str
    mkvtoolnix_dir: str
    mediainfo_dir: str
    tags_to_remove: list[str]


def load_config(filepath):
    parser = configparser.ConfigParser()
    with open(filepath, 'r', encoding='utf-8') as file:
        parser.read_file(file)

    root_dir_value = parser.get('paths', 'root_dir', fallback=None)
    tmdb_api_key = parser.get('tmdb', 'api_key', fallback=None)
    letterboxd_watched_file = parser.get('letterboxd', 'watched_file', fallback=None)
    mkvtoolnix_dir = parser.get('tracks', 'mkvtoolnix_dir', fallback='')
    mediainfo_dir = parser.get('tracks', 'mediainfo_dir', fallback='')
    tags_to_remove_value = parser.get('tags', 'remove', fallback='')

    if not root_dir_value:
        raise ValueError("config.ini root_dir not found")
    if not tmdb_api_key:
        raise ValueError("config.ini api_key not found")
    if not letterboxd_watched_file:
        raise ValueError("config.ini watched_file not found")

    return Config(
        root_dirs=[d.strip() for d in root_dir_value.split(';')],
        tmdb_api_key=tmdb_api_key,
        letterboxd_watched_file=letterboxd_watched_file,
        mkvtoolnix_dir=mkvtoolnix_dir,
        mediainfo_dir=mediainfo_dir,
        tags_to_remove=[tag.strip() for tag in tags_to_remove_value.split(';') if tag.strip()],
    )
