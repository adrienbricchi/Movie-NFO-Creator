---
name: update-awards
description: Refresh the award lookup CSVs in movie_nfo_creator/awards/ (Oscars, César, Palme d'Or) from Wikidata, review each new film, and write the vetted additions. Use when asked to update, refresh or check the award lists, or after a new ceremony.
---

# Update the award lists

The award CSVs in `movie_nfo_creator/awards/` are refreshed from Wikidata by `movie_nfo_creator/refresh_awards.py`.
The script only appends films missing locally, and never removes a row: Wikidata lacks some older winners and lags on recent ceremonies, so local rows stay authoritative.
Which CSV maps to which Wikidata award item is `AWARD_SOURCES` in `movie_nfo_creator/awards.py`.

## Steps

1. From the repo root, run the dry run and read its output:
   ```bash
   python3 -m movie_nfo_creator.refresh_awards
   ```
   Each `+` line is a film Wikidata lists for that award but the CSV lacks, with its IMDb link.
2. Vet every `+` line before writing anything: confirm the film really won (or, for the nominee list, was nominated for) that award and that the IMDb id points at the right film,
   e.g. against the award's Wikipedia list of winners. Wikidata mix-ups happen, like Other People's Money (1991) carrying the César of L'Argent des autres (1978).
3. For each false positive, add its IMDb id to that source's `wikidata_false_positives` in `awards.py`, with a one-line comment naming the film and the mix-up, then re-run the dry run.
4. Show the user the vetted additions as IMDb links and get a go-ahead before writing.
5. Apply them:
   ```bash
   python3 -m movie_nfo_creator.refresh_awards --write
   ```
   New rows are appended at the end of each CSV, sorted by ceremony year, titled with the Wikidata original title (or French/English label).
   Fix a title by hand if it doesn't match the CSV's existing style; the title column is informational, only the IMDb id is used for tagging.
6. Check `git diff movie_nfo_creator/awards/` and run the tests: `python3 -m unittest discover -s tests`.

## After a new ceremony

Wikidata can take weeks to record a ceremony (Oscars in March, César in February, Cannes in May).
If a winner you know of doesn't show up as a `+` line, add the row to the CSV by hand: `Title,ttXXXXXXX`, appended at the end, no trailing newline.
`--show-missing` lists the local rows Wikidata doesn't know about, as `?` lines; they're expected for old honorary Oscars, pre-1955 Cannes Grand Prix and recent ceremonies.

Don't commit unless the user asks.
