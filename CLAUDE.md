# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Python tool (`movie_nfo_creator` package) that scans a local movie library for
`.mkv` files, matches each one against TMDb, and creates/updates a Kodi-style
`movie.nfo` file next to it. It also cross-references a Letterboxd watch-history
export to mark movies as watched, and tags movies that won/were nominated for
major awards (Oscars, César, Palme d'Or) using local CSV lookup tables in
`movie_nfo_creator/tag_lists/awards/`.

This is a personal, interactive CLI utility. A small `unittest` suite lives in `tests/`: `python -m unittest discover -s tests`.

## Running

```
python script.py
```

`script.py` at the repo root is a thin backwards-compatible shim that calls
`movie_nfo_creator.cli:main`. Once installed (`pip install -e .`), the
`movie-nfo-creator` console script (declared in `pyproject.toml`) is equivalent.

Dependencies are declared in `pyproject.toml` (`requests`). Install with
`pip install -e .` or `pip install requests` directly.

Before running, copy `config.ini.dist` to `config.ini` and fill in:
- `[paths] root_dir` — one or more library root folders (`;`-separated) to scan
- `[tmdb] api_key` — a TMDb API key
- `[letterboxd] watched_file` — path to a Letterboxd "watched" CSV export
- `[tracks] mkvtoolnix_dir` — optional, empty by default (looks up
  `mkvmerge`/`mkvextract` on `PATH`). Set to MKVToolNix's install folder (e.g.
  `C:\Program Files\MKVToolNix` on Windows) if it's not on `PATH` — the
  Windows installer doesn't add it there itself.
- `[tracks] mediainfo_dir` — optional, empty by default (looks up
  `mediainfo` on `PATH`). Set to MediaInfo CLI's install folder if it's not
  on `PATH`. Unlike `mkvtoolnix_dir`, MediaInfo is a soft dependency: if the
  binary can't be found and this setting is left empty, `probe_mediainfo`
  silently skips (no error) — HDR detection and the accurate video bitrate
  it provides are just unavailable, everything else still runs. Only set
  and misconfigured is treated as an error worth printing, since then the
  absence is unintentional.
- `[tags] remove` — optional, empty by default. Tags (`;`-separated) pruned from every NFO, on an exact case-sensitive match.

`config.ini` and `watched.csv` are gitignored (personal/secret data);
`config.ini.dist` is the template committed to the repo.

`--no-cache` (parsed by `cli.py:parse_args`, standard `argparse`, `store_true`)
ignores the mkv deep-analysis cache (`mkv_cache.py`) for the whole run —
every file is re-probed via `mkvmerge`/`mkvextract`/`mediainfo` regardless of
a cached entry's age, and the refreshed result overwrites that entry as it
goes (same `ON CONFLICT DO UPDATE` used normally), so the cache ends up fully
current for the next run without a separate reset/delete step. Named after
`docker build --no-cache`'s convention (skip reads, still write) rather than
a literal "wipe the table" reset.

The script is interactive: it prompts on stdin (`[Y/n]`) before creating a new
NFO file or before adding a movie to `watched_override.csv`.

## Architecture

`movie_nfo_creator/cli.py:main()` is the entry point and orchestrates a linear
pipeline — read it first to understand control flow, then dip into the module
it calls into for each concern:

- `config.py` — loads and validates `config.ini` into a `Config` dataclass.
- `scanner.py` — `find_mkv_files`, `parse_title_and_year`, `are_roughly_equals`.
- `tmdb.py` — `TmdbClient`, a thin wrapper around the TMDb API (search, lookup
  by id, lookup by IMDb id, credits). Holds the API key instance-side instead
  of as a module global.
- `nfo.py` — all `movie.nfo` read/write logic.
- `letterboxd.py` — parses the Letterboxd watched-history export.
- `tag_lists.py` — the automatic tag lists (bundled package data under `movie_nfo_creator/tag_lists/`, resolved via `Path(__file__).parent`, not cwd-relative).
- `mkv.py` — inspection of each `.mkv`'s inner tracks via the MKVToolNix CLI
  (`mkvmerge`/`mkvextract`, must be in `PATH` or `[tracks] mkvtoolnix_dir`).
- `mkv_cache.py` — 1-day cache (same TTL as `tmdb.py`'s HTTP cache) for
  `mkv.py`'s analysis, keyed on the file's path + size + mtime rather than a
  content hash (hashing multi-GB files would defeat the point of caching).

**Discovery**: `find_mkv_files` globs each configured root for
`ROOTDIR/YYYY-YYYY/**/*.mkv` (library folders are named by year ranges).
For each match, `parse_title_and_year` extracts the title/year from the
filename (expected pattern: `Title (..., YYYY, ...).mkv`), and the sibling
`movie.nfo` in the same folder is located.

**NFO format**: An NFO file is *not* well-formed XML on its own — it's an XML
`<movie>` block followed by a trailing plain-text IMDb URL line
(`https://www.imdb.com/title/ttXXXXXXX`). Every reader/writer in `nfo.py`
(`parse_movie_nfo_xml`, `parse_movie_nfo_imdb`, `add_tag_to_movie_nfo`,
`add_playcount_to_nfo`) has to split off that last line before parsing the XML
and re-append it after serializing. Keep this in mind when touching any NFO
read/write code — a naive `ET.parse()` on the raw file will fail.

**TMDb lookup**: If an existing NFO already has an IMDb id, that id is used via
`TmdbClient.get_movie_by_imdb_id` to fetch canonical TMDb data instead of
searching by title, since it's a more reliable match. Otherwise
`TmdbClient.find_movie` searches TMDb by title+year (`search_movie`) and
requires a strict, case-insensitive match on title/original_title/year. All
TMDb calls retry once, after a 10s sleep, on HTTP 429.

**Watched status**: Combines two sources — the Letterboxd CSV
(`parse_letterboxd_csv`, matched by title+year via `are_roughly_equals`, which
normalizes `:` vs `-` and strips trailing parenthetical suffixes) and a local
manual override file, `watched_override.csv` (id-based, for movies watched
outside Letterboxd). If the NFO's `<playcount>` disagrees with the computed
watched status, the script either patches the NFO in (`add_playcount_to_nfo`)
or, on a mismatch the other direction, interactively offers to record the
movie in `watched_override.csv`.

**Automatic tagging**: `parse_tag_lists` (`tag_lists.py`) loads every `movie_nfo_creator/tag_lists/**/*.csv` into a single dict of tag → id list.
A list CSV starts with its tag name on the first line, then the `original_title,imdb_id` header and one film per line.
The code knows nothing about what a list is, and adding one is dropping a CSV there, in any subfolder.
For each movie, missing tags are appended to the NFO (`add_tag_to_movie_nfo`) and tags present in the NFO that no longer match
the movie's IMDb id are flagged as errors (not auto-removed).
Any other NFO tag that matches no automatic tag is reported as an unknown tag (`find_tag_mismatches` in `tags.py`).
Tags listed in `[tags] remove` are pruned from the NFO (`remove_tag_from_movie_nfo`), and an automatic tag listed there is never added.

The subfolders only sort the lists:
- `awards/` — one list per award, keyed to a French-language award-name tag.
- `studios/` — a studio's films (Pixar, Ghibli, Walt Disney Animation Studios).
- `universes/` — cinematic universes (MCU, Star Wars, Godzilla eras…) and theme lists (Disney attraction adaptations).
- `characters/` — the films a character appears in, whatever the saga (Batman, Dracula, Godzilla…), updated by hand.

The award and universe CSVs are refreshed from Wikidata by the `update-awards` project skill (`.claude/skills/update-awards/`),
whose scripts and tests live in the skill folder, outside the package.

All user-facing text (NFO `<title>` content, printed diffs, award tag names) is
in French, matching `language=fr-FR` used in the TMDb API calls — preserve this
if extending the script.

**Track inspection (`mkv.py`)**: always runs (no config toggle — it used to be
gated behind `[tracks] deep_check`, removed once `mkv_cache.py` made re-runs
within a day nearly free). `probe_mkv` shells out to `mkvmerge -J <file>` to read
track/container metadata as JSON, and separately stats the file for its size;
`extract_chapter_start_times` shells out to `mkvextract <file> chapters -s
<tmp-file>` (simple chapter format written to a throwaway temp file, since
unlike `mkvmerge -J`, `mkvextract`'s `chapters` mode has no documented stdout
support and silently writes nothing when there are no chapters) to read
chapter start timestamps — **strictly read-only**: the `.mkv` file itself is
never opened, written, or modified by this tool (or by Claude Code working in
this repo) — the only file this project ever writes to is `movie.nfo`. Both
tools follow the MKVToolNix exit-code convention (0 = ok, 1 = ok with
warnings, 2 = hard failure) — only 2 is treated as a real failure; a plain
non-zero check would wrongly discard valid output on a mere warning. These
checks only need the mkv file itself, so `analyze_movie` (`cli.py`) runs them
even when the movie couldn't be matched on TMDb (which otherwise short-circuits
most of the analysis) — don't reintroduce a dependency on a successful TMDb
match for them.

**Caching (`mkv_cache.py`)**: `analyze_movie` calls `load_cached_deep_analysis`
before ever invoking `probe_mkv`/`extract_chapter_start_times`, and
`store_deep_analysis_cache` after, both against `MOVIES_DB_PATH` (the same
sqlite file used by `movies.py`, just another table — `mkv_analysis_cache`).
Cache key is `(filepath, size_bytes, mtime_ns)` from a single `os.stat()`
call, deliberately *not* a content hash — hashing a multi-GB file on every
run would cost more than just re-running `mkvmerge`/`mkvextract`, defeating
the point. 30-day TTL (`CACHE_TTL_SECONDS`) — longer than `tmdb.py`'s 1-day
`requests_cache` expiry, since the cache key already changes whenever the
file itself does; the TTL here only bounds staleness from an MKVToolNix
upgrade or a code change to what gets probed, not from the file's own
content drifting. A cache hit skips both subprocess calls entirely, so
if a file is replaced by another of the exact same size *and* mtime within
that day, the cache would serve stale data — accepted as vanishingly
unlikely for a personal library. `analyze_movie` runs inside a
`ThreadPoolExecutor` (`COMPARISON_WORKERS` threads), so cache reads/writes
happen concurrently; `_connect` uses `sqlite3.connect(..., timeout=30.0)` to
ride out lock contention rather than adding any manual locking.

`cli.py:ensure_mediainfo` guards against exactly the schema-evolution risk
called out above: a cache hit whose `mkv_info` predates the MediaInfo fields
(`hdr_formats`, `mediainfo_video_bps` — either from before this feature
existed, or from a run where `mediainfo` wasn't found/configured yet) would
otherwise silently miss HDR detection and the accurate bitrate for up to the
full 30-day TTL. `analyze_movie` calls it on every cache hit; it checks for
`'hdr_formats' not in mkv_info` (not falsiness — an empty list is a valid,
already-probed "no HDR detected" result) and, only if the key is truly
absent, re-runs `probe_mediainfo` and re-stores the merged blob so the fix
propagates on the very next run instead of waiting for the TTL or a file
change.

- `missing_audio_languages` flags movies with no French and/or no
  original-language (from TMDb's `original_language`, `None` when there's no
  TMDb match) audio track. The French requirement is skipped when the
  filename is tagged VOST (`scanner.is_vost`, a case-insensitive `vost`
  substring anywhere in the filename, e.g. `Title (2019, 1080p VOST).mkv`) —
  those are intentionally French-subtitle-only releases with no French dub.
  Skipped entirely (no check at all, VOST or not) when `probe_mkv` finds
  exactly one audio track and it's tagged `zxx` (no linguistic content,
  either via `language_ietf` or the legacy `language` property) — that's a
  silent film, not a movie missing a dub.
- `estimate_video_bitrate_mbps` is four tiers, each falling back to the next:
  1. `mediainfo_video_bps`, from `probe_mediainfo`'s MediaInfo `BitRate` field
     — a real measured/computed per-track video bitrate, more consistently
     populated than mkvmerge's `tag_bps` (tier 2) since MediaInfo computes it
     from actual stream statistics when container tags are missing. Only
     present when MediaInfo is installed (see `[tracks] mediainfo_dir`).
  2. The video track's own `tag_bps` property (a per-track bits-per-second
     statistic `mkvmerge` sometimes writes at mux time) — the real
     video-only bitrate, when present.
  3. `(size_bytes - audio_bps_total * duration_seconds / 8) * 8 / duration`
     — total size minus the audio tracks' own known bytes (their `tag_bps`,
     same property, summed across every audio track). Only used when
     **every** audio track has a usable `tag_bps` (`probe_mkv` sets
     `audio_bps_total` to `None`, not a partial sum, if even one track is
     missing it — a partial subtraction would silently underestimate audio
     and inflate the video estimate).
  4. `size_bytes * 8 / duration` (whole file, including every audio
     track/subtitle/attachment) — used when none of the above applies.
  Tier 4 alone is common enough to be load-bearing, not a rare edge case,
  and it overestimates bitrate on releases with many/heavy audio tracks
  (extended editions with several dubs and commentary tracks are the classic
  case — confirmed false-flagging a perfectly reasonable LOTR encode this
  way before `tag_bps` was used at all). Use `.get(...)`, not `[...]`, for
  `mediainfo_video_bps`/`video_bps`/`audio_bps_total` when reading a cached
  `mkv_info` — entries cached before these fields existed won't have them.
- `reencode_reason` flags movies as re-encode candidates from bitrate alone:
  x264 over 12 Mbps, x265 over 8 Mbps — no other codecs are flagged. One
  resolution/HDR exemption: below UHD width, a detected `hdr_formats` (see
  HDR detection below) skips the check entirely — 1080p HDR releases are
  assumed to already need/carry a higher bitrate to avoid banding, not to be
  re-encode candidates. UHD width is unaffected by this exemption (still
  goes through this flat cap, in addition to `uhd_reencode_reason` below),
  and it still routinely flags legitimate UHD/HDR masters as false positives
  there (accepted tradeoff — meant to be eyeballed manually).
- `uhd_reencode_reason` is a second, narrower check layered on top for UHD
  content specifically (video width ≥ 3840, x265 only): cap is
  `X265_UHD_BITRATE_CAP_MBPS` (currently 24 Mbps, hand-tuned from a real tight
  UHD/HDR x265 remux measured at 23.1 Mb/s overall). Both checks run
  independently — a file can be flagged by the flat cap without tripping the
  UHD cap (expected for legitimate 4K masters).
- `reencode_savings_bytes` estimates bytes saved if a flagged file were
  re-encoded down to a realistic target bitrate — `SAVINGS_TARGET_4K_MBPS`
  (20 Mbps) for UHD-width video, `SAVINGS_TARGET_1080P_MBPS` (6 Mbps)
  otherwise — deliberately independent of the warn caps above, since those
  are tuned to catch bloat, not to state what a good re-encode should target.
  Also goes through `estimate_video_bitrate_mbps` (real `video_bps` when
  present, whole-file `size/duration` otherwise): `savings = (bitrate_mbps -
  target_mbps) * duration_seconds * 1_000_000 / 8`, which is algebraically
  the same "shrink total size to a target total bitrate" math as before when
  falling back to the whole-file estimate, but a much smaller and more
  honest number when `video_bps` is real (confirmed on a real LOTR extended
  edition: ~17 Mbps whole-file estimate said ~20 GB saveable, ~9.55 Mbps real
  `video_bps` said ~6.5 GB — the true number, since only the video track
  actually gets re-encoded, audio tracks don't shrink). Only computed/reported
  when the
  file already tripped one of the reencode checks. `cli.py` sums this across
  the whole library into an "Estimated re-encode savings" summary line,
  formatted via `format_size_fr` (French Mo/Go, binary units).
- Chapter checks (`has_no_chapters`, `has_overlapping_chapters`,
  `repetitive_chapters_reason`) flag: zero chapters; any chapter start time
  not strictly after the previous one (out-of-order/duplicate — mkv's simple
  chapter format has no explicit end times, so this is the only definition of
  "overlap" that applies); and, for files with 4+ chapters, chapter gaps that
  are all within 5% of their average (auto-generated fake chapters at a
  fixed interval, e.g. every 5 or 10 minutes). The zero-chapters flag is
  skipped for filenames tagged WEB (`scanner.is_web`, `\bweb` — matches WEB,
  WEBRip, WEB-DL, etc.), since web releases routinely ship without chapters;
  the overlap and repetitive-interval checks still apply to them if they do
  have chapters.

**HDR detection (`mkv.py:probe_mediainfo`/`classify_hdr`)**: an earlier attempt
at HDR detection via `mkvmerge -J`'s container-level `Colour` properties
(`color_transfer_characteristics`, `max_content_light_level`, etc.) was rolled
back — those are frequently absent even on genuinely HDR files (confirmed
against a real MULTi/DoVi/2160p UHD remux, muxed by mkvmerge v100, whose video
track had none of them), since actually proving HDR requires parsing the video
bitstream's VUI/SEI, which `mkvmerge` doesn't do. This was later revisited
using MediaInfo instead (which does parse the bitstream), gated behind the new
optional `[tracks] mediainfo_dir` soft dependency: `probe_mediainfo` shells out
to `mediainfo --Output=JSON <file>`, reads the first video track's
`HDR_Format`, `HDR_Format_Compatibility`, and `transfer_characteristics`
fields, and `classify_hdr` maps them to a label list (a file can carry more
than one, e.g. a dual-layer Dolby Vision remux with an HDR10 fallback layer):
- `Dolby Vision` — `HDR_Format` contains "Dolby Vision".
- `HDR10+` — `HDR_Format_Compatibility` contains "HDR10+" (checked before
  plain HDR10 since the string "hdr10" is a substring of "hdr10+").
- `HDR10` — `HDR_Format_Compatibility` contains "HDR10" and not "HDR10+".
- `HLG` — `transfer_characteristics` is exactly "HLG" (broadcast-safe curve,
  usually ships with no HDR10-style SEI/dynamic metadata at all).
- `PQ10` — `transfer_characteristics` is "PQ" but none of the above matched
  (a PQ-mastered file with no recognized HDR10 compatibility signaling).
The result (`hdr_formats`, alongside `mediainfo_video_bps` used by
`estimate_video_bitrate_mbps`) is merged into the cached `mkv_info` dict in
`cli.py:analyze_movie`.

`mkv.py:missing_hdr_tag_reason` flags a movie whose video track has a
detected HDR format but whose filename carries no recognized HDR tag — a
mislabeled release is easy to miss when browsing the library by filename
alone. It's a pure function over `mkv_info['hdr_formats']` and a
filename-derived boolean; `cli.py` supplies that boolean via
`scanner.py:has_hdr_tag` (a `HDR_FILENAME_TAG_RE` match on `HDR10+`,
`HDR10Plus`, `HDR10`, `HDR`, `Dolby Vision`/`DoVi`, or `HLG` — same loose
leading-`\b`-only style as `is_web`). Deliberately excludes bare `DV` as a
recognized tag: it collides with the common `DVDRip`/`DVDScr` release tag
family, and modern HDR releases spell out `DoVi`/`Dolby Vision` in the
filename anyway. The reason string returned is the comma-joined
`hdr_formats` labels (e.g. `"Dolby Vision, HDR10"`), printed by `cli.py` as
"missing HDR tag in filename for: ...", counted, and summarized with up to 5
examples like the other first-N checks.

`mkv.py:unwarranted_hdr_tag_reason` is the symmetric check the other way:
filename carries an HDR tag but `hdr_formats` came back empty (mislabeled
release, or a manual rename mistake). Both checks share the same
`has_hdr_tag_in_filename` boolean, computed once in `cli.py:analyze_movie` and
passed to both rather than calling `has_hdr_tag` twice.

**Resolution tag mismatch (`scanner.py:declared_resolution_class` +
`mkv.py:resolution_class_from_width`/`resolution_tag_mismatch_reason`)**:
flags a filename resolution tag (`SD`/`480p`/`576p`, `720p`, `1080p`,
`1440p`, `2160p`/`4K`) that doesn't match the video track's actual width.
`resolution_class_from_width` buckets `video_width` at the midpoints between
standard widths (720/1280, 1080/1920, 1440/2560, 2160/3840) rather than
requiring an exact match, since real files commonly deviate slightly (scope
crops, open-matte masters). Only fires when the filename actually declares a
resolution — a file with no resolution tag at all is never flagged.

**File/folder name mismatch**: `cli.py:analyze_movie` flags a movie file
whose name (minus extension) doesn't exactly match its parent folder's name —
a plain string comparison (not `are_roughly_equals`, which is for
title-vs-TMDb/filename equivalence, not this literal one-folder-per-movie
convention). Computed unconditionally from the two path components alone, so
it doesn't depend on `mkv_info`/TMDb/NFO resolution at all — it still fires
for a file that fails every other lookup.

**`rules.py`**: most per-file checks (missing audio languages, chapter issues,
both HDR-tag checks, resolution tag mismatch, folder/file name mismatch) share
one shape — a per-file check producing 0+ message lines, counted, with up to 5
example filepaths (first found, not ranked) in the summary — and are declared
as data (`SimpleRule(key, label, check)`, `check: analysis -> list[str] or
falsy`) in `cli.py`'s `SIMPLE_RULES` list, run each iteration via
`SimpleRuleRunner.run(filepath, analysis)`, and summarized in one call to
`SimpleRuleRunner.print_summary()`. Re-encode candidates are the one check
with a genuinely different shape — a sortable value (savings bytes) for a
top-5-by-value ranked list plus a running total, not just first-N examples —
so they get their own `RankedRule`/`RankedRuleRunner` (`cli.py`'s
`REENCODE_RULE`), sharing only the common `key`/`label`/`check` fields with
`SimpleRule` via the `Rule` base class. `title_diff` (three distinct fields,
not a message list, and printed in plain text rather than
`print_error`/red — informational, not a warning), `missing_nfo`/
`tmdb_unmatched` (no natural per-file message at all — `tmdb_unmatched`
prints nothing per-file, `missing_nfo` prints plain-text "Missing NFO"), and
duplicate detection (genuinely cross-file, only resolvable after the full
Step 5 loop via `movie_locations` — see below) don't fit either rule shape
and stay as bespoke code in `cli.py`'s Step 5 block. When adding a new
per-file check: if it's a simple pass/fail with printable message(s), add a
`SimpleRule` to `SIMPLE_RULES` rather than hand-writing the counter/examples/
print/summary boilerplate; only reach for something bespoke if it doesn't
fit that shape (extra structured payload, non-error styling, or cross-file
state).

**Duplicate detection**: `movie_locations` (built during the Step 5 loop,
keyed by each matched movie's IMDb id → list of folder paths, one entry per
file processed) is the only cross-file check — everything else in that loop
is purely per-file. A duplicate is the same IMDb id appearing under more than
one distinct folder (not just more than one file — the library is one folder
per movie, so this is the right granularity, not `filepath`). The inline
warning fires the moment a second distinct folder is seen for an id it's
already tracking; the final `duplicate_groups` dict is only computable after
the full loop (a later file could turn an as-yet-unique id into a duplicate),
so the "same IMDb id, different folders" summary line — with up to 5
example groups, each listing every folder — is built as a final pass right
before the `=== Summary ===` block, not accumulated incrementally like the
other counts.
