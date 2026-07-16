# electoral-drift

Monorepo foundation for analyzing electoral drift across Polish counties.

The project starts with a PostgreSQL-backed database layer, Alembic migrations, and a
minimal FastAPI service. `DB_CONFIG.md` is the source of truth for database schema
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

Import regions from a UTF-8 CSV file:

```bash
uv run electoral-import-regions data/raw/regions.csv
```

Expected CSV columns:

```csv
teryt_code,name,region_type,voivodeship,valid_from,valid_to
0264011,Wroclaw,city_county,dolnoslaskie,1999-01-01,
```

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

Run tests:

```bash
uv run pytest
```

Run lint checks:

```bash
uv run ruff check .
```

Format code:

```bash
uv run ruff format .
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
