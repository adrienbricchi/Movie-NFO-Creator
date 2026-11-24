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

from pathlib import Path


def folder_uri(folder):
    return Path(folder).absolute().as_uri() + '/'


def with_folder_link(filepath):
    return f"{filepath}  {folder_uri(Path(filepath).parent)}"


class FileHeader:

    def __init__(self, filepath):
        self.filepath = filepath
        self.printed = False

    def print(self):
        if not self.printed:
            print(with_folder_link(self.filepath))
            self.printed = True
