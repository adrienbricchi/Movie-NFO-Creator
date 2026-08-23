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


def _normalize_for_comparison(title, filename_lenient, colon_dash='-'):
    # TMDb's fr-FR titles use a non-breaking space before ':' (French
    # typographic convention); normalize all whitespace to a plain space so
    # that doesn't register as a title difference.
    normalized = re.sub(r'\s+', ' ', title)
    # TMDb uses a curly right single quote (U+2019) for apostrophes while
    # NFOs/filenames typically use a straight one (U+0027); same character.
    normalized = normalized.replace('’', "'")
    # '&' and 'et' are both legitimate spellings of the same French movie
    # title (e.g. TMDb switching "Wallace et Gromit" to "Wallace & Gromit"),
    # so this equivalence applies everywhere, not just filename comparisons.
    normalized = re.sub(r'\s+&\s+', ' and ', normalized)
    normalized = re.sub(r'\bet\b', 'and', normalized, flags=re.IGNORECASE)
    if filename_lenient:
        normalized = re.sub(r'mission\s*:\s*impossible', 'mission impossible', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\s*:', colon_dash, normalized)
        normalized = normalized.replace('/', '-')
        normalized = normalized.replace('—', '-')
        normalized = normalized.replace('–', '-')
        normalized = re.sub(r'\s?\?$', '', normalized)
        # '*' can't appear in filenames at all (like ':'), so it's just
        # dropped rather than substituted (e.g. "Thunderbolts*" on disk
        # becomes "Thunderbolts").
        normalized = normalized.replace('*', '')
    normalized = re.sub(r'\s\(.*?\)$', '', normalized)
    return normalized.casefold()


def are_roughly_equals(title_1, title_2, filename_lenient=True):
    if not filename_lenient:
        return _normalize_for_comparison(title_1, False) == _normalize_for_comparison(title_2, False)

    # A ':' can legitimately show up in a filename as either '-' or ' -'
    # (filenames can't contain ':' at all), so try both interpretations.
    # A hyphen that's actually part of the title (no ':' involved on either
    # side) never goes through this - its spacing stays significant.
    for colon_dash in ('-', ' -'):
        title_1_normalized = _normalize_for_comparison(title_1, True, colon_dash)
        title_2_normalized = _normalize_for_comparison(title_2, True, colon_dash)
        if title_1_normalized == title_2_normalized:
            return True
    return False


def parse_title_and_year(filename):
    # Matches: "Movie Title (optional stuff, 2024, optional).mkv"
    match = re.match(r'^(.*?)\s*\((?:.*?, )*(\d{4})(?:, .*?)*\)\.mkv$', filename)
    if match:
        title = match.group(1).strip()
        year = match.group(2)
        return title, year
    return None
