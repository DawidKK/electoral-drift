# Database Design Notes

`DB_CONFIG.md` is the source of truth for schema requirements.

The first implementation creates four PostgreSQL schemas:

- `raw` for source-shaped data.
- `core` for normalized source-of-truth tables.
- `analytics` for derived rankings, summaries, and stability labels.
- `ml` for modeling datasets, model runs, predictions, and metrics.

Important conventions:

- TERYT codes are stored as text.
- Election facts and political interpretations are separate.
- Socioeconomic observations use long format: one row per region, variable, and year.
- ML features for an election in year `Y` may only use data known no later than `Y - 1`.
