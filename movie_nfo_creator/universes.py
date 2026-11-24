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

UNIVERSES_DIR = Path(__file__).parent / 'universes'


def parse_universes():
    result = {}
    for universe_source in [
        ('Marvel Cinematic Universe', 'mcu.csv'),
        ('DC Extended Universe', 'dceu.csv'),
        ('DC Universe', 'dcu.csv'),
        ("Sony's Spider-Man Universe", 'ssu.csv'),
        ('X-Men', 'xmen.csv'),
        ('MonsterVerse', 'monsterverse.csv'),
        ('Godzilla - Shōwa era', 'godzilla_showa.csv'),
        ('Godzilla - Heisei era', 'godzilla_heisei.csv'),
        ('Godzilla - Millennium era', 'godzilla_millennium.csv'),
        ('Godzilla - Reiwa era', 'godzilla_reiwa.csv'),
        ('Wizarding World', 'wizarding_world.csv'),
        ('Conjuring Universe', 'conjuring.csv'),
        ('Star Wars', 'star_wars.csv'),
        ('Terre du Milieu', 'middle_earth.csv'),
        ('View Askewniverse', 'askewniverse.csv'),
        ('Fast and Furious', 'fast_and_furious.csv'),
        ('Miyagi-verse', 'miyagiverse.csv'),
        ('Universal Monsters - Classic era', 'universal_monsters_classic.csv'),
        ('Universal Monsters - Modern era', 'universal_monsters_modern.csv'),
        ('La Momie', 'the_mummy.csv'),
        ('Hammer Horror', 'hammer_horror.csv'),
        ('Rocky', 'rocky.csv'),
        ('Cars', 'cars.csv'),
        ('Moi, moche et méchant', 'despicable_me.csv'),
        ('DC Animated Universe', 'dcau.csv'),
        ('DC Animated Movie Universe', 'dcamu.csv'),
        ('DC Animated Tomorrowverse', 'dc_animated_tomorrowverse.csv'),
        ('DC Animated Standalone', 'dc_animated_standalone.csv'),
        ('James Bond 007', 'james_bond.csv'),
        ('Superman Cinematic Universe', 'superman_1978.csv'),
        ('Trilogie Cornetto', 'cornetto.csv'),
        ('Trilogie du dollar', 'dollars.csv'),
        ('Cycle Antoine Doinel', 'antoine_doinel.csv'),
        ('OSS 117', 'oss_117.csv'),
        ('Trilogie de la vengeance', 'vengeance.csv'),
        ('Cloverfield', 'cloverfield.csv'),
        ('La Planète des singes', 'planet_of_the_apes.csv'),
        ('Terminator', 'terminator.csv'),
        ('Halloween', 'halloween.csv'),
        ('Vendredi 13', 'friday_the_13th.csv'),
        ('Freddy', 'nightmare_on_elm_street.csv'),
        ('Massacre à la tronçonneuse', 'texas_chainsaw_massacre.csv'),
        ('Hellraiser', 'hellraiser.csv'),
        ('John Wick', 'john_wick.csv'),
        ('Star Trek', 'star_trek.csv'),
        ('SOS Fantômes', 'ghostbusters.csv'),
        ('Alien', 'alien.csv'),
        ('Predator', 'predator.csv'),
        ('Eastrail 177', 'eastrail_177.csv'),
        ('Batman Burtonverse', 'batman_burtonverse.csv'),
        ('Transformers', 'transformers.csv'),
        ("L'Exorciste", 'exorcist.csv'),
        ('Evil Dead', 'evil_dead.csv'),
        ('Mad Max', 'mad_max.csv'),
    ]:
        result[universe_source[0]] = parse_movie_id_csv_into_id_array(UNIVERSES_DIR / universe_source[1])

    return result
