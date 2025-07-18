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
import requests
import glob
import time
import csv
import os
import re
import xml.etree.ElementTree as ET


TMDB_API_KEY = None
ROOT_PATH = None
LETTERBOXD_WATCHED_FILES = None


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
            })
    return movies


def is_movie_in_letterboxd_list(letterboxd_data, title, year):
    for letterboxd_movie in letterboxd_data:
        if letterboxd_movie['title'].casefold() == title.casefold() and letterboxd_movie['year'] == year:
            return True
    return False


def get_tmdb_movie(movie):
    tmdb_movie = search_movie_tmdb(movie[0], int(movie[1]))

    if tmdb_movie is None or not tmdb_movie.get("id"):
        print(str(movie) + " not found on TMDB")
        return None

    tmdb_movie = get_movie_details(tmdb_movie['id'])

    if tmdb_movie is None:
        print(str(movie) + " not found on TMDB")
        return None

    if not tmdb_movie.get("imdb_id"):
        print(str(movie) + " IMDB id not found on TMDB")
        return None

    return tmdb_movie


def search_movie_tmdb(title, year=None):
    url = 'https://api.themoviedb.org/3/search/movie'
    params = {
        'api_key': TMDB_API_KEY,
        'query': title,
        'include_adult': 'false',
        'language': 'fr-FR',
    }
    if year:
        params['year'] = year
    response = requests.get(url, params=params)
    data = response.json()
    results = data.get('results', [])
    if results:
        return results[0]
    return None


def get_movie_details(tmdb_id):
    url = f'https://api.themoviedb.org/3/movie/{tmdb_id}'
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'fr-FR',
    }
    response = requests.get(url, params=params)
    data = response.json()
    return data


def load_properties(filepath):
    config = configparser.ConfigParser()
    config.read(filepath)
    return config


def find_mkv_files(root_dir):
    pattern = os.path.join(
        root_dir,
        '[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]',
        '**',
        '*.mkv'
    )
    return glob.glob(pattern, recursive=True)


def parse_title_and_year(filename):
    # Matches: "Movie Title (optional stuff, 2024, optional).mkv"
    match = re.match(r'^(.*?)\s*\((?:.*?, )*(\d{4})(?:, .*?)*\)\.mkv$', filename)
    if match:
        title = match.group(1).strip()
        year = match.group(2)
        return (title, year)
    return None


def parse_movie_nfo(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if len(lines) < 2:
        print("File too short or invalid format.")
        return None

    xml_content = ''.join(lines[:-1])  # All lines except the last one

    try:
        root = ET.fromstring(xml_content)
        return root
    except ET.ParseError as e:
        print(f"XML parsing error: {e}")
        return None


def get_movie_title(root):
    try:
        if root.tag != 'movie':
            print("Root tag is not <movie>")
            return None
        title_element = root.find('title')
        if title_element is not None:
            return title_element.text.strip()
        else:
            print("<title> tag not found under <movie>")
            return None
    except ET.ParseError as e:
        print(f"XML parsing error: {e}")
        return None



if __name__ == '__main__':

    config = load_properties('config.ini')
    ROOT_PATH = config.get('paths', 'root_dir', fallback=None)
    TMDB_API_KEY = config.get('tmdb', 'api_key', fallback=None)
    LETTERBOXD_WATCHED_FILES = config.get('letterboxd', 'watched_file', fallback=None)

    if not ROOT_PATH:
        print("config.ini root_dir not found")
        exit(1)

    if not TMDB_API_KEY:
        print("config.ini api_key not found")
        exit(1)

    if not LETTERBOXD_WATCHED_FILES:
        print("config.ini watched_file not found")
        exit(1)

    letterboxd_movies = parse_letterboxd_csv(LETTERBOXD_WATCHED_FILES)

    filepaths = find_mkv_files(ROOT_PATH)
    for i, filepath in enumerate(filepaths):

        filename = os.path.basename(filepath)
        movie = parse_title_and_year(filename)

        if movie is None:
            # print("No match: " + filename)
            continue

        # We have to wait to respect the TMDB API limit
        if i % 20 == 0 and i > 0:
            message = f"Sleeping 10 seconds to respect TMDb rate limit..."
            print(message, end='', flush=True)
            time.sleep(10)
            print('\r' + ' ' * len(message) + '\r', end='', flush=True)

        tmdb_movie = get_tmdb_movie(movie)
        if tmdb_movie is None:
            continue

        imdb_id = tmdb_movie.get('imdb_id')
        tmdb_title = tmdb_movie.get('title')
        tmdb_original_title = tmdb_movie.get('original_title')
        tmdb_release_date = tmdb_movie.get('release_date')
        tmdb_release_year = int(tmdb_release_date[:4]) if tmdb_release_date else None
        watched = is_movie_in_letterboxd_list(letterboxd_movies, tmdb_original_title, tmdb_release_year)

        print(str(movie) + " " + imdb_id + " " + str(watched))

        folder_name = os.path.dirname(filepath)
        nfo_root = parse_movie_nfo(os.path.join(folder_name, 'movie.nfo'))

        if nfo_root is None:
            print("Cannot parse NFO: " + filepath)
            continue

        nfo_title = get_movie_title(nfo_root)
        if nfo_title is None:
            print("Cannot parse NFO title: " + filepath)
            continue

        if nfo_title.casefold() != tmdb_movie['title'].casefold() or nfo_title.casefold() != movie[0].casefold():
            print("    Title difference found")
            print("    NFO movie title: " + nfo_title)
            print("    TMDB movie title: " + tmdb_title)
            print("    File movie title: " + movie[0])
