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

import re
import xml.etree.ElementTree as ET

from .csv_utils import append_movie_to_csv
from .util import print_error


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


def prompt_create_movie_nfo(filepath, imdb_url, tmdb_movie, watched, tmdb_client):

    credits = tmdb_client.get_movie_credits(tmdb_movie['id'])
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
