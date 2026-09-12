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
- skips foreign rows without a municipality TERYT code and reports their count;
- skips PKW's synthetic `zagranica` and `statki` regions even when they have a six-digit code.

Interim output remains source-oriented. Committee normalization and political-bloc assignment
belong to the interim-to-processed transformation. Enrichment with the full TERYT representation
and resolution of historical territorial changes require a versioned reference dataset and
remain a later step.

## Sejm Interim to Processed

Build importer-ready CSVs for every interim election pair:

```bash
uv run electoral-transform-sejm-processed \
  data/interim/elections/sejm \
  data/processed/elections/sejm \
  data/raw/teryt/terc
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
- requires a historical `<year>-01-01.csv` TERC snapshot for every election;
- resolves the six-character PKW code to a seven-character historical TERC identifier;
- takes the municipality name, type, and voivodeship from the matching TERC snapshot;
- creates the region dictionary from the newest available metadata for each full code.

Only whole-municipality TERC records are eligible: types `1`, `2`, `3`, `8`, and `9`. City and
rural-area subdivisions of an urban-rural municipality (`4` and `5`) are excluded because PKW
reports the municipality as a whole. A municipality whose official type changes over time receives
a different full TERC identifier; a future analytical crosswalk may link such histories without
rewriting the source facts.

## GUS/BDL P2670 Raw to Interim

The unemployment input is the GUS/BDL P2670 indicator, *registered unemployed persons as a share
of the working-age population*. It is not the official registered unemployment rate, whose
denominator is the economically active civilian population.

Transform the immutable wide export into source-oriented long observations:

```bash
uv run electoral-transform-bdl-unemployment-interim \
  data/raw/features/bezrobocie_2014_2025.csv \
  data/interim/features/bezrobocie_2014_2025-long.csv
```

The transformation:

- requires `Kod`, `Nazwa`, and ascending `ogółem;<year>;[%]` columns;
- preserves seven-digit TERC identifiers as text;
- converts decimal commas to exact decimal values;
- emits one row per historical municipality code and year;
- keeps only whole municipalities of types `1`, `2`, and `3`;
- reports and excludes national, voivodeship, and county aggregates and types `4` and `5`;
- skips empty values without replacing them with zero;
- rejects duplicates, unsupported geography, and percentages outside `0`–`100`;
- carries the raw file SHA-256 into every interim observation.

For the repository source file this produces 29,732 observations for 2014–2025. Its SHA-256 is
`2eb9eb1ed57d2fa505521b69ab067dfcf6c6287400ca93d4311f3aa554b4717b`.

## Historical TERC Region Dictionary

Build the shared importer-ready region dictionary before importing socioeconomic observations:

```bash
uv run electoral-transform-terc-regions \
  data/raw/teryt/terc \
  data/processed/regions/terc-2014-2025.csv

uv run electoral-import-regions \
  data/processed/regions/terc-2014-2025.csv
```

The dictionary reads every annual `<year>-01-01.csv`, verifies the exact `STAN_NA`, retains types
`1`, `2`, `3`, `8`, and `9`, and uses the newest available official metadata for each full code.
Feature-specific importers never create regions implicitly.

## GUS/BDL P2670 Interim to Processed

Validate every long observation against the TERC snapshot for its year:

```bash
uv run electoral-transform-bdl-unemployment-processed \
  data/interim/features/bezrobocie_2014_2025-long.csv \
  data/processed/features/bezrobocie_2014_2025-gminy.csv \
  data/raw/teryt/terc
```

The transformation requires an exact full-code match in `<year>-01-01.csv`. One declared
historical exception uses `2018-01-02.csv` for Chełmiec (`1210022`): TERC represented it as an
urban-rural municipality on 1 January, but the change was reversed the next day and BDL reports
the annual observation under the restored rural code. No general fallback or name-based mapping
is allowed.

## GUS/BDL P2670 Database Import

Import the validated observations after the shared region dictionary:

```bash
uv run electoral-import-bdl-unemployment \
  data/processed/features/bezrobocie_2014_2025-gminy.csv
```

The command writes:

- `registered_unemployed_working_age_share` to `core.socioeconomic_variables`;
- GUS/BDL P2670 URL, download date, and raw hash to `core.data_sources`;
- long municipality-year facts to `core.socioeconomic_observations`.

Values are percentage points, so `6.5` means 6.5%. The import resolves regions and existing
observations in batches. Reimporting the identical source is a no-op. A missing region, changed
variable metadata, different provenance, or conflicting value rolls back the entire transaction.

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
