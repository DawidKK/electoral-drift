# Ingestion

The ingestion package loads public source data into the database before the API reads it.
This keeps heavy data preparation out of HTTP requests.

## Raw PKW Sejm to Interim

Transform one supported PKW export:

```bash
uv run electoral-transform-sejm-interim \
  data/raw/elections/sejm/2019-sejm.csv \
  data/interim/elections/sejm
```

The command supports the repository's 2015, 2019, and 2023 Sejm exports. It creates:

- `<source>-gmina-totals.csv` — one row per municipality and election;
- `<source>-committee-results.csv` — one row per municipality, election, and committee.

The transformation:

- handles the year-specific separator, header names, and election date;
- removes Polish thousands separators from integer values;
- converts `-` and empty committee cells to missing values;
- preserves explicit zero-vote results;
- normalizes source municipality codes to six characters with leading zeroes;
- retains source committee names without assigning analytical political blocs;
- skips foreign rows without a municipality TERYT code and reports their count.

Interim output remains source-oriented. Committee normalization and political-bloc assignment
belong to the interim-to-processed transformation. Enrichment with the full TERYT representation
and resolution of historical territorial changes require a versioned reference dataset and
remain a later step.

## Sejm Interim to Processed

Build importer-ready CSVs for every interim election pair:

```bash
uv run electoral-transform-sejm-processed \
  data/interim/elections/sejm \
  data/processed/elections/sejm
```

The command creates one `<year>-sejm-gminy.csv` per election and one shared `regions.csv`.
Election files use the existing `electoral-import-elections` contract. The region dictionary uses
the `electoral-import-regions` contract and must be imported first.

The processed transformation:

- joins municipality totals with long committee results;
- uses explicit, complete mappings from PKW labels to readable committee names and political
  blocs;
- fails on an unknown committee rather than silently assigning it to `other`;
- calculates `vote_share` and `turnout` as percentage points rounded to four decimal places;
- verifies that committee votes equal valid votes for every municipality;
- rejects missing totals and duplicate processed facts;
- creates the region dictionary from the newest available metadata for each code.

The current processed identifier is PKW's six-character municipality code. The repository does
not yet contain a versioned TERYT reference with `RODZ_GMI`, so the transformation does not invent
a seventh digit or resolve historical boundary changes. `region_type` is therefore the honest,
general value `municipality`.

## Region CSV Import

Command:

```bash
uv run electoral-import-regions data/raw/regions.csv
```

Required columns:

- `teryt_code`
- `name`
- `region_type`

Optional columns:

- `voivodeship`
- `valid_from`
- `valid_to`

`valid_from` and `valid_to` use `YYYY-MM-DD` format. `teryt_code` is always read as text
so leading zeroes are preserved.

For the MVP, imported regions are municipalities (`gminy`). Election-source identifiers must be
normalized to the chosen municipality TERYT representation before loading results. County-level
rows are not the source observation unit and may be produced later as derived aggregates.

## Election Results CSV Import

Command:

```bash
uv run electoral-import-elections data/raw/election_results.csv
```

Required columns:

- `election_date`
- `election_type`
- `round`
- `teryt_code`
- `committee_name`
- `bloc_name`
- `votes`

Optional columns:

- `description`
- `vote_share`
- `turnout`
- `eligible_voters`
- `valid_votes`

The importer writes to `core.elections`, `core.committees`, and `core.election_results`.
Regions and political blocs must already exist. Percentages are stored as percentage
points, so `42.1000` means 42.1 percent.
