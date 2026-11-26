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
from datetime import timedelta

import requests
import requests_cache

from .scanner import are_roughly_equals
from .util import print_error

YEAR_TOLERANCE = 1


def wait_for_tmdb_api_rate():
    message = "Sleeping 10 seconds to respect TMDb rate limit..."
    print(message, end='', flush=True)
    time.sleep(10)
    print('\r' + ' ' * len(message) + '\r', end='', flush=True)


class TmdbClient:
    BASE_URL = 'https://api.themoviedb.org/3'

    def __init__(self, api_key, language='fr-FR'):
        self.api_key = api_key
        self.language = language
        self.session = requests_cache.CachedSession(
            'local',
            expire_after=timedelta(days=1),
            allowable_codes=(200,),
            wal=True,
        )

    def _request(self, url, params):
        try:
            return self.session.get(url, params=params)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait_for_tmdb_api_rate()
                return self._request(url, params)
            raise
        except Exception as e:
            print_error(f"Corrupted cache entry for {url}, deleting and refetching: {e}")
            prepared_request = self.session.prepare_request(requests.Request('GET', url, params=params))
            self.session.cache.delete(self.session.cache.create_key(prepared_request))
            return self.session.get(url, params=params)

    def find_movie(self, movie):
        tmdb_movie = self.search_movie(movie[0], int(movie[1]))

        if tmdb_movie is None or not tmdb_movie.get("id"):
            print_error(str(movie) + " not found on TMDB")
            return None

        tmdb_movie = self.get_movie_by_id(tmdb_movie['id'])

        if tmdb_movie is None:
            print_error(str(movie) + " not found on TMDB")
            return None

        return tmdb_movie

    def search_movie(self, title, year=None):
        url = f'{self.BASE_URL}/search/movie'
        params = {
            'api_key': self.api_key,
            'query': title,
            'include_adult': 'false',
            'language': self.language,
        }

        response = self._request(url, params)
        results = response.json().get('results', [])

        strict_match = self._best_result(results, title, year, fuzzy_title=False, year_tolerance=0)
        return strict_match or self._best_result(results, title, year, fuzzy_title=True, year_tolerance=YEAR_TOLERANCE)

    @staticmethod
    def _best_result(results, title, year, fuzzy_title, year_tolerance):
        title_cf = title.casefold()

        for result in results:
            result_title = result.get('title', '')
            result_original = result.get('original_title', '')
            release_date = result.get('release_date', '')
            release_year = int(release_date[:4]) if release_date else None

            if fuzzy_title:
                title_matches = are_roughly_equals(result_title, title) or are_roughly_equals(result_original, title)
            else:
                title_matches = result_title.casefold() == title_cf or result_original.casefold() == title_cf

            year_matches = year is None or (release_year is not None and abs(release_year - year) <= year_tolerance)

            if title_matches and year_matches:
                return result

        return None

    def get_movie_by_id(self, tmdb_id):
        url = f'{self.BASE_URL}/movie/{tmdb_id}'
        params = {
            'api_key': self.api_key,
            'language': self.language,
        }

        return self._request(url, params).json()

    def get_movie_by_imdb_id(self, imdb_id):
        url = f'{self.BASE_URL}/find/{imdb_id}'
        params = {
            'api_key': self.api_key,
            'external_source': 'imdb_id',
            'language': self.language,
        }

        data = self._request(url, params).json()
        movie_results = data.get('movie_results', [])
        if movie_results:
            movie = movie_results[0]  # Should be unique for a movie
            movie['imdb_id'] = imdb_id  # Manual injection
            return movie
        else:
            print_error(f"No movie found for IMDb ID {imdb_id}")
            return None

    def get_movie_credits(self, tmdb_id):
        url = f'{self.BASE_URL}/movie/{tmdb_id}/credits'
        params = {
            'api_key': self.api_key,
            'language': self.language,
        }

        return self._request(url, params).json()
