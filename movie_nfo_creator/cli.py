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

import argparse
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from .awards import parse_awards
from .config import load_config
from .letterboxd import letterboxd_id_from_url, parse_letterboxd_csv, resolve_letterboxd_watched
from .mkv import (
    extract_chapter_start_times,
    format_size_fr,
    has_no_chapters,
    has_overlapping_chapters,
    missing_audio_languages,
    missing_hdr_tag_reason,
    probe_mediainfo,
    probe_mkv,
    reencode_reason,
    reencode_savings_bytes,
    repetitive_chapters_reason,
    resolution_tag_mismatch_reason,
    uhd_reencode_reason,
    unwarranted_hdr_tag_reason,
)
from .mkv_cache import load_cached_deep_analysis, store_deep_analysis_cache
from .movies import ask_and_mark_watched, load_movies_db, upsert_movie
from .nfo import (
    add_playcount_to_nfo,
    add_tag_to_movie_nfo,
    get_movie_element,
    get_movie_elements,
    parse_movie_nfo_imdb,
    parse_movie_nfo_xml,
    prompt_create_movie_nfo,
)
from .scanner import (
    are_roughly_equals,
    declared_resolution_class,
    find_mkv_files,
    has_hdr_tag,
    is_vost,
    is_web,
    parse_title_and_year,
)
from .rules import RankedRule, RankedRuleRunner, SimpleRule, SimpleRuleRunner
from .tmdb import TmdbClient
from .util import buffered_error_count, flush_buffered_errors, print_error, start_error_buffering

TMDB_FETCH_WORKERS = 8
NFO_PARSE_WORKERS = 8
COMPARISON_WORKERS = 8
MOVIES_DB_PATH = 'local.sqlite'

SIMPLE_RULES = [
    SimpleRule(
        'missing_track_languages', 'Missing audio language tracks',
        lambda analysis: (
            ["missing audio track(s) for: " + ", ".join(analysis['missing_track_languages'])]
            if analysis['missing_track_languages'] else None
        ),
    ),
    SimpleRule(
        'chapter_issues', 'Chapter issues found',
        lambda analysis: (
            ["chapter issue: " + issue for issue in analysis['chapter_issues']]
            if analysis['chapter_issues'] else None
        ),
    ),
    SimpleRule(
        'missing_hdr_tag', 'Missing HDR tag in filename',
        lambda analysis: (
            ["missing HDR tag in filename for: " + analysis['missing_hdr_tag']]
            if analysis['missing_hdr_tag'] else None
        ),
    ),
    SimpleRule(
        'unwarranted_hdr_tag', 'HDR tag in filename but non-HDR video',
        lambda analysis: [analysis['unwarranted_hdr_tag']] if analysis['unwarranted_hdr_tag'] else None,
    ),
    SimpleRule(
        'resolution_tag_mismatch', 'Resolution tag mismatch',
        lambda analysis: [analysis['resolution_tag_mismatch']] if analysis['resolution_tag_mismatch'] else None,
    ),
    SimpleRule(
        'folder_name_mismatch', 'File/folder name mismatch',
        lambda analysis: (
            ["file name doesn't match parent folder name"] if analysis['folder_name_mismatch'] else None
        ),
    ),
]

REENCODE_RULE = RankedRule(
    'reencode', 'Re-encode candidates',
    lambda analysis: (
        (
            ["reencode candidate: " + reason for reason in analysis['reencode_reasons']],
            analysis['reencode_savings_bytes'],
        )
        if analysis['reencode_reasons'] else None
    ),
    per_file_value_label='estimated savings',
    total_value_label='Estimated re-encode savings',
    ranked_header='Top 5 most profitable re-encodes:',
    format_value=format_size_fr,
)


def fetch_tmdb_movie(tmdb_client, movie, imdb_id):
    return tmdb_client.get_movie_by_imdb_id(imdb_id) if imdb_id else tmdb_client.find_movie(movie)


def ensure_mediainfo(filepath, mkv_info, config):
    needs_mediainfo_probe = mkv_info is not None and 'hdr_formats' not in mkv_info
    if not needs_mediainfo_probe:
        return mkv_info, False

    mediainfo_info = probe_mediainfo(filepath, config.mediainfo_dir)
    if mediainfo_info is None:
        return mkv_info, False

    mkv_info.update(mediainfo_info)
    return mkv_info, True


def analyze_movie(entry, tmdb_movie, nfo_root, movies_db, letterboxd_movies, awards, config, no_cache=False):
    filepath, movie, movie_nfo_path, _ = entry

    result = {
        'skip': tmdb_movie is None,
        'missing_track_languages': [],
        'reencode_reasons': [],
        'reencode_savings_bytes': None,
        'chapter_issues': [],
        'missing_hdr_tag': None,
        'unwarranted_hdr_tag': None,
        'resolution_tag_mismatch': None,
        'folder_name_mismatch': (
            os.path.splitext(os.path.basename(filepath))[0] != os.path.basename(os.path.dirname(filepath))
        ),
    }

    cached = None if no_cache else load_cached_deep_analysis(MOVIES_DB_PATH, filepath)
    if cached is not None:
        mkv_info, chapter_starts = cached
        mkv_info, mediainfo_backfilled = ensure_mediainfo(filepath, mkv_info, config)
        if mediainfo_backfilled:
            store_deep_analysis_cache(MOVIES_DB_PATH, filepath, mkv_info, chapter_starts)
    else:
        mkv_info = probe_mkv(filepath, config.mkvtoolnix_dir)
        chapter_starts = extract_chapter_start_times(filepath, config.mkvtoolnix_dir)
        mkv_info, _ = ensure_mediainfo(filepath, mkv_info, config)
        store_deep_analysis_cache(MOVIES_DB_PATH, filepath, mkv_info, chapter_starts)

    if mkv_info is not None:
        original_language = tmdb_movie.get('original_language') if tmdb_movie else None
        require_french = not is_vost(os.path.basename(filepath))
        result['missing_track_languages'] = missing_audio_languages(mkv_info, original_language, require_french)
        result['reencode_reasons'] = [
            reason for reason in (reencode_reason(mkv_info), uhd_reencode_reason(mkv_info)) if reason
        ]
        if result['reencode_reasons']:
            result['reencode_savings_bytes'] = reencode_savings_bytes(mkv_info)
        has_hdr_tag_in_filename = has_hdr_tag(os.path.basename(filepath))
        result['missing_hdr_tag'] = missing_hdr_tag_reason(mkv_info, has_hdr_tag_in_filename)
        result['unwarranted_hdr_tag'] = unwarranted_hdr_tag_reason(mkv_info, has_hdr_tag_in_filename)
        result['resolution_tag_mismatch'] = resolution_tag_mismatch_reason(
            mkv_info, declared_resolution_class(os.path.basename(filepath))
        )

    if chapter_starts is not None:
        if has_no_chapters(chapter_starts) and not is_web(os.path.basename(filepath)):
            result['chapter_issues'].append("no chapters")
        if has_overlapping_chapters(chapter_starts):
            result['chapter_issues'].append("overlapping/out-of-order chapters")
        repetitive_reason = repetitive_chapters_reason(chapter_starts)
        if repetitive_reason:
            result['chapter_issues'].append(repetitive_reason)

    if tmdb_movie is None:
        return result

    imdb_id = tmdb_movie.get('imdb_id')
    tmdb_title = tmdb_movie.get('title')
    tmdb_original_title = tmdb_movie.get('original_title')
    tmdb_release_date = tmdb_movie.get('release_date')
    tmdb_release_year = int(tmdb_release_date[:4]) if tmdb_release_date else None
    is_watched, matched_letterboxd_movie = resolve_letterboxd_watched(
        letterboxd_movies, movies_db, imdb_id, tmdb_original_title, tmdb_release_year
    )

    result.update({
        'imdb_id': imdb_id,
        'tmdb_original_title': tmdb_original_title,
        'matched_letterboxd_movie': matched_letterboxd_movie,
        'is_watched': is_watched,
        'missing_nfo': nfo_root is None,
        'title_parse_error': False,
        'title_diff': None,
        'nfo_watched': False,
        'missing_tags': [],
        'irrelevant_tags': [],
    })

    if nfo_root is None:
        return result

    nfo_title = get_movie_element(nfo_root, "title")
    if nfo_title is None:
        result['title_parse_error'] = True
        return result

    nfo_matches_tmdb = (
        are_roughly_equals(nfo_title, tmdb_title, filename_lenient=False)
        or are_roughly_equals(nfo_title, tmdb_original_title, filename_lenient=False)
    )
    nfo_matches_filename = are_roughly_equals(nfo_title, movie[0])
    if not nfo_matches_tmdb or not nfo_matches_filename:
        result['title_diff'] = {
            'nfo_title': nfo_title,
            'tmdb_title': tmdb_title,
            'file_title': movie[0],
        }

    nfo_watch_count = get_movie_element(nfo_root, "playcount")
    result['nfo_watched'] = nfo_watch_count is not None

    nfo_tags = get_movie_elements(nfo_root, "tag")
    appropriate_award_tags = [key for key, values in awards.items() if imdb_id in values]
    result['missing_tags'] = [tag for tag in appropriate_award_tags if tag not in nfo_tags]
    result['irrelevant_tags'] = [tag for tag in awards.keys() if tag in nfo_tags and imdb_id not in awards[tag]]

    return result


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help="ignore the mkv deep-analysis cache and re-probe every file (mkvmerge/mkvextract/mediainfo)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        config = load_config('config.ini')
    except (ValueError, FileNotFoundError) as e:
        print_error(str(e))
        raise SystemExit(1)

    if args.no_cache:
        print("--no-cache: ignoring cached mkv analysis, re-probing every file")

    tmdb_client = TmdbClient(config.tmdb_api_key)

    letterboxd_movies = parse_letterboxd_csv(config.letterboxd_watched_file)
    movies_db = load_movies_db(MOVIES_DB_PATH)
    awards = parse_awards()

    filepaths = []
    for dir_root in config.root_dirs:
        print(f"Scanning {dir_root}...")
        filepaths.extend(find_mkv_files(dir_root))

    print("\n=== Step 1/5: Parsing library ===")
    entries = []
    for filepath in tqdm(filepaths, desc="Parsing library"):
        filename = os.path.basename(filepath)
        movie = parse_title_and_year(filename)
        if movie is None:
            continue
        folder_name = os.path.dirname(filepath)
        movie_nfo_path = os.path.join(folder_name, 'movie.nfo')
        imdb_id = parse_movie_nfo_imdb(movie_nfo_path)
        entries.append((filepath, movie, movie_nfo_path, imdb_id))

    print("\n=== Step 2/5: Fetching TMDb data ===")
    start_error_buffering()
    tmdb_movies = [None] * len(entries)
    with ThreadPoolExecutor(max_workers=TMDB_FETCH_WORKERS) as executor:
        future_to_index = {
            executor.submit(fetch_tmdb_movie, tmdb_client, movie, imdb_id): index
            for index, (filepath, movie, movie_nfo_path, imdb_id) in enumerate(entries)
        }
        with tqdm(total=len(entries), desc="Fetching TMDb data") as progress:
            for future in as_completed(future_to_index):
                tmdb_movies[future_to_index[future]] = future.result()
                progress.set_postfix(errors=buffered_error_count())
                progress.update(1)
    flush_buffered_errors()

    print("\n=== Step 3/5: Parsing NFO files ===")
    start_error_buffering()
    nfo_roots = [None] * len(entries)
    with ThreadPoolExecutor(max_workers=NFO_PARSE_WORKERS) as executor:
        future_to_index = {
            executor.submit(parse_movie_nfo_xml, movie_nfo_path): index
            for index, (filepath, movie, movie_nfo_path, imdb_id) in enumerate(entries)
        }
        with tqdm(total=len(entries), desc="Parsing NFO files") as progress:
            for future in as_completed(future_to_index):
                nfo_roots[future_to_index[future]] = future.result()
                progress.set_postfix(errors=buffered_error_count())
                progress.update(1)
    flush_buffered_errors()

    print("\n=== Step 4/5: Resolving movie file data ===")
    start_error_buffering()
    analyses = [None] * len(entries)
    with ThreadPoolExecutor(max_workers=COMPARISON_WORKERS) as executor:
        future_to_index = {
            executor.submit(analyze_movie, entry, tmdb_movie, nfo_root, movies_db, letterboxd_movies, awards, config, args.no_cache): index
            for index, (entry, tmdb_movie, nfo_root) in enumerate(zip(entries, tmdb_movies, nfo_roots))
        }
        with tqdm(total=len(entries), desc="Resolving movie file data") as progress:
            for future in as_completed(future_to_index):
                analyses[future_to_index[future]] = future.result()
                progress.set_postfix(errors=buffered_error_count())
                progress.update(1)
    flush_buffered_errors()

    print("\n=== Step 5/5: Checking for mismatches ===")
    title_diff_count = 0
    title_diff_examples = []
    missing_nfo_count = 0
    tmdb_unmatched_count = 0
    simple_rules_runner = SimpleRuleRunner(SIMPLE_RULES)
    reencode_runner = RankedRuleRunner(REENCODE_RULE)
    movie_locations = {}
    for (filepath, movie, movie_nfo_path, _), tmdb_movie, nfo_root, analysis in zip(entries, tmdb_movies, nfo_roots, analyses):

        if nfo_root is None:
            missing_nfo_count += 1
            print(filepath)
            print("    Missing NFO")

        simple_rules_runner.run(filepath, analysis)
        reencode_runner.run(filepath, analysis)

        if tmdb_movie is None or analysis['skip']:
            tmdb_unmatched_count += 1
            continue

        imdb_id = analysis['imdb_id']
        tmdb_original_title = analysis['tmdb_original_title']
        matched_letterboxd_movie = analysis['matched_letterboxd_movie']
        is_watched = analysis['is_watched']

        folder = os.path.dirname(filepath)
        other_folders = movie_locations.setdefault(imdb_id, [])
        if other_folders and folder not in other_folders:
            print(filepath)
            print_error("    duplicate: same IMDb id as " + other_folders[0])
        other_folders.append(folder)

        cached_entry = movies_db.get(imdb_id)
        newly_confirmed_watched = matched_letterboxd_movie is not None and not (cached_entry and cached_entry['watched'])
        needs_write = cached_entry is None or newly_confirmed_watched
        if needs_write:
            if matched_letterboxd_movie is not None:
                letterboxd_id = letterboxd_id_from_url(matched_letterboxd_movie['url'])
            else:
                letterboxd_id = cached_entry['letterboxd_id'] if cached_entry else ''
            tmdb_id = tmdb_movie.get('id', '')
            upsert_movie(MOVIES_DB_PATH, imdb_id, tmdb_original_title, letterboxd_id, tmdb_id, is_watched)
            movies_db[imdb_id] = {
                'title': tmdb_original_title,
                'letterboxd_id': letterboxd_id,
                'tmdb_id': tmdb_id,
                'watched': is_watched,
            }

        if analysis['missing_nfo']:
            prompt_create_movie_nfo(movie_nfo_path, imdb_id, tmdb_movie, is_watched, tmdb_client)
            continue

        if analysis['title_parse_error']:
            print(filepath)
            print_error("    Cannot parse NFO title")
            continue

        if analysis['title_diff']:
            title_diff_count += 1
            title_diff_examples.append(filepath)
            diff = analysis['title_diff']
            print(filepath)
            print("    Title difference found")
            print("    NFO movie title: " + diff['nfo_title'])
            print("    TMDB movie title: " + diff['tmdb_title'])
            print("    File movie title: " + diff['file_title'])

        nfo_watched = analysis['nfo_watched']
        if nfo_watched and not is_watched:
            print_error("    watched status mismatch")
            comma_less_title = movie[0].replace(',', '')
            ask_and_mark_watched(MOVIES_DB_PATH, movies_db, imdb_id, comma_less_title, tmdb_movie.get('id', ''))

        if is_watched and not nfo_watched:
            add_playcount_to_nfo(movie_nfo_path)

        for missing_tag in analysis['missing_tags']:
            add_tag_to_movie_nfo(movie_nfo_path, missing_tag)

        for irrelevant_tag in analysis['irrelevant_tags']:
            print_error("    irrelevant award tag: " + irrelevant_tag)

    duplicate_groups = {
        imdb_id: sorted(set(folders)) for imdb_id, folders in movie_locations.items() if len(set(folders)) > 1
    }

    any_issues = (
        title_diff_count or missing_nfo_count or tmdb_unmatched_count
        or simple_rules_runner.any_issues() or reencode_runner.any_issues() or duplicate_groups
    )
    if any_issues:
        print("\n=== Summary ===")
        if title_diff_count:
            print("Title differences found: " + str(title_diff_count))
            for example_filepath in title_diff_examples[:5]:
                print("    " + example_filepath)
        if missing_nfo_count:
            print("Missing NFO files: " + str(missing_nfo_count))
        if tmdb_unmatched_count:
            print("TMDb matches not found: " + str(tmdb_unmatched_count))
        reencode_runner.print_summary()
        simple_rules_runner.print_summary()
        if duplicate_groups:
            print("Duplicate movies (same IMDb id, different folders): " + str(len(duplicate_groups)))
            for imdb_id, folders in list(duplicate_groups.items())[:5]:
                print(f"    {imdb_id}:")
                for folder in folders:
                    print(f"        {folder}")
