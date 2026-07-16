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
