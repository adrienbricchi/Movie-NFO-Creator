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

import xml.etree.ElementTree as ET

from ..utils import print_error
from ..api import get_movie_credits


def indent_xml(elem, level=0):
    """Add indentation to XML elements for pretty printing."""
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


def prompt_create_movie_nfo(filepath, imdb_url, tmdb_movie, watched, api_key=None):
    """Prompt user before creating NFO file."""
    credits = get_movie_credits(tmdb_movie['id'], api_key)
    cast_list = [c['name'] for c in credits.get('cast', [])[:5]]
    directors = [c['name'] for c in credits.get('crew', []) if c.get('job') == 'Director']

    print("\n=== Movie Info ===")
    print(f"Title: {tmdb_movie.get('title')} ({tmdb_movie.get('release_date', 'N/A')[:4]})")
    print(f"Director: {directors[0] if directors else 'N/A'}")
    print("Cast: " + ", ".join(cast_list) if cast_list else "Cast: N/A")
    print("==================\n")

    answer = input("Do you want to create this NFO? [Y/n] ").strip().lower()
    if answer in ('', 'y', 'yes'):
        create_movie_nfo(filepath, imdb_url, tmdb_movie, watched)
    else:
        print("NFO creation skipped.")


def create_movie_nfo(filepath, imdb_id, tmdb_movie, watched):
    """Create a new NFO file."""
    title = tmdb_movie.get("title")
    title = title.replace('&', '&amp;')
    title = title.replace('\u2019', "'")
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


def add_tag_to_movie_nfo(nfo_path, tag_value):
    """Add a tag element to an existing NFO file."""
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


def add_playcount_to_nfo(nfo_path):
    """Add playcount element to an existing NFO file."""
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
