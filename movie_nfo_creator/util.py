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

import threading

from tqdm import tqdm

_error_buffer = None
_error_buffer_lock = threading.Lock()


def print_error(message):
    formatted = f"\033[91m{message}\033[0m"
    with _error_buffer_lock:
        if _error_buffer is not None:
            _error_buffer.append(formatted)
            return
    tqdm.write(formatted)


def start_error_buffering():
    global _error_buffer
    with _error_buffer_lock:
        _error_buffer = []


def buffered_error_count():
    with _error_buffer_lock:
        return len(_error_buffer) if _error_buffer is not None else 0


def flush_buffered_errors():
    global _error_buffer
    with _error_buffer_lock:
        messages, _error_buffer = _error_buffer, None
    for message in messages or []:
        tqdm.write(message)
