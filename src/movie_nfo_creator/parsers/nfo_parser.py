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

from ..utils import print_error


def parse_movie_nfo_imdb(filepath):
    """Parse IMDB ID from NFO file (expects IMDB URL as last line)."""
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


def parse_movie_nfo_xml(filepath):
    """Parse XML content from NFO file (all lines except the last IMDB URL line)."""
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
    """Get a single element value from movie XML root."""
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
    """Get multiple element values from movie XML root (for tags, genres, etc.)."""
    try:
        if root.tag != 'movie':
            print_error("Root tag is not <movie>")
            return None
        elements = root.findall(node_name)
        return [el.text.strip() for el in elements if el is not None and el.text]
    except ET.ParseError as e:
        print_error(f"XML parsing error: {e}")
        return None
