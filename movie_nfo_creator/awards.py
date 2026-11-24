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
from pathlib import Path

from .csv_utils import parse_movie_id_csv_into_id_array

AWARDS_DIR = Path(__file__).parent / 'awards'


@dataclass(frozen=True)
class AwardSource:
    tag: str
    filename: str
    wikidata_award: str
    nominees_only: bool = False
    wikidata_false_positives: tuple = ()


AWARD_SOURCES = [
    AwardSource('Oscar du meilleur film', 'oscar_best_picture.csv', 'Q102427'),
    AwardSource('Oscar du meilleur film - Nomination', 'oscar_best_picture_nominee.csv', 'Q102427', nominees_only=True),
    AwardSource('Oscar du meilleur film international', 'oscar_best_international_picture.csv', 'Q105304'),
    AwardSource("Oscar du meilleur film d'animation", 'oscar_best_animated_picture.csv', 'Q106800'),
    # tt0102609 is Other People's Money (1991), mixed up on Wikidata with L'Argent des autres (1978).
    AwardSource('César du meilleur film', 'cesar_best_picture.csv', 'Q645595', wikidata_false_positives=('tt0102609',)),
    AwardSource("Palme d'Or", 'palme_d_or.csv', 'Q179808'),
]


def parse_awards():
    return {source.tag: parse_movie_id_csv_into_id_array(AWARDS_DIR / source.filename) for source in AWARD_SOURCES}
