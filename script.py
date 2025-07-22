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


def print_error(message):
    print(f"\033[91m{message}\033[0m")


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
        if are_roughly_equals(letterboxd_movie['title'], title) and letterboxd_movie['year'] == year:
            return True
    return False


def wait_for_tmdb_api_rate():
    message = f"Sleeping 10 seconds to respect TMDb rate limit..."
    print(message, end='', flush=True)
    time.sleep(10)
    print('\r' + ' ' * len(message) + '\r', end='', flush=True)


def find_tmdb_movie(movie):

    tmdb_movie = search_movie_tmdb(movie[0], int(movie[1]))

    if tmdb_movie is None or not tmdb_movie.get("id"):
        print_error(str(movie) + " not found on TMDB")
        return None

    tmdb_movie = get_movie_by_tmdb_id(tmdb_movie['id'])

    if tmdb_movie is None:
        print_error(str(movie) + " not found on TMDB")
        return None

    if not tmdb_movie.get("imdb_id"):
        print_error(str(movie) + " IMDB id not found on TMDB")
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

    try:
        response = requests.get(url, params=params)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            wait_for_tmdb_api_rate()
            return search_movie_tmdb(title, year)
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


def get_movie_by_tmdb_id(tmdb_id):
    url = f'https://api.themoviedb.org/3/movie/{tmdb_id}'
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'fr-FR',
    }

    try:
        response = requests.get(url, params=params)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            wait_for_tmdb_api_rate()
            return get_movie_by_tmdb_id(tmdb_id)
        else:
            raise

    data = response.json()
    return data


def get_movie_by_imdb_id(imdb_id):
    url = f'https://api.themoviedb.org/3/find/{imdb_id}'
    params = {
        'api_key': TMDB_API_KEY,
        'external_source': 'imdb_id',
        'language': 'fr-FR',
    }

    try:
        response = requests.get(url, params=params)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            wait_for_tmdb_api_rate()
            return get_movie_by_imdb_id(imdb_id)
        else:
            raise

    data = response.json()
    movie_results = data.get('movie_results', [])
    if movie_results:
        movie = movie_results[0] # Should be unique for a movie
        movie['imdb_id'] = imdb_id  # Manual injection
        return movie
    else:
        print_error(f"No movie found for IMDb ID {imdb_id}")
        return None


def get_movie_credits(tmdb_id):
    url = f'https://api.themoviedb.org/3/movie/{tmdb_id}/credits'
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'fr-FR',
    }

    try:
        response = requests.get(url, params=params)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            wait_for_tmdb_api_rate()
            return get_movie_credits(tmdb_id)
        else:
            raise

    return response.json()


def load_properties(filepath):
    config = configparser.ConfigParser()
    with open(filepath, 'r', encoding='utf-8') as file:
        config.read_file(file)
    return config


def find_mkv_files(root_dir):
    pattern = os.path.join(
        root_dir,
        '[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]',
        '**',
        '*.mkv'
    )
    return glob.glob(pattern, recursive=True)


def are_roughly_equals(title_1, title_2):
    title_1_cleaned = title_1.replace(':', '-')
    title_2_cleaned = title_2.replace(':', '-')
    title_1_cleaned = re.sub(r'\s\(.*?\)$', '', title_1_cleaned)
    title_2_cleaned = re.sub(r'\s\(.*?\)$', '', title_2_cleaned)
    return title_1_cleaned.casefold() == title_2_cleaned.casefold()


def parse_title_and_year(filename):
    # Matches: "Movie Title (optional stuff, 2024, optional).mkv"
    match = re.match(r'^(.*?)\s*\((?:.*?, )*(\d{4})(?:, .*?)*\)\.mkv$', filename)
    if match:
        title = match.group(1).strip()
        year = match.group(2)
        return title, year
    return None


def parse_movie_nfo_imdb(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if not lines:
                return None
            last_line = lines[-1].strip()
            match = re.match(r'^https://www\.imdb\.com/title/(tt\d+)$', last_line)
            if match:
                return match.group(1)
            if re.match(r'^https?://(www\.)?imdb\.com/title/tt\d+/?$', last_line):
                print_error(f"Last line is a poor IMDb URL: {last_line}")
                return None
            if re.match(r'^ https://www.themoviedb.org/.*?$', last_line):
                return None
            else:
                print_error(f"Last line is not a valid IMDb URL: {last_line}")
                return None
    except Exception as e:
        print_error(f"Error reading NFO file {filepath}: {e}")
        return None


def prompt_create_movie_nfo(filepath, imdb_url, tmdb_movie, watched):

    credits = get_movie_credits(tmdb_movie['id'])
    cast_list = [c['name'] for c in credits.get('cast', [])[:5]]
    directors = [c['name'] for c in credits.get('crew', []) if c.get('job') == 'Director']

    print("\n=== Movie Info ===")
    print(f"Title: {tmdb_movie.get('title')} ({tmdb_movie.get('release_date', 'N/A')[:4]})")
    print(f"Director: {directors[0] if directors else 'N/A'}")
    print("Cast: " + ", ".join(cast_list) if cast_list else "Cast: N/A")
    print("==================\n")

    answer = input(f"Do you want to create this NFO? [Y/n] ").strip().lower()
    if answer in ('', 'y', 'yes'):
        create_movie_nfo(filepath, imdb_url, tmdb_movie, watched)
    else:
        print("NFO creation skipped.")


def create_movie_nfo(filepath, imdb_id, tmdb_movie, watched):
    title = tmdb_movie.get("title")
    title = title.replace('&', '&amp;')
    title = title.replace('’', "'")
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<movie>\n')
            f.write(f'  <title>{title}</title>\n')
            if watched:
                f.write('  <playcount>1</playcount>\n')
            f.write('</movie>\n')
            f.write("https://www.imdb.com/title/" + imdb_id)
        print(f"NFO file created at {filepath}")
    except Exception as e:
        print_error(f"Error writing NFO file {filepath}: {e}")


def parse_movie_nfo_xml(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return None

    if len(lines) < 2:
        print_error("File too short or invalid format.")
        return None

    xml_content = ''.join(lines[:-1])  # All lines except the last one

    try:
        root = ET.fromstring(xml_content)
        return root
    except ET.ParseError as e:
        print_error(f"XML parsing error: {e}")
        return None


def parse_awards():
    result = {}
    for award_source in [
        ('Oscar du meilleur film', 'oscar_best_picture.csv'),
        ('Oscar du meilleur film - Nomination', 'oscar_best_picture_nominee.csv'),
        ('Oscar du meilleur film international', 'oscar_best_international_picture.csv'),
        ("Oscar du meilleur film d'animation", 'oscar_best_animated_picture.csv'),
        ('César du meilleur film', 'cesar_best_picture.csv'),
        ("Palme d'Or", 'palme_d_or.csv'),
    ]:
        result[award_source[0]] = parse_movie_id_csv_into_id_array("./awards/" + award_source[1])

    return result


def parse_movie_id_csv_into_id_array(csv_path):
    result = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)  # Skip header
        for row in reader:
            title, imdb_id = row
            result.append(imdb_id)
    return result


def get_movie_element(root, node_name):
    try:
        if root.tag != 'movie':
            print_error("Root tag is not <movie>")
            return None
        title_element = root.find(node_name)
        if title_element is not None:
            return title_element.text.strip()
        else:
            return None
    except ET.ParseError as e:
        print_error(f"XML parsing error: {e}")
        return None


def get_movie_elements(root, node_name):
    try:
        if root.tag != 'movie':
            print_error("Root tag is not <movie>")
            return None
        elements = root.findall(node_name)
        return [el.text.strip() for el in elements if el is not None and el.text]
    except ET.ParseError as e:
        print_error(f"XML parsing error: {e}")
        return None


def indent_xml(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
           elem.text = i + "  "
        for child in elem:
            indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i


def add_tag_to_movie_nfo(nfo_path, tag_value):
    try:
        with open(nfo_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if len(lines) < 2:
            print_error(f"NFO file too short: {nfo_path}")
            return False

        xml_content = ''.join(lines[:-1])  # All lines except the last (IMDb link)
        imdb_link = lines[-1].rstrip('\n')

        root = ET.fromstring(xml_content)
        if root.tag != 'movie':
            print_error(f"Root tag is not <movie> in {nfo_path}")
            return False

        # Add the new <tag>
        new_element = ET.Element("tag")
        new_element.text = tag_value
        root.append(new_element)

        indent_xml(root)

        # Write back the XML with header and IMDb link
        try:
            with open(nfo_path, 'w', encoding='utf-8') as f:
                tree = ET.ElementTree(root)
                tree.write(f, encoding='unicode', xml_declaration=True)
                f.write('\n' + imdb_link.strip() + '\n')
            print(f"Tag <tag>{tag_value}</tag> added and file updated: {nfo_path}")
        except Exception as e:
            print_error(f"Error writing NFO with header: {e}")

        return True

    except Exception as e:
        print_error(f"Error updating NFO {nfo_path}: {e}")
        return False


def ask_and_append_movie_to_watched_override(title, imdb_id):
    answer = input(f"Add movie '{title}' ({imdb_id}) to watched_override.csv? [Y/n]: ").strip().lower()
    if answer in ['', 'y', 'yes']:
        append_movie_to_csv("watched_override.csv", title, imdb_id)
    else:
        print("Skipped.")


def append_movie_to_csv(csv_path, title, imdb_id):
    file_exists = os.path.isfile(csv_path)
    try:
        with open(csv_path, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['title', 'imdb_id'])
            writer.writerow([title, imdb_id])
        print(f"Movie '{title}' ({imdb_id}) added to {csv_path}")
    except Exception as e:
        print(f"Error writing to CSV: {e}")


def add_playcount_to_nfo(nfo_path):
    try:
        with open(nfo_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if len(lines) < 2:
            print(f"File too short: {nfo_path}")
            return False

        xml_content = ''.join(lines[:-1])
        imdb_link = lines[-1].rstrip('\n')

        root = ET.fromstring(xml_content)
        if root.tag != 'movie':
            print(f"Invalid root tag in {nfo_path}")
            return False

        if root.find('playcount') is None:
            playcount_elem = ET.Element('playcount')
            playcount_elem.text = '1'
            root.append(playcount_elem)
        else:
            print(f"'playcount' already present in {nfo_path}")
            return False

        indent_xml(root)

        with open(nfo_path, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n')
            f.write(ET.tostring(root, encoding='unicode'))
            f.write('\n' + imdb_link.strip() + '\n')

        print(f"'playcount' added with indent to {nfo_path}")
        return True

    except Exception as e:
        print(f"Error updating playcount in {nfo_path}: {e}")
        return False


if __name__ == '__main__':

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

        tmdb_movie = get_movie_by_imdb_id(imdb_id) if imdb_id else find_tmdb_movie(movie)
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
            prompt_create_movie_nfo(movie_nfo_path, imdb_id, tmdb_movie, letterboxd_watched)
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