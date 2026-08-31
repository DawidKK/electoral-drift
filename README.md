# electoral-drift

Monorepo foundation for analyzing electoral drift across Polish municipalities (`gminy`).

The project starts with a PostgreSQL-backed database layer, Alembic migrations, and a
minimal FastAPI service. `docs/database_schema.md` is the source of truth for database schema
requirements.

## Requirements

- Python 3.14
- uv
- Docker and Docker Compose

## Setup

Install Python dependencies for all workspace packages:

```bash
uv sync --all-packages
```

Copy local environment defaults if you want to customize ports or passwords:

```bash
cp .env.example .env
```

Start PostgreSQL and pgAdmin:

```bash
docker compose up -d db pgadmin
```

If local port `5432` is already in use, start PostgreSQL on another host port:

```bash
POSTGRES_PORT=5433 docker compose up -d db
DATABASE_URL=postgresql+psycopg://electoral:electoral@localhost:5433/electoral_db uv run alembic upgrade head
```

Run database migrations:

```bash
uv run alembic upgrade head
```

Transform a raw PKW Sejm export into municipality totals and long committee results:

```bash
uv run electoral-transform-sejm-interim \
  data/raw/elections/sejm/2019-sejm.csv \
  data/interim/elections/sejm
```

Supported source years are 2015, 2019, and 2023. See `docs/ingestion.md` for the interim schemas
and normalization rules.

Build importer-ready election results and a municipality dictionary:

```bash
uv run electoral-transform-sejm-processed \
  data/interim/elections/sejm \
  data/processed/elections/sejm \
  data/raw/teryt/terc
```

Processed election files can then be loaded with `electoral-import-elections`; import the
generated `regions.csv` first.

See [`docs/teryt_mapping.md`](docs/teryt_mapping.md) for a beginner-friendly explanation of PKW
codes, historical TERC mapping, and excluded non-municipality records.

Import regions from a UTF-8 CSV file:

```bash
uv run electoral-import-regions data/raw/regions.csv
```

Expected CSV columns:

```csv
teryt_code,name,region_type,voivodeship,valid_from,valid_to
0201011,Bolesławiec,urban_municipality,dolnoslaskie,1999-01-01,
```

Import election results from a UTF-8 CSV file:

```bash
uv run electoral-import-elections data/raw/election_results.csv
```

Expected CSV columns:

```csv
election_date,election_type,round,description,teryt_code,committee_name,bloc_name,votes,vote_share,turnout,eligible_voters,valid_votes
2019-10-13,parliamentary,1,Sejm 2019,0201011,Koalicja Obywatelska,ko_bloc,4308,23.9480,60.8770,29895,17989
```

Rebuild canonical municipality mappings after importing regions and election results:

```bash
uv run electoral-rebuild-canonical-regions
```

The command links historical seven-digit TERYT versions that share the same six-digit
municipality base. It preserves every source TERYT code and can be run repeatedly.

Start the API locally:

```bash
uv run uvicorn app.main:app --app-dir apps/api --reload
```

Then check:

```bash
curl http://127.0.0.1:8000/health
```

pgAdmin is available at `http://localhost:5050` by default.

## Development

For implementation, fixes, and refactoring in `apps/api`, `packages/db`, or the future
`packages/ml`, invoke the repository skill:

```text
$python-api-tdd
```

The skill requires an approved plan, a confirmed failing test, the smallest passing
implementation, refactoring, self-review, and all quality gates.

Run tests:

```bash
uv run pytest
```

Rebuild political-stability analytics after importing election results:

```bash
uv run electoral-rebuild-stability
```

The batch command replaces `analytics.region_political_stability` atomically. Read the resulting
ranking through `GET /analytics/stability-ranking` or the changing municipalities through
`GET /analytics/swing-counties`. The latter route retains its current name for API compatibility.
Both endpoints accept `limit` from 1 to 1000.

Run lint checks:

```bash
uv run ruff check .
```

Check formatting:

```bash
uv run ruff format --check .
```

Run type and architecture checks:

```bash
uv run mypy apps/api packages/db
uv run lint-imports
```

## Repository Layout

```text
apps/api/      FastAPI application
packages/db/   SQLAlchemy models, DB settings, Alembic migrations
packages/ingestion/ CSV import utilities for source data
data/          raw, interim, and processed reproducible datasets
docs/          API and database notes
```

The frontend is intentionally deferred until the minimal API contract is useful enough
to support dashboard work.
