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

from dataclasses import dataclass


@dataclass(frozen=True)
class TagMismatches:
    missing: list
    irrelevant: list
    unknown: list


def find_tag_mismatches(nfo_tags, imdb_id, tag_lists):
    nfo_tags = nfo_tags or []
    appropriate_tags = [tag for tag, imdb_ids in tag_lists.items() if imdb_id in imdb_ids]
    return TagMismatches(
        missing=[tag for tag in appropriate_tags if tag not in nfo_tags],
        irrelevant=[tag for tag in tag_lists if tag in nfo_tags and imdb_id not in tag_lists[tag]],
        unknown=[tag for tag in nfo_tags if tag not in tag_lists],
    )
