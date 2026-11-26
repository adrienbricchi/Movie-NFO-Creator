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
    removable: list


def find_tag_mismatches(nfo_tags, movie_ids, tag_lists, tags_to_remove=()):
    movie_ids = {movie_ids} if isinstance(movie_ids, str) else set(movie_ids)
    removable = [tag for tag in dict.fromkeys(nfo_tags or []) if tag in tags_to_remove]
    nfo_tags = [tag for tag in nfo_tags or [] if tag not in tags_to_remove]
    tag_lists = {tag: listed_ids for tag, listed_ids in tag_lists.items() if tag not in tags_to_remove}
    appropriate_tags = [tag for tag, listed_ids in tag_lists.items() if movie_ids & set(listed_ids)]
    return TagMismatches(
        missing=[tag for tag in appropriate_tags if tag not in nfo_tags],
        irrelevant=[tag for tag in tag_lists if tag in nfo_tags and tag not in appropriate_tags],
        unknown=[tag for tag in nfo_tags if tag not in tag_lists],
        removable=removable,
    )
