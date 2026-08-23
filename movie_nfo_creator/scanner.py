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

import glob
import os
import re


def find_mkv_files(root_dir):
    pattern = os.path.join(
        root_dir,
        '[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]',
        '**',
        '*.mkv'
    )
    return [path for path in glob.glob(pattern, recursive=True) if os.path.isfile(path)]


def _normalize_for_comparison(title, filename_lenient):
    normalized = title
    if filename_lenient:
        normalized = normalized.replace(':', '-')
        normalized = re.sub(r'\s?\?$', '', normalized)
        normalized = re.sub(r'\s+&\s+', ' and ', normalized)
        normalized = re.sub(r'\bet\b', 'and', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'\s\(.*?\)$', '', normalized)
    return normalized.casefold()


def are_roughly_equals(title_1, title_2, filename_lenient=True):
    return _normalize_for_comparison(title_1, filename_lenient) == _normalize_for_comparison(title_2, filename_lenient)


def parse_title_and_year(filename):
    # Matches: "Movie Title (optional stuff, 2024, optional).mkv"
    match = re.match(r'^(.*?)\s*\((?:.*?, )*(\d{4})(?:, .*?)*\)\.mkv$', filename)
    if match:
        title = match.group(1).strip()
        year = match.group(2)
        return title, year
    return None
