---
name: update-awards
description: Refresh the award lookup CSVs in movie_nfo_creator/tag_lists/awards/ (Oscars, César, Palme d'Or…) and the cinematic universe CSVs in movie_nfo_creator/tag_lists/universes/ (MCU, DCU, Star Wars…) from Wikidata, review each new film, and write the vetted additions. Use when asked to update, refresh or check the award or universe lists, after a new ceremony or a new universe film.
---

# Update the award lists

The award CSVs in `movie_nfo_creator/tag_lists/awards/` are refreshed from Wikidata by this skill's `scripts/refresh_awards.py`, kept out of the package on purpose.
The script only appends films missing locally, and never removes a row: Wikidata lacks some older winners and lags on recent ceremonies, so local rows stay authoritative.
Which CSV maps to which Wikidata award item is `AWARD_SOURCES` at the top of the script; a new CSV in `awards/` needs an entry there too (the script warns about unmapped ones).
`scripts/fetched_years.json` holds the last ceremony year already covered per CSV: only later ceremonies are suggested, so old years are never refreshed.
A film's ceremony year comes from Wikidata, or is estimated as its release year + 1; films with no date at all are skipped and counted.

## Steps

1. From the repo root, run the dry run and read its output:
   ```bash
   python3 .claude/skills/update-awards/scripts/refresh_awards.py
   ```
   Each `+` line is a film from a ceremony after the fetched year that the CSV lacks, with its ceremony year and IMDb link.
   Wikidata's query service is sometimes slow: a run takes up to a minute, and a `ReadTimeout` just needs a re-run.
2. Vet every `+` line before writing anything: confirm the film really won (or, for the nominee list, was nominated for) that award and that the IMDb id points at the right film,
   e.g. against the award's Wikipedia list of winners. Wikidata mix-ups happen, like Other People's Money (1991) carrying the César of L'Argent des autres (1978).
3. For each false positive, add its IMDb id to that source's `wikidata_false_positives` in the script's `AWARD_SOURCES`, with a one-line comment naming the film and the mix-up, then re-run the dry run.
4. Check each new ceremony is complete (every winner, and every nominee for a nominee list): `--write` moves `fetched_years.json` up to the newest ceremony it adds,
   and that year is never suggested again. Add what Wikidata lacks by hand first.
   Show the user the vetted additions as IMDb links and get a go-ahead before writing.
5. Apply them:
   ```bash
   python3 .claude/skills/update-awards/scripts/refresh_awards.py --write
   ```
   New rows are appended at the end of each CSV, sorted by ceremony year, titled with the Wikidata original title (or French/English label).
   Fix a title by hand if it doesn't match the CSV's existing style; the title column is informational, only the IMDb id is used for tagging.
6. Check `git diff movie_nfo_creator/tag_lists/awards/`. After changing the script itself, run its tests: `python3 -m unittest discover -s .claude/skills/update-awards/scripts`.

## Adding a new award

Wikidata's award statements are too sparse to build a full history (it had 39 of the 224 César Best Film nominees).
Seed the CSV from the award's Wikipedia list instead: take each film's article link, resolve it to its Wikidata item (`wbgetentities` with `sites=<lang>wiki&titles=…`),
read the item's IMDb id (`P345`), and cross-check against Wikidata's own award statements. Watch for ties and links to a non-film article (a play, a novel).
Then add the tag and its CSV path to `movie_nfo_creator/tag_lists/tags.csv`, the source to `AWARD_SOURCES`, and its last seeded ceremony year to `fetched_years.json`.

## After a new ceremony

Wikidata can take weeks to record a ceremony (Oscars in March, César in February, Cannes in May).
If a winner you know of doesn't show up as a `+` line, add the row to the CSV by hand: `Title,ttXXXXXXX`, appended at the end, no trailing newline.
`--show-missing` lists the local rows Wikidata doesn't know about, as `?` lines; they're expected for old honorary Oscars, pre-1955 Cannes Grand Prix and recent ceremonies.

## Cinematic universes

The universe CSVs in `movie_nfo_creator/tag_lists/universes/` follow the same rules, with `scripts/refresh_universes.py`:
```bash
python3 .claude/skills/update-awards/scripts/refresh_universes.py
```
- `UNIVERSE_SOURCES` maps each CSV to the Wikidata items films link to (series, fictional universe or franchise, directly or through one sub-series).
  `closed=True` universes are never refreshed, and those without an item (Godzilla Reiwa, Universal Monsters modern era, Hellraiser, Ghostbusters, Millenium, the Disney attraction adaptations) are updated by hand,
  as are the studio lists (Pixar, Ghibli), which films link to as a production company.
- `scripts/universe_fetched_dates.json` holds a release-date cut-off per CSV: only films released after it, and already out, are suggested.
  `--write` moves it to the newest release added.
- Announced films that already have an IMDb id are listed ahead of release, so the tag is there as soon as the file is.
  Drop or rename one if it is cancelled or retitled; the refresh never suggests films already in a list.
- The lists hold theatrical and streaming feature films, plus a few specials asked for by name (the MCU shorts, the Star Wars Holiday Special). Wikidata also links shorts, TV specials, fan films and Lego specials (Star Wars),
  and franchise items lump unrelated reboots together (every Mummy film sits in Q3823300): vet each `+` line the same way, and add false positives to `wikidata_false_positives`.
- Seeding a new universe works like a new award: list its films from Wikipedia, resolve their IMDb ids through Wikidata, add the tag and
  its CSV path to `movie_nfo_creator/tag_lists/tags.csv`, the source to `UNIVERSE_SOURCES` and, if it is refreshed, today's date to `universe_fetched_dates.json`.
- When IMDb splits a film into its original and a recut (Japanese Godzilla films and their US versions), list both ids, since TMDB may match either.

Don't commit unless the user asks.
