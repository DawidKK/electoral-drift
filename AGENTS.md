# AGENTS.md

## Instruction scope

These instructions apply to the entire repository unless a more specific `AGENTS.md` file exists in a subdirectory.

This repository is intended to be a monorepo for an analytical and machine learning project focused on regional electoral shifts in Poland. The project combines a backend API, PostgreSQL database, data ingestion pipelines, classical machine learning workflows, and a frontend/dashboard.

## Project goal

The goal is to build an application and data pipeline for analyzing political drift across Polish counties (`powiaty`).

The project should support:

- ingesting and normalizing election results from PKW,
- ingesting and normalizing socioeconomic data from GUS/BDL and other public sources,
- storing structured data in PostgreSQL,
- identifying stable, swing, and potentially shifting regions,
- building leakage-safe ML datasets,
- training classical machine learning models such as historical baselines, ElasticNet, XGBoost, or LightGBM,
- storing model runs, predictions, and metrics,
- exposing data through FastAPI,
- presenting results in a React client/dashboard.

Main analytical question:

> Can public data — election results, demography, economics, migration, urbanization, and religiosity — help identify and forecast regional electoral shifts?

## Domain assumptions

The MVP should analyze data at the county level (`powiat`). Municipalities (`gminy`) may be added later.

Core concepts:

- `region` — a territorial unit, initially a county or city with county rights,
- `election` — a specific election, for example the 2023 parliamentary election or the second round of the 2020 presidential election,
- `committee` — a specific committee, party list, party, or candidate in a given election,
- `political_bloc` — a normalized analytical bloc, for example `pis_bloc`, `ko_bloc`, `left_bloc`, `other`,
- `socioeconomic_observation` — a value of a structural variable for a region in a given year,
- `political_drift` — a change in support, margin, or winning bloc in a region across elections.

Do not assume that party or committee names are stable over time. Committees and candidates must be mapped to normalized political blocs.

## Target technology stack

Use the following technologies unless the user explicitly decides otherwise:

- Python 3.14
- FastAPI for the HTTP backend,
- PostgreSQL as the main database,
- Docker and Docker Compose for local services,
- SQLAlchemy for database models and database access,
- Alembic for migrations,
- `uv` for Python dependency management,
- pandas or Polars for data processing,
- scikit-learn, XGBoost or LightGBM, and SHAP in the ML package,
- React for the frontend,
- pgAdmin for database inspection and administration,
- pytest for Python tests.

When choosing between simplicity and excessive architecture, prefer simplicity. However, do not mix responsibilities between apps and packages.

## Monorepo structure

The repository should eventually follow a structure similar to this:

```text
electoral-drift-ml/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── routers/
│   │   │   ├── services/
│   │   │   ├── schemas/
│   │   │   └── core/
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   └── web/
│       ├── src/
│       ├── package.json
│       └── Dockerfile
│
├── packages/
│   ├── db/
│   │   ├── electoral_db/
│   │   ├── alembic/
│   │   ├── tests/
│   │   └── pyproject.toml
│   │
│   ├── ingestion/
│   │   ├── electoral_ingestion/
│   │   ├── tests/
│   │   └── pyproject.toml
│   │
│   └── ml/
│       ├── electoral_ml/
│       ├── notebooks/
│       ├── tests/
│       └── pyproject.toml
│
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
│
├── docs/
│   ├── DB_CONFIG.md
│   ├── database_design.md
│   ├── ml_methodology.md
│   └── api_contract.md
│
├── infra/
├── docker-compose.yml
├── AGENTS.md
├── DB_CONFIG.md
├── README.md
└── .env.example
```

If the repository is still being initialized, create this structure iteratively. Do not create empty directories unless they are useful for project clarity.

## Responsibility boundaries

### `apps/api`

FastAPI application.

Responsibilities:

- HTTP endpoints,
- request and response validation through Pydantic,
- database communication through the DB layer,
- returning data about regions, elections, results, rankings, and predictions,
- lightweight application logic.

The API must not train models or run heavy feature engineering inside HTTP requests.

### `apps/web`

React application.

Responsibilities:

- dashboard UI,
- maps,
- ranking tables,
- region/county detail views,
- trend charts,
- prediction result presentation.

The frontend should communicate with the backend only through public API endpoints.

### `packages/db`

Database package.

Responsibilities:

- SQLAlchemy models,
- Alembic migrations,
- PostgreSQL connection configuration,
- schema definitions for `raw`, `core`, `analytics`, and `ml`,
- dictionary seed data, for example `political_blocs`, if needed.

The detailed database design lives in `DB_CONFIG.md`. Treat `DB_CONFIG.md` as the source of requirements for database schema implementation.

### `packages/ingestion`

Data ingestion package.

Responsibilities:

- downloading or loading PKW election data,
- downloading or loading GUS/BDL data,
- TERYT normalization,
- input validation and cleaning,
- loading data into `raw`, `core`, or files under `data/raw` and `data/interim`.

Ingestion code must not contain model training code.

### `packages/ml`

Machine learning package.

Responsibilities:

- building modeling datasets,
- feature engineering,
- target engineering,
- historical baselines,
- model training,
- time-aware evaluation,
- prediction generation,
- writing model outputs to the `ml` schema,
- model interpretation, for example SHAP.

The ML pipeline should run as a batch job. The API should read stored predictions from the database, not train models live.

## Data layers

Use the following separation of data layers:

```text
raw        → source data or data as close to the source as practical
core       → normalized facts and dictionaries
analytics  → views, aggregates, rankings, political stability metrics
ml         → modeling datasets, model runs, predictions
```

Do not mix source, analytical, and model data in a single table.

Facts and interpretations must be separated. Example:

- fact: a committee received 42.3% in county X,
- interpretation: the committee belongs to `pis_bloc`,
- derived interpretation: county X is `safe_pis` or `swing`.

## Database design rules

Follow `DB_CONFIG.md` when designing the database. Most important summarized requirements:

- PostgreSQL is the main database.
- Store TERYT codes as text, never as integers.
- Relationships between tables must be explicit through foreign keys.
- Each table should have one responsibility.
- Store election data separately from annual structural data.
- Store GUS/BDL data in long format: `region`, `variable`, `year`, `value`.
- The ML dataset is a derived layer and must be reproducible.
- For an election in year `Y`, model features may only use data known no later than year `Y - 1`.
- Add `UNIQUE` constraints to prevent duplicates.
- Add indexes for frequent joins and filters.

## Docker and local development

The project should support local development through Docker Compose.

Minimal services:

- `db` — PostgreSQL,
- `api` — FastAPI,
- `web` — React,
- optional `ml` — manually triggered ML job/pipeline,
- optional `pgadmin` — PostgreSQL administration panel.

Preferred minimal PostgreSQL service:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: electoral
      POSTGRES_PASSWORD: electoral
      POSTGRES_DB: electoral_db
    ports:
      - "5432:5432"
    volumes:
      - electoral_postgres_data:/var/lib/postgresql/data

volumes:
  electoral_postgres_data:
```

The repository should include `.env.example` with sample configuration but no production secrets.

Example variables:

```env
DATABASE_URL=postgresql+psycopg://electoral:electoral@localhost:5432/electoral_db
POSTGRES_USER=electoral
POSTGRES_PASSWORD=electoral
POSTGRES_DB=electoral_db
```

## Dependency management

Use `uv` for Python code.

Preferred commands:

```bash
uv sync
uv add fastapi sqlalchemy alembic psycopg pydantic
uv add --dev pytest ruff mypy
```

For `apps/web`, use the Node package manager selected for the project. Prefer `pnpm` if no other choice exists.

## Migrations

Use Alembic for database schema changes.

Do not create tables manually in pgAdmin as the main way of evolving the schema. pgAdmin is for inspection, debugging, and manual database exploration.

Every schema change should have a migration.

Preferred commands should be documented in `README.md` or `Makefile`, for example:

```bash
alembic revision --autogenerate -m "create core tables"
alembic upgrade head
alembic downgrade -1
```

## API — expected endpoint areas

The project should eventually support endpoints similar to:

```text
GET /health
GET /regions
GET /regions/{region_id}
GET /regions/{region_id}/elections
GET /regions/{region_id}/socioeconomic
GET /elections
GET /elections/{election_id}/results
GET /analytics/stability-ranking
GET /analytics/swing-counties
GET /analytics/region/{region_id}/timeline
GET /ml/model-runs
GET /ml/predictions
```

Do not implement everything at once if the user asks only for setup. Preserve a structure that enables later expansion.

## ML methodology rules

In the ML package:

- compare models against a historical baseline first,
- do not use random county-level splits as the main validation strategy,
- prefer time-aware validation, for example training on earlier elections and testing on later elections,
- explicitly prevent time leakage,
- store metrics, parameters, and predictions,
- interpret results with SHAP or other explainability tools only after proper evaluation.

Example target:

```text
target_margin_delta = pis_ko_margin_current - pis_ko_margin_previous
```

Example features:

```text
previous_pis_vote_share
previous_ko_vote_share
previous_pis_ko_margin
unemployment_level
unemployment_delta_4y
income_level
income_delta_4y
dominicantes_level
dominicantes_delta_4y
age_65_plus_level
age_65_plus_delta_4y
migration_balance_level
migration_balance_delta_4y
```

## Code and style

Follow these rules:

- write readable and typed code,
- use Python type hints,
- avoid global state,
- keep business logic in `services`, not in FastAPI routers,
- keep Pydantic schemas separate from SQLAlchemy models,
- do not commit secrets,
- use `.env.example` for sample configuration,
- add tests for data transformations, migrations, and key endpoints,
- update documentation when changing repo structure or database design.

## Tests and quality

Eventually support:

```bash
pytest
ruff check .
ruff format .
mypy .
```

If these tools are not configured yet, do not assume they exist. Add them iteratively and document usage in `README.md`.

Useful early tests:

- database connection test,
- migration/table creation test,
- `UNIQUE` constraint test,
- sample region import test,
- simple `switch_count` calculation test,
- `/health` endpoint test.

## Documentation

Keep documentation in Markdown.

Important files:

- `AGENTS.md` — instructions for Codex and high-level repository guidance,
- `DB_CONFIG.md` — detailed database design documentation,
- `README.md` — project setup and run instructions,
- `docs/api_contract.md` — API contract once endpoints are defined,
- `docs/ml_methodology.md` — ML methodology once the pipeline is built.

`DB_CONFIG.md` should remain the technical database document. Do not move the full database documentation into `AGENTS.md`; `AGENTS.md` should only reference `DB_CONFIG.md` as the schema requirements source.

## Acceptance criteria for the first setup

The first project setup should eventually allow:

1. running PostgreSQL through Docker Compose,
2. connecting to the database through pgAdmin or another SQL client,
3. running FastAPI locally,
4. calling the `/health` endpoint,
5. running Alembic migrations,
6. creating the base database schemas,
7. preserving a monorepo structure with `apps/` and `packages/`,
8. using `uv` for Python dependencies,
9. having `.env.example`,
10. having documentation in `README.md`, `AGENTS.md`, and `DB_CONFIG.md`.

## Do not do unless needed

- Do not implement the full ML model if the task is only project setup.
- Do not create microservices without a clear need.
- Do not train models inside API requests.
- Do not store full large datasets in Git if they can be reproduced from public sources.
- Do not mix data ingestion code with FastAPI code.
- Do not commit secrets or production passwords.
- Do not design the frontend before a minimal API contract exists.

## Preferred workflow

Work iteratively:

1. repository and Docker setup,
2. PostgreSQL configuration,
3. migrations and minimal schema,
4. seed base dictionaries,
5. minimal API,
6. sample data ingestion,
7. first analytical aggregates,
8. ML dataset,
9. models,
10. dashboard.

Every change should support the core project goal: analyzing and modeling regional electoral shifts in Poland.
