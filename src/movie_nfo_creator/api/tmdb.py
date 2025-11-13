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

import time
import requests

from ..utils import print_error


def wait_for_tmdb_api_rate():
    """Wait for TMDB API rate limit."""
    message = "Sleeping 10 seconds to respect TMDb rate limit..."
    print(message, end='', flush=True)
    time.sleep(10)
    print('\r' + ' ' * len(message) + '\r', end='', flush=True)


def search_movie_tmdb(title, year=None, api_key=None):
    """Search for a movie on TMDB by title and optional year."""
    url = 'https://api.themoviedb.org/3/search/movie'
    params = {
        'api_key': api_key,
        'query': title,
        'include_adult': 'false',
        'language': 'fr-FR',
    }
    if year:
        params['year'] = year

    try:
        response = requests.get(url, params=params)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            wait_for_tmdb_api_rate()
            return search_movie_tmdb(title, year, api_key)
        else:
            raise

    data = response.json()
    results = data.get('results', [])

    if not results:
        return None

    title_cf = title.casefold()

    for result in results:
        # Check title and release year strictly
        result_title = result.get('title', '').casefold()
        result_original = result.get('original_title', '').casefold()
        release_date = result.get('release_date', '')
        release_year = int(release_date[:4]) if release_date else None

        if (result_title == title_cf or result_original == title_cf) and (year is None or release_year == year):
            return result

    # If no strict match
    return None


def get_movie_by_tmdb_id(tmdb_id, api_key=None):
    """Get movie details from TMDB by TMDB ID."""
    url = f'https://api.themoviedb.org/3/movie/{tmdb_id}'
    params = {
        'api_key': api_key,
        'language': 'fr-FR',
    }

    try:
        response = requests.get(url, params=params)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            wait_for_tmdb_api_rate()
            return get_movie_by_tmdb_id(tmdb_id, api_key)
        else:
            raise

    data = response.json()
    return data


def get_movie_by_imdb_id(imdb_id, api_key=None):
    """Get movie details from TMDB by IMDB ID."""
    url = f'https://api.themoviedb.org/3/find/{imdb_id}'
    params = {
        'api_key': api_key,
        'external_source': 'imdb_id',
        'language': 'fr-FR',
    }

    try:
        response = requests.get(url, params=params)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            wait_for_tmdb_api_rate()
            return get_movie_by_imdb_id(imdb_id, api_key)
        else:
            raise

    data = response.json()
    movie_results = data.get('movie_results', [])
    if movie_results:
        movie = movie_results[0]  # Should be unique for a movie
        movie['imdb_id'] = imdb_id  # Manual injection
        return movie
    else:
        print_error(f"No movie found for IMDb ID {imdb_id}")
        return None


def get_movie_credits(tmdb_id, api_key=None):
    """Get movie credits (cast and crew) from TMDB."""
    url = f'https://api.themoviedb.org/3/movie/{tmdb_id}/credits'
    params = {
        'api_key': api_key,
        'language': 'fr-FR',
    }

    try:
        response = requests.get(url, params=params)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            wait_for_tmdb_api_rate()
            return get_movie_credits(tmdb_id, api_key)
        else:
            raise

    return response.json()


def find_tmdb_movie(movie, api_key=None):
    """Find a movie on TMDB and return full details with IMDB ID."""
    tmdb_movie = search_movie_tmdb(movie[0], int(movie[1]), api_key)

    if tmdb_movie is None or not tmdb_movie.get("id"):
        print_error(str(movie) + " not found on TMDB")
        return None

    tmdb_movie = get_movie_by_tmdb_id(tmdb_movie['id'], api_key)

    if tmdb_movie is None:
        print_error(str(movie) + " not found on TMDB")
        return None

    if not tmdb_movie.get("imdb_id"):
        print_error(str(movie) + " IMDB id not found on TMDB")
        return None

    return tmdb_movie
