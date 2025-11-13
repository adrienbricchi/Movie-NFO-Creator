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
import glob
import os

from .api import get_movie_by_imdb_id, find_tmdb_movie
from .parsers import (
    parse_letterboxd_csv,
    parse_movie_id_csv_into_id_array,
    parse_awards,
    is_movie_in_letterboxd_list,
    parse_movie_nfo_imdb,
    parse_movie_nfo_xml,
    get_movie_element,
    get_movie_elements,
    append_movie_to_csv,
)
from .nfo import (
    prompt_create_movie_nfo,
    add_tag_to_movie_nfo,
    add_playcount_to_nfo,
)
from .utils import print_error, are_roughly_equals, parse_title_and_year


def load_properties(filepath):
    """Load configuration from INI file."""
    config = configparser.ConfigParser()
    with open(filepath, 'r', encoding='utf-8') as file:
        config.read_file(file)
    return config


def find_mkv_files(root_dir):
    """Find all MKV files in the specified directory pattern."""
    pattern = os.path.join(
        root_dir,
        '[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]',
        '**',
        '*.mkv'
    )
    return glob.glob(pattern, recursive=True)


def ask_and_append_movie_to_watched_override(title, imdb_id):
    """Ask user if they want to add a movie to the watched override list."""
    answer = input(f"Add movie '{title}' ({imdb_id}) to watched_override.csv? [Y/n]: ").strip().lower()
    if answer in ['', 'y', 'yes']:
        append_movie_to_csv("watched_override.csv", title, imdb_id)
    else:
        print("Skipped.")


def main():
    """Main CLI entry point."""
    config = load_properties('config.ini')
    ROOT_PATH = config.get('paths', 'root_dir', fallback=None)
    TMDB_API_KEY = config.get('tmdb', 'api_key', fallback=None)
    LETTERBOXD_WATCHED_FILES = config.get('letterboxd', 'watched_file', fallback=None)

    if not ROOT_PATH:
        print_error("config.ini root_dir not found")
        exit(1)

    if not TMDB_API_KEY:
        print_error("config.ini api_key not found")
        exit(1)

    if not LETTERBOXD_WATCHED_FILES:
        print_error("config.ini watched_file not found")
        exit(1)

    letterboxd_movies = parse_letterboxd_csv(LETTERBOXD_WATCHED_FILES)
    override_watched_movies = parse_movie_id_csv_into_id_array('watched_override.csv')
    awards = parse_awards()

    filepaths = find_mkv_files(ROOT_PATH)
    for i, filepath in enumerate(filepaths):

        filename = os.path.basename(filepath)
        movie = parse_title_and_year(filename)
        folder_name = os.path.dirname(filepath)
        movie_nfo_path = os.path.join(folder_name, 'movie.nfo')
        imdb_id = parse_movie_nfo_imdb(movie_nfo_path)

        if movie is None:
            # print("No match: " + filename)
            continue

        tmdb_movie = get_movie_by_imdb_id(imdb_id, TMDB_API_KEY) if imdb_id else find_tmdb_movie(movie, TMDB_API_KEY)
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

        print(str(movie) + " " + imdb_id)
        nfo_root = parse_movie_nfo_xml(movie_nfo_path)

        if nfo_root is None:
            prompt_create_movie_nfo(movie_nfo_path, imdb_id, tmdb_movie, letterboxd_watched, TMDB_API_KEY)
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
