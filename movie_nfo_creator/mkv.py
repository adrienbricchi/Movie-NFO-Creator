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

import json
import os
import re
import subprocess
import tempfile

from .util import print_error

MKVMERGE_BINARY = 'mkvmerge'
MKVEXTRACT_BINARY = 'mkvextract'
MEDIAINFO_BINARY = 'mediainfo'

X264_BITRATE_CAP_MBPS = 12
X265_BITRATE_CAP_MBPS = 8

UHD_MIN_WIDTH = 3840
X265_UHD_BITRATE_CAP_MBPS = 24

# Width buckets, centered on standard resolutions (720/1280, 1080/1920,
# 1440/2560, 2160/3840) with cutoffs at their midpoints.
SD_MAX_WIDTH = 1000
WIDTH_720P_MAX = 1600
WIDTH_1080P_MAX = 2240
WIDTH_1440P_MAX = 3200

SAVINGS_TARGET_1080P_MBPS = 6
SAVINGS_TARGET_4K_MBPS = 20

MIN_CHAPTERS_FOR_PATTERN_CHECK = 4
REPETITIVE_GAP_TOLERANCE_RATIO = 0.05

CHAPTER_LINE_RE = re.compile(r'^CHAPTER\d+=(\d+):(\d+):(\d+(?:\.\d+)?)$')

ISO_639_2_TO_1 = {
    'fre': 'fr', 'fra': 'fr',
    'eng': 'en',
    'ger': 'de', 'deu': 'de',
    'spa': 'es',
    'ita': 'it',
    'por': 'pt',
    'rus': 'ru',
    'jpn': 'ja',
    'kor': 'ko',
    'chi': 'zh', 'zho': 'zh',
    'dut': 'nl', 'nld': 'nl',
    'swe': 'sv',
    'dan': 'da',
    'nor': 'no',
    'fin': 'fi',
    'pol': 'pl',
    'tur': 'tr',
    'ara': 'ar',
    'hin': 'hi',
    'gre': 'el', 'ell': 'el',
    'cze': 'cs', 'ces': 'cs',
    'hun': 'hu',
    'heb': 'he',
    'tha': 'th',
    'vie': 'vi',
}


def normalize_track_language(properties):
    ietf = properties.get('language_ietf')
    if ietf and ietf not in ('und', 'zxx'):
        return ietf.split('-')[0].lower()

    language = properties.get('language')
    if not language or language in ('und', 'zxx'):
        return None
    return ISO_639_2_TO_1.get(language.lower(), language.lower())


def is_no_linguistic_content(properties):
    return properties.get('language_ietf') == 'zxx' or properties.get('language') == 'zxx'


def parse_tag_bps(properties):
    try:
        return int(properties.get('tag_bps'))
    except (TypeError, ValueError):
        return None


def video_codec_family(track):
    codec = (track.get('codec') or '').lower()
    codec_id = (track.get('properties', {}).get('codec_id') or '').lower()
    if 'avc' in codec or 'h.264' in codec or 'avc' in codec_id:
        return 'x264'
    if 'hevc' in codec or 'h.265' in codec or 'hevc' in codec_id:
        return 'x265'
    return None


def resolve_binary(binary_name, mkvtoolnix_dir):
    if not mkvtoolnix_dir:
        return binary_name
    return os.path.join(mkvtoolnix_dir, binary_name + '.exe')


def probe_mkv(filepath, mkvtoolnix_dir=''):
    binary = resolve_binary(MKVMERGE_BINARY, mkvtoolnix_dir)
    try:
        process = subprocess.run(
            [binary, '-J', filepath],
            capture_output=True,
            encoding='utf-8',
        )
    except FileNotFoundError:
        print_error(f"mkvmerge not found at '{binary}'. Check [tracks] mkvtoolnix_dir in config.ini, or install MKVToolNix and add it to your PATH.")
        return None

    if process.returncode not in (0, 1):
        print_error(f"mkvmerge failed on {filepath}: {process.stderr.strip()}")
        return None

    try:
        data = json.loads(process.stdout)
    except json.JSONDecodeError as e:
        print_error(f"Cannot parse mkvmerge output for {filepath}: {e}")
        return None

    audio_languages = set()
    audio_track_count = 0
    audio_no_linguistic_content_count = 0
    audio_bps_total = 0
    audio_bps_known_count = 0
    video_codec = None
    video_width = None
    video_bps = None
    for track in data.get('tracks', []):
        if track.get('type') == 'audio':
            audio_track_count += 1
            properties = track.get('properties', {})
            if is_no_linguistic_content(properties):
                audio_no_linguistic_content_count += 1
            language = normalize_track_language(properties)
            if language:
                audio_languages.add(language)
            track_bps = parse_tag_bps(properties)
            if track_bps is not None:
                audio_bps_total += track_bps
                audio_bps_known_count += 1
        elif track.get('type') == 'video' and video_codec is None:
            properties = track.get('properties', {})
            video_codec = video_codec_family(track)
            pixel_dimensions = properties.get('pixel_dimensions', '')
            match = re.match(r'^(\d+)x(\d+)$', pixel_dimensions)
            if match:
                video_width = int(match.group(1))
            video_bps = parse_tag_bps(properties)

    duration_ns = data.get('container', {}).get('properties', {}).get('duration')
    duration_seconds = duration_ns / 1_000_000_000 if duration_ns else None

    try:
        size_bytes = os.path.getsize(filepath)
    except OSError as e:
        print_error(f"Cannot stat {filepath}: {e}")
        size_bytes = None

    is_mute = audio_track_count == 1 and audio_no_linguistic_content_count == 1
    audio_bps_complete = audio_track_count > 0 and audio_bps_known_count == audio_track_count

    return {
        'audio_languages': audio_languages,
        'is_mute': is_mute,
        'video_codec': video_codec,
        'video_width': video_width,
        'video_bps': video_bps,
        'audio_bps_total': audio_bps_total if audio_bps_complete else None,
        'duration_seconds': duration_seconds,
        'size_bytes': size_bytes,
    }


def classify_hdr(video_track):
    hdr_format = (video_track.get('HDR_Format') or '').lower()
    compatibility = (video_track.get('HDR_Format_Compatibility') or '').lower()
    transfer = (video_track.get('transfer_characteristics') or '').lower()

    labels = []
    if 'dolby vision' in hdr_format:
        labels.append('Dolby Vision')
    if 'hdr10+' in compatibility:
        labels.append('HDR10+')
    elif 'hdr10' in compatibility:
        labels.append('HDR10')
    if transfer == 'hlg':
        labels.append('HLG')
    if not labels and transfer == 'pq':
        labels.append('PQ10')
    return labels


def probe_mediainfo(filepath, mediainfo_dir=''):
    binary = resolve_binary(MEDIAINFO_BINARY, mediainfo_dir)
    try:
        process = subprocess.run(
            [binary, '--Output=JSON', filepath],
            capture_output=True,
            encoding='utf-8',
        )
    except FileNotFoundError:
        if mediainfo_dir:
            print_error(f"mediainfo not found at '{binary}'. Check [tracks] mediainfo_dir in config.ini.")
        return None

    if process.returncode != 0:
        print_error(f"mediainfo failed on {filepath}: {process.stderr.strip()}")
        return None

    try:
        data = json.loads(process.stdout)
    except json.JSONDecodeError as e:
        print_error(f"Cannot parse mediainfo output for {filepath}: {e}")
        return None

    video_track = next(
        (track for track in data.get('media', {}).get('track', []) if track.get('@type') == 'Video'),
        None,
    )
    if video_track is None:
        return None

    try:
        mediainfo_video_bps = int(float(video_track.get('BitRate')))
    except (TypeError, ValueError):
        mediainfo_video_bps = None

    return {
        'mediainfo_video_bps': mediainfo_video_bps,
        'hdr_formats': classify_hdr(video_track),
    }


def missing_hdr_tag_reason(mkv_info, has_hdr_tag_in_filename):
    hdr_formats = mkv_info.get('hdr_formats')
    if not hdr_formats or has_hdr_tag_in_filename:
        return None
    return ", ".join(hdr_formats)


def unwarranted_hdr_tag_reason(mkv_info, has_hdr_tag_in_filename):
    if not has_hdr_tag_in_filename or mkv_info.get('hdr_formats'):
        return None
    return "filename tagged HDR/DoVi but video track isn't HDR"


def resolution_class_from_width(video_width):
    if video_width is None:
        return None
    if video_width < SD_MAX_WIDTH:
        return 'SD'
    if video_width < WIDTH_720P_MAX:
        return '720p'
    if video_width < WIDTH_1080P_MAX:
        return '1080p'
    if video_width < WIDTH_1440P_MAX:
        return '1440p'
    return '2160p'


def resolution_tag_mismatch_reason(mkv_info, declared_resolution):
    if declared_resolution is None:
        return None

    actual_resolution = resolution_class_from_width(mkv_info['video_width'])
    if actual_resolution is None or actual_resolution == declared_resolution:
        return None
    return f"filename says {declared_resolution}, video track is {actual_resolution}"


def missing_audio_languages(mkv_info, original_language, require_french=True):
    if mkv_info['is_mute']:
        return []

    expected_languages = ['fr'] if require_french else []
    if original_language and original_language not in expected_languages:
        expected_languages.append(original_language)
    return [language for language in expected_languages if language not in mkv_info['audio_languages']]


def estimate_video_bitrate_mbps(mkv_info):
    mediainfo_video_bps = mkv_info.get('mediainfo_video_bps')
    if mediainfo_video_bps:
        return mediainfo_video_bps / 1_000_000

    video_bps = mkv_info.get('video_bps')
    if video_bps:
        return video_bps / 1_000_000

    duration_seconds = mkv_info['duration_seconds']
    size_bytes = mkv_info['size_bytes']
    if not duration_seconds or not size_bytes:
        return None

    audio_bps_total = mkv_info.get('audio_bps_total')
    if audio_bps_total is not None:
        audio_bytes = audio_bps_total * duration_seconds / 8
        video_bytes = size_bytes - audio_bytes
        if video_bytes > 0:
            return (video_bytes * 8) / (duration_seconds * 1_000_000)

    return (size_bytes * 8) / (duration_seconds * 1_000_000)


def reencode_reason(mkv_info):
    codec = mkv_info['video_codec']
    if codec is None:
        return None

    video_width = mkv_info['video_width']
    is_uhd = video_width is not None and video_width >= UHD_MIN_WIDTH
    if mkv_info.get('hdr_formats') and not is_uhd:
        return None

    bitrate_mbps = estimate_video_bitrate_mbps(mkv_info)
    if bitrate_mbps is None:
        return None

    cap_mbps = X264_BITRATE_CAP_MBPS if codec == 'x264' else X265_BITRATE_CAP_MBPS
    if bitrate_mbps <= cap_mbps:
        return None
    return f"{codec} at {bitrate_mbps:.1f} Mbps (cap: {cap_mbps} Mbps)"


def uhd_reencode_reason(mkv_info):
    codec = mkv_info['video_codec']
    video_width = mkv_info['video_width']
    is_uhd = video_width is not None and video_width >= UHD_MIN_WIDTH
    if codec != 'x265' or not is_uhd:
        return None

    bitrate_mbps = estimate_video_bitrate_mbps(mkv_info)
    if bitrate_mbps is None or bitrate_mbps <= X265_UHD_BITRATE_CAP_MBPS:
        return None
    return f"UHD x265 at {bitrate_mbps:.1f} Mbps (cap: {X265_UHD_BITRATE_CAP_MBPS:.1f} Mbps)"


def reencode_savings_bytes(mkv_info):
    video_width = mkv_info['video_width']
    duration_seconds = mkv_info['duration_seconds']
    if not duration_seconds:
        return None

    bitrate_mbps = estimate_video_bitrate_mbps(mkv_info)
    if bitrate_mbps is None:
        return None

    is_uhd = video_width is not None and video_width >= UHD_MIN_WIDTH
    target_mbps = SAVINGS_TARGET_4K_MBPS if is_uhd else SAVINGS_TARGET_1080P_MBPS

    savings_bytes = (bitrate_mbps - target_mbps) * 1_000_000 * duration_seconds / 8
    return savings_bytes if savings_bytes > 0 else None


def format_size_fr(size_bytes):
    size_go = size_bytes / (1024 ** 3)
    if size_go >= 1:
        return f"{size_go:.2f} Go"
    size_mo = size_bytes / (1024 ** 2)
    return f"{size_mo:.0f} Mo"


def extract_chapter_start_times(filepath, mkvtoolnix_dir=''):
    binary = resolve_binary(MKVEXTRACT_BINARY, mkvtoolnix_dir)
    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.txt')
    os.close(tmp_fd)
    try:
        try:
            process = subprocess.run(
                [binary, filepath, 'chapters', '-s', tmp_path],
                capture_output=True,
                encoding='utf-8',
            )
        except FileNotFoundError:
            print_error(f"mkvextract not found at '{binary}'. Check [tracks] mkvtoolnix_dir in config.ini, or install MKVToolNix and add it to your PATH.")
            return None

        if process.returncode not in (0, 1):
            print_error(f"mkvextract failed on {filepath}: {process.stderr.strip()}")
            return None

        try:
            with open(tmp_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            lines = []
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    chapter_starts = []
    for line in lines:
        match = CHAPTER_LINE_RE.match(line.strip())
        if match:
            hours, minutes, seconds = match.groups()
            chapter_starts.append(int(hours) * 3600 + int(minutes) * 60 + float(seconds))
    return sorted(chapter_starts)


def has_no_chapters(chapter_starts):
    return len(chapter_starts) == 0


def has_overlapping_chapters(chapter_starts):
    return any(next_start <= start for start, next_start in zip(chapter_starts, chapter_starts[1:]))


def repetitive_chapters_reason(chapter_starts):
    if len(chapter_starts) < MIN_CHAPTERS_FOR_PATTERN_CHECK:
        return None

    gaps = [next_start - start for start, next_start in zip(chapter_starts, chapter_starts[1:])]
    average_gap = sum(gaps) / len(gaps)
    if average_gap <= 0:
        return None

    tolerance = REPETITIVE_GAP_TOLERANCE_RATIO * average_gap
    gaps_are_uniform = all(abs(gap - average_gap) <= tolerance for gap in gaps)
    if not gaps_are_uniform:
        return None

    return f"chapters look auto-generated, every ~{average_gap / 60:.1f} min"
