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
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from .awards import parse_awards
from .config import load_config
from .letterboxd import letterboxd_id_from_url, parse_letterboxd_csv, resolve_letterboxd_watched
from .movies import ask_and_mark_watched, load_movies_db, upsert_movie
from .nfo import (
    add_playcount_to_nfo,
    add_tag_to_movie_nfo,
    get_movie_element,
    get_movie_elements,
    parse_movie_nfo_imdb,
    parse_movie_nfo_xml,
    prompt_create_movie_nfo,
)
from .scanner import are_roughly_equals, find_mkv_files, parse_title_and_year
from .tmdb import TmdbClient
from .util import print_error

TMDB_FETCH_WORKERS = 8
MOVIES_DB_PATH = 'local.sqlite'


def fetch_tmdb_movie(tmdb_client, movie, imdb_id):
    return tmdb_client.get_movie_by_imdb_id(imdb_id) if imdb_id else tmdb_client.find_movie(movie)


def main():
    try:
        config = load_config('config.ini')
    except (ValueError, FileNotFoundError) as e:
        print_error(str(e))
        raise SystemExit(1)

    tmdb_client = TmdbClient(config.tmdb_api_key)

    letterboxd_movies = parse_letterboxd_csv(config.letterboxd_watched_file)
    movies_db = load_movies_db(MOVIES_DB_PATH)
    awards = parse_awards()

    filepaths = []
    for dir_root in config.root_dirs:
        filepaths.extend(find_mkv_files(dir_root))

    print("\n=== Step 1/3: Parsing library ===")
    entries = []
    for filepath in filepaths:
        filename = os.path.basename(filepath)
        movie = parse_title_and_year(filename)
        if movie is None:
            continue
        folder_name = os.path.dirname(filepath)
        movie_nfo_path = os.path.join(folder_name, 'movie.nfo')
        imdb_id = parse_movie_nfo_imdb(movie_nfo_path)
        entries.append((filepath, movie, movie_nfo_path, imdb_id))

    print("\n=== Step 2/3: Fetching TMDb data ===")
    tmdb_movies = [None] * len(entries)
    with ThreadPoolExecutor(max_workers=TMDB_FETCH_WORKERS) as executor:
        future_to_index = {
            executor.submit(fetch_tmdb_movie, tmdb_client, movie, imdb_id): index
            for index, (filepath, movie, movie_nfo_path, imdb_id) in enumerate(entries)
        }
        for future in tqdm(as_completed(future_to_index), total=len(entries), desc="Fetching TMDb data"):
            tmdb_movies[future_to_index[future]] = future.result()

    print("\n=== Step 3/3: Checking for mismatches ===")
    for (filepath, movie, movie_nfo_path, imdb_id), tmdb_movie in zip(entries, tmdb_movies):

        if tmdb_movie is None:
            continue

        imdb_id = tmdb_movie.get('imdb_id')
        tmdb_title = tmdb_movie.get('title')
        tmdb_original_title = tmdb_movie.get('original_title')
        tmdb_release_date = tmdb_movie.get('release_date')
        tmdb_release_year = int(tmdb_release_date[:4]) if tmdb_release_date else None
        letterboxd_watched, matched_letterboxd_movie = resolve_letterboxd_watched(
            letterboxd_movies, movies_db, imdb_id, tmdb_original_title, tmdb_release_year
        )
        cached_entry = movies_db.get(imdb_id)
        newly_confirmed_watched = matched_letterboxd_movie is not None and not (cached_entry and cached_entry['watched'])
        needs_write = cached_entry is None or newly_confirmed_watched
        if needs_write:
            if matched_letterboxd_movie is not None:
                letterboxd_id = letterboxd_id_from_url(matched_letterboxd_movie['url'])
            else:
                letterboxd_id = cached_entry['letterboxd_id'] if cached_entry else ''
            tmdb_id = tmdb_movie.get('id', '')
            upsert_movie(MOVIES_DB_PATH, imdb_id, tmdb_original_title, letterboxd_id, tmdb_id, letterboxd_watched)
            movies_db[imdb_id] = {
                'title': tmdb_original_title,
                'letterboxd_id': letterboxd_id,
                'tmdb_id': tmdb_id,
                'watched': letterboxd_watched,
            }
        is_watched = letterboxd_watched

        nfo_root = parse_movie_nfo_xml(movie_nfo_path)

        if nfo_root is None:
            prompt_create_movie_nfo(movie_nfo_path, imdb_id, tmdb_movie, letterboxd_watched, tmdb_client)
            continue

        nfo_title = get_movie_element(nfo_root, "title")
        if nfo_title is None:
            print_error("Cannot parse NFO title: " + filepath)
            continue

        nfo_matches_tmdb = are_roughly_equals(nfo_title, tmdb_movie['title'], filename_lenient=False)
        nfo_matches_filename = are_roughly_equals(nfo_title, movie[0])
        if not nfo_matches_tmdb or not nfo_matches_filename:
            print("    Title difference found")
            print("    NFO movie title: " + nfo_title)
            print("    TMDB movie title: " + tmdb_title)
            print("    File movie title: " + movie[0])

        nfo_watch_count = get_movie_element(nfo_root, "playcount")
        nfo_watched = nfo_watch_count is not None

        if nfo_watched and not is_watched:
            print_error("    watched status mismatch")
            comma_less_title = movie[0].replace(',', '')
            ask_and_mark_watched(MOVIES_DB_PATH, movies_db, imdb_id, comma_less_title, tmdb_movie.get('id', ''))

        if is_watched and not nfo_watched:
            add_playcount_to_nfo(movie_nfo_path)

        nfo_tags = get_movie_elements(nfo_root, "tag")
        appropriate_award_tags = [key for key, values in awards.items() if imdb_id in values]
        for missing_tag in [tag for tag in appropriate_award_tags if tag not in nfo_tags]:
            add_tag_to_movie_nfo(movie_nfo_path, missing_tag)

        for irrelevant_tag in [tag for tag in awards.keys() if tag in nfo_tags and imdb_id not in awards[tag]]:
            print_error("    irrelevant award tag: " + irrelevant_tag)
