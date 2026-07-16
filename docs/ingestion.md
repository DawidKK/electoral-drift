# Ingestion

The ingestion package loads public source data into the database before the API reads it.
This keeps heavy data preparation out of HTTP requests.

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
