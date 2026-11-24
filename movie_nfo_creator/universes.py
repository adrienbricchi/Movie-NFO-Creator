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
        ('Alien', 'alien.csv'),
        ('Astérix', 'asterix.csv'),
        ('Batman Burtonverse', 'batman_burtonverse.csv'),
        ('Blade', 'blade.csv'),
        ('Candyman', 'candyman.csv'),
        ('Cars', 'cars.csv'),
        ('Chucky', 'chucky.csv'),
        ('Cloverfield', 'cloverfield.csv'),
        ('Conjuring Universe', 'conjuring.csv'),
        ('Cycle Antoine Doinel', 'antoine_doinel.csv'),
        ('DC Animated Movie Universe', 'dcamu.csv'),
        ('DC Animated Standalone', 'dc_animated_standalone.csv'),
        ('DC Animated Tomorrowverse', 'dc_animated_tomorrowverse.csv'),
        ('DC Animated Universe', 'dcau.csv'),
        ('DC Extended Universe', 'dceu.csv'),
        ('DC Universe', 'dcu.csv'),
        ('Destination finale', 'final_destination.csv'),
        ('Die Hard', 'die_hard.csv'),
        ('Dragons', 'how_to_train_your_dragon.csv'),
        ('Eastrail 177', 'eastrail_177.csv'),
        ('Evil Dead', 'evil_dead.csv'),
        ('Fast and Furious', 'fast_and_furious.csv'),
        ('Freddy', 'nightmare_on_elm_street.csv'),
        ('Godzilla - Heisei era', 'godzilla_heisei.csv'),
        ('Godzilla - Millennium era', 'godzilla_millennium.csv'),
        ('Godzilla - Reiwa era', 'godzilla_reiwa.csv'),
        ('Godzilla - Shōwa era', 'godzilla_showa.csv'),
        ('Halloween', 'halloween.csv'),
        ('Hammer Horror', 'hammer_horror.csv'),
        ('Hellraiser', 'hellraiser.csv'),
        ('Hunger Games', 'hunger_games.csv'),
        ('Indiana Jones', 'indiana_jones.csv'),
        ('James Bond 007', 'james_bond.csv'),
        ('Jason Bourne', 'bourne.csv'),
        ('John Wick', 'john_wick.csv'),
        ('Jurassic Park', 'jurassic_park.csv'),
        ('Kingsman', 'kingsman.csv'),
        ('Kung Fu Panda', 'kung_fu_panda.csv'),
        ("L'Âge de glace", 'ice_age.csv'),
        ("L'Exorciste", 'exorcist.csv'),
        ('La Momie', 'the_mummy.csv'),
        ('La Planète des singes', 'planet_of_the_apes.csv'),
        ('Le Labyrinthe', 'maze_runner.csv'),
        ('Mad Max', 'mad_max.csv'),
        ('Marvel Cinematic Universe', 'mcu.csv'),
        ('Massacre à la tronçonneuse', 'texas_chainsaw_massacre.csv'),
        ('Matrix', 'matrix.csv'),
        ('Men in Black', 'men_in_black.csv'),
        ('Mission impossible', 'mission_impossible.csv'),
        ('Miyagi-verse', 'miyagiverse.csv'),
        ('Moi, moche et méchant', 'despicable_me.csv'),
        ('MonsterVerse', 'monsterverse.csv'),
        ('Mortal Kombat', 'mortal_kombat.csv'),
        ('OSS 117', 'oss_117.csv'),
        ('Pirates des Caraïbes', 'pirates_of_the_caribbean.csv'),
        ('Predator', 'predator.csv'),
        ('Rambo', 'rambo.csv'),
        ('Resident Evil', 'resident_evil.csv'),
        ('Rocky', 'rocky.csv'),
        ('Romero - Living Dead', 'romero_dead.csv'),
        ('Scream', 'scream.csv'),
        ('Shrek', 'shrek.csv'),
        ("Sony's Spider-Man Universe", 'ssu.csv'),
        ('SOS Fantômes', 'ghostbusters.csv'),
        ('Star Trek', 'star_trek.csv'),
        ('Star Wars', 'star_wars.csv'),
        ('Superman Cinematic Universe', 'superman_1978.csv'),
        ('Terminator', 'terminator.csv'),
        ('Terre du Milieu', 'middle_earth.csv'),
        ('The Purge', 'the_purge.csv'),
        ('Toy Story', 'toy_story.csv'),
        ('Transformers', 'transformers.csv'),
        ('Trilogie Cornetto', 'cornetto.csv'),
        ("Trilogie de l'Apocalypse", 'apocalypse_trilogy.csv'),
        ('Trilogie de la vengeance', 'vengeance.csv'),
        ('Trilogie du dollar', 'dollars.csv'),
        ('Trilogie marseillaise', 'marseille.csv'),
        ('Twilight', 'twilight.csv'),
        ('Underworld', 'underworld.csv'),
        ('Universal Monsters - Classic era', 'universal_monsters_classic.csv'),
        ('Universal Monsters - Modern era', 'universal_monsters_modern.csv'),
        ('Vendredi 13', 'friday_the_13th.csv'),
        ('View Askewniverse', 'askewniverse.csv'),
        ('Wizarding World', 'wizarding_world.csv'),
        ('X-Men', 'xmen.csv'),
    ]:
        result[universe_source[0]] = parse_movie_id_csv_into_id_array(UNIVERSES_DIR / universe_source[1])

    return result
