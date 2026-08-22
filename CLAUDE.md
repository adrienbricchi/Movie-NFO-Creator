# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Python tool (`movie_nfo_creator` package) that scans a local movie library for
`.mkv` files, matches each one against TMDb, and creates/updates a Kodi-style
`movie.nfo` file next to it. It also cross-references a Letterboxd watch-history
export to mark movies as watched, and tags movies that won/were nominated for
major awards (Oscars, César, Palme d'Or) using local CSV lookup tables in
`movie_nfo_creator/awards/`.

There is no test suite — this is a personal, interactive CLI utility.

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

`config.ini` and `watched.csv` are gitignored (personal/secret data);
`config.ini.dist` is the template committed to the repo.

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
- `awards.py` / `csv_utils.py` — award CSV lookup tables (bundled package data
  under `movie_nfo_creator/awards/`, resolved via `Path(__file__).parent`, not
  cwd-relative) and generic title/imdb_id CSV parsing shared with
  `watched_override.csv`.

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

**Awards tagging**: `parse_awards` loads each CSV in `movie_nfo_creator/awards/`
(one IMDb id per line, keyed to a French-language award-name tag) into a dict of
award-name → id list. For each movie, missing award tags are appended to the
NFO (`add_tag_to_movie_nfo`) and tags present in the NFO that no longer match
the movie's IMDb id are flagged as errors (not auto-removed).

All user-facing text (NFO `<title>` content, printed diffs, award tag names) is
in French, matching `language=fr-FR` used in the TMDb API calls — preserve this
if extending the script.
