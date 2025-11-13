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


def print_error(message):
    """Print error messages in red."""
    print(f"\033[91m{message}\033[0m")


def are_roughly_equals(title_1, title_2):
    """Check if two movie titles are roughly equal (ignoring case and some punctuation)."""
    title_1_cleaned = title_1.replace(':', '-')
    title_2_cleaned = title_2.replace(':', '-')
    title_1_cleaned = re.sub(r'\s\(.*?\)$', '', title_1_cleaned)
    title_2_cleaned = re.sub(r'\s\(.*?\)$', '', title_2_cleaned)
    return title_1_cleaned.casefold() == title_2_cleaned.casefold()


def parse_title_and_year(filename):
    """Parse title and year from filename.

    Matches: "Movie Title (optional stuff, 2024, optional).mkv"
    """
    match = re.match(r'^(.*?)\s*\((?:.*?, )*(\d{4})(?:, .*?)*\)\.mkv$', filename)
    if match:
        title = match.group(1).strip()
        year = match.group(2)
        return title, year
    return None
