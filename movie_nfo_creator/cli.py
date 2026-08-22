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

import os

from .awards import parse_awards
from .config import load_config
from .csv_utils import parse_movie_id_csv_into_id_array
from .letterboxd import is_movie_in_letterboxd_list, parse_letterboxd_csv
from .nfo import (
    add_playcount_to_nfo,
    add_tag_to_movie_nfo,
    ask_and_append_movie_to_watched_override,
    get_movie_element,
    get_movie_elements,
    parse_movie_nfo_imdb,
    parse_movie_nfo_xml,
    prompt_create_movie_nfo,
)
from .scanner import are_roughly_equals, find_mkv_files, parse_title_and_year
from .tmdb import TmdbClient
from .util import print_error


def main():
    try:
        config = load_config('config.ini')
    except (ValueError, FileNotFoundError) as e:
        print_error(str(e))
        raise SystemExit(1)

    tmdb_client = TmdbClient(config.tmdb_api_key)

    letterboxd_movies = parse_letterboxd_csv(config.letterboxd_watched_file)
    override_watched_movies = parse_movie_id_csv_into_id_array('watched_override.csv')
    awards = parse_awards()

    filepaths = []
    for dir_root in config.root_dirs:
        filepaths.extend(find_mkv_files(dir_root))

    for filepath in filepaths:

        filename = os.path.basename(filepath)
        movie = parse_title_and_year(filename)
        folder_name = os.path.dirname(filepath)
        movie_nfo_path = os.path.join(folder_name, 'movie.nfo')
        imdb_id = parse_movie_nfo_imdb(movie_nfo_path)

        if movie is None:
            continue

        tmdb_movie = tmdb_client.get_movie_by_imdb_id(imdb_id) if imdb_id else tmdb_client.find_movie(movie)
        if tmdb_movie is None:
            continue

        imdb_id = tmdb_movie.get('imdb_id')
        tmdb_title = tmdb_movie.get('title')
        tmdb_original_title = tmdb_movie.get('original_title')
        tmdb_release_date = tmdb_movie.get('release_date')
        tmdb_release_year = int(tmdb_release_date[:4]) if tmdb_release_date else None
        letterboxd_watched = is_movie_in_letterboxd_list(letterboxd_movies, tmdb_original_title, tmdb_release_year)
        override_watched = imdb_id in override_watched_movies
        is_watched = letterboxd_watched or override_watched

        nfo_root = parse_movie_nfo_xml(movie_nfo_path)

        if nfo_root is None:
            prompt_create_movie_nfo(movie_nfo_path, imdb_id, tmdb_movie, letterboxd_watched, tmdb_client)
            continue

        nfo_title = get_movie_element(nfo_root, "title")
        if nfo_title is None:
            print_error("Cannot parse NFO title: " + filepath)
            continue

        if not are_roughly_equals(nfo_title, tmdb_movie['title']) or not are_roughly_equals(nfo_title, movie[0]):
            print("    Title difference found")
            print("    NFO movie title: " + nfo_title)
            print("    TMDB movie title: " + tmdb_title)
            print("    File movie title: " + movie[0])

        nfo_watch_count = get_movie_element(nfo_root, "playcount")
        nfo_watched = nfo_watch_count is not None

        if nfo_watched and not is_watched:
            print_error("    watched status mismatch")
            comma_less_title = movie[0].replace(',', '')
            ask_and_append_movie_to_watched_override(comma_less_title, imdb_id)

        if is_watched and not nfo_watched:
            add_playcount_to_nfo(movie_nfo_path)

        nfo_tags = get_movie_elements(nfo_root, "tag")
        appropriate_award_tags = [key for key, values in awards.items() if imdb_id in values]
        for missing_tag in [tag for tag in appropriate_award_tags if tag not in nfo_tags]:
            add_tag_to_movie_nfo(movie_nfo_path, missing_tag)

        for irrelevant_tag in [tag for tag in awards.keys() if tag in nfo_tags and imdb_id not in awards[tag]]:
            print_error("    irrelevant award tag: " + irrelevant_tag)
