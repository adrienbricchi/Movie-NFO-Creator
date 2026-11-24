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

from .csv_utils import parse_movie_id_csv_into_id_array

AWARDS_DIR = Path(__file__).parent / 'awards'


def parse_awards():
    result = {}
    for award_source in [
        ('Oscar du meilleur film', 'oscar_best_picture.csv'),
        ('Oscar du meilleur film - Nomination', 'oscar_best_picture_nominee.csv'),
        ('Oscar du meilleur film international', 'oscar_best_international_picture.csv'),
        ("Oscar du meilleur film d'animation", 'oscar_best_animated_picture.csv'),
        ('César du meilleur film', 'cesar_best_picture.csv'),
        ("Palme d'Or", 'palme_d_or.csv'),
        ('César du meilleur film - Nomination', 'cesar_best_picture_nominee.csv'),
        ('Goya du meilleur film', 'goya_best_picture.csv'),
        ('BAFTA du meilleur film', 'bafta_best_film.csv'),
    ]:
        result[award_source[0]] = parse_movie_id_csv_into_id_array(AWARDS_DIR / award_source[1])

    return result
