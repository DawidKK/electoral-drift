"""create initial electoral drift schemas

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


POLITICAL_BLOCS = [
    ("pis_bloc", "Normalized analytical bloc for PiS and aligned committees/candidates."),
    ("ko_bloc", "Normalized analytical bloc for KO and aligned committees/candidates."),
    ("left_bloc", "Normalized analytical bloc for left-wing committees/candidates."),
    ("psl_td_bloc", "Normalized analytical bloc for PSL, Third Way, and aligned groups."),
    ("confederation_bloc", "Normalized analytical bloc for Confederation."),
    ("other", "Other committees, local lists, or unmapped candidates."),
]


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS raw")
    op.execute("CREATE SCHEMA IF NOT EXISTS core")
    op.execute("CREATE SCHEMA IF NOT EXISTS analytics")
    op.execute("CREATE SCHEMA IF NOT EXISTS ml")

    op.create_table(
        "regions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("teryt_code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("region_type", sa.Text(), nullable=False),
        sa.Column("voivodeship", sa.Text()),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
        sa.UniqueConstraint("teryt_code", name="uq_regions_teryt_code"),
        schema="core",
    )
    op.create_table(
        "elections",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("election_date", sa.Date(), nullable=False),
        sa.Column("election_year", sa.Integer(), nullable=False),
        sa.Column("election_type", sa.Text(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("description", sa.Text()),
        schema="core",
    )
    op.create_index(
        "idx_elections_year_type", "elections", ["election_year", "election_type"], schema="core"
    )
    op.create_table(
        "political_blocs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.UniqueConstraint("name", name="uq_political_blocs_name"),
        schema="core",
    )
    op.create_table(
        "data_sources",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("downloaded_at", sa.DateTime()),
        sa.Column("description", sa.Text()),
        schema="core",
    )
    op.create_table(
        "socioeconomic_variables",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("unit", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.UniqueConstraint("code", name="uq_socioeconomic_variables_code"),
        schema="core",
    )
    op.create_table(
        "committees",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("election_id", sa.BigInteger(), nullable=False),
        sa.Column("bloc_id", sa.BigInteger()),
        sa.ForeignKeyConstraint(["bloc_id"], ["core.political_blocs.id"]),
        sa.ForeignKeyConstraint(["election_id"], ["core.elections.id"]),
        sa.UniqueConstraint("name", "election_id", name="uq_committees_name_election"),
        schema="core",
    )
    op.create_table(
        "election_results",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("region_id", sa.BigInteger(), nullable=False),
        sa.Column("election_id", sa.BigInteger(), nullable=False),
        sa.Column("committee_id", sa.BigInteger(), nullable=False),
        sa.Column("bloc_id", sa.BigInteger()),
        sa.Column("votes", sa.Integer()),
        sa.Column("vote_share", sa.Numeric(8, 4)),
        sa.Column("turnout", sa.Numeric(8, 4)),
        sa.Column("eligible_voters", sa.Integer()),
        sa.Column("valid_votes", sa.Integer()),
        sa.Column("source_id", sa.BigInteger()),
        sa.ForeignKeyConstraint(["bloc_id"], ["core.political_blocs.id"]),
        sa.ForeignKeyConstraint(["committee_id"], ["core.committees.id"]),
        sa.ForeignKeyConstraint(["election_id"], ["core.elections.id"]),
        sa.ForeignKeyConstraint(["region_id"], ["core.regions.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["core.data_sources.id"]),
        sa.UniqueConstraint(
            "region_id", "election_id", "committee_id", name="uq_election_results_fact"
        ),
        schema="core",
    )
    op.create_index(
        "idx_election_results_region_election",
        "election_results",
        ["region_id", "election_id"],
        schema="core",
    )
    op.create_index(
        "idx_election_results_committee", "election_results", ["committee_id"], schema="core"
    )
    op.create_index("idx_election_results_bloc", "election_results", ["bloc_id"], schema="core")
    op.create_table(
        "socioeconomic_observations",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("region_id", sa.BigInteger(), nullable=False),
        sa.Column("variable_id", sa.BigInteger(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("value", sa.Numeric()),
        sa.Column("source_id", sa.BigInteger()),
        sa.Column("source_note", sa.Text()),
        sa.ForeignKeyConstraint(["region_id"], ["core.regions.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["core.data_sources.id"]),
        sa.ForeignKeyConstraint(["variable_id"], ["core.socioeconomic_variables.id"]),
        sa.UniqueConstraint(
            "region_id", "variable_id", "year", name="uq_socioeconomic_observations_fact"
        ),
        schema="core",
    )
    op.create_index(
        "idx_socio_region_year",
        "socioeconomic_observations",
        ["region_id", "year"],
        schema="core",
    )
    op.create_index(
        "idx_socio_variable_year",
        "socioeconomic_observations",
        ["variable_id", "year"],
        schema="core",
    )

    op.create_table(
        "region_political_stability",
        sa.Column("region_id", sa.BigInteger(), primary_key=True),
        sa.Column("pis_wins", sa.Integer()),
        sa.Column("ko_wins", sa.Integer()),
        sa.Column("other_wins", sa.Integer()),
        sa.Column("switch_count", sa.Integer()),
        sa.Column("avg_winner_margin", sa.Numeric(8, 4)),
        sa.Column("avg_abs_pis_ko_margin", sa.Numeric(8, 4)),
        sa.Column("pis_ko_margin_trend", sa.Numeric(8, 4)),
        sa.Column("volatility_score", sa.Numeric(8, 4)),
        sa.Column("stability_label", sa.Text()),
        sa.ForeignKeyConstraint(["region_id"], ["core.regions.id"]),
        schema="analytics",
    )

    op.create_table(
        "model_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("trained_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("train_period", sa.Text()),
        sa.Column("test_period", sa.Text()),
        sa.Column("params", postgresql.JSONB()),
        sa.Column("metrics", postgresql.JSONB()),
        schema="ml",
    )
    op.create_table(
        "modeling_dataset",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("region_id", sa.BigInteger(), nullable=False),
        sa.Column("election_id", sa.BigInteger(), nullable=False),
        sa.Column("previous_pis_vote_share", sa.Numeric(8, 4)),
        sa.Column("previous_ko_vote_share", sa.Numeric(8, 4)),
        sa.Column("previous_pis_ko_margin", sa.Numeric(8, 4)),
        sa.Column("unemployment_level", sa.Numeric(12, 4)),
        sa.Column("unemployment_delta_4y", sa.Numeric(12, 4)),
        sa.Column("income_level", sa.Numeric(12, 4)),
        sa.Column("income_delta_4y", sa.Numeric(12, 4)),
        sa.Column("dominicantes_level", sa.Numeric(12, 4)),
        sa.Column("dominicantes_delta_4y", sa.Numeric(12, 4)),
        sa.Column("age_65_plus_level", sa.Numeric(12, 4)),
        sa.Column("age_65_plus_delta_4y", sa.Numeric(12, 4)),
        sa.Column("migration_balance_level", sa.Numeric(12, 4)),
        sa.Column("migration_balance_delta_4y", sa.Numeric(12, 4)),
        sa.Column("target_pis_vote_share", sa.Numeric(8, 4)),
        sa.Column("target_ko_vote_share", sa.Numeric(8, 4)),
        sa.Column("target_pis_ko_margin", sa.Numeric(8, 4)),
        sa.Column("target_margin_delta", sa.Numeric(8, 4)),
        sa.Column("target_winner_changed", sa.Boolean()),
        sa.ForeignKeyConstraint(["election_id"], ["core.elections.id"]),
        sa.ForeignKeyConstraint(["region_id"], ["core.regions.id"]),
        sa.UniqueConstraint("region_id", "election_id", name="uq_modeling_dataset_region_election"),
        schema="ml",
    )
    op.create_table(
        "predictions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("model_run_id", sa.BigInteger(), nullable=False),
        sa.Column("region_id", sa.BigInteger(), nullable=False),
        sa.Column("election_id", sa.BigInteger(), nullable=False),
        sa.Column("predicted_value", sa.Numeric(12, 4)),
        sa.Column("actual_value", sa.Numeric(12, 4)),
        sa.Column("residual", sa.Numeric(12, 4)),
        sa.ForeignKeyConstraint(["election_id"], ["core.elections.id"]),
        sa.ForeignKeyConstraint(["model_run_id"], ["ml.model_runs.id"]),
        sa.ForeignKeyConstraint(["region_id"], ["core.regions.id"]),
        sa.UniqueConstraint("model_run_id", "region_id", "election_id", name="uq_predictions_fact"),
        schema="ml",
    )

    political_blocs = sa.table(
        "political_blocs",
        sa.column("name", sa.Text()),
        sa.column("description", sa.Text()),
        schema="core",
    )
    op.bulk_insert(
        political_blocs,
        [{"name": name, "description": description} for name, description in POLITICAL_BLOCS],
    )

    op.execute(
        """
        CREATE VIEW analytics.region_election_summary AS
        SELECT
            er.region_id,
            er.election_id,
            e.election_year,
            e.election_type,
            pb.name AS bloc_name,
            SUM(er.votes) AS votes,
            ROUND((SUM(er.votes)::numeric / NULLIF(MAX(er.valid_votes), 0)) * 100, 4)
                AS vote_share
        FROM core.election_results er
        JOIN core.elections e ON e.id = er.election_id
        LEFT JOIN core.political_blocs pb ON pb.id = er.bloc_id
        GROUP BY er.region_id, er.election_id, e.election_year, e.election_type, pb.name
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS analytics.region_election_summary")
    op.drop_table("predictions", schema="ml")
    op.drop_table("modeling_dataset", schema="ml")
    op.drop_table("model_runs", schema="ml")
    op.drop_table("region_political_stability", schema="analytics")
    op.drop_index("idx_socio_variable_year", table_name="socioeconomic_observations", schema="core")
    op.drop_index("idx_socio_region_year", table_name="socioeconomic_observations", schema="core")
    op.drop_table("socioeconomic_observations", schema="core")
    op.drop_index("idx_election_results_bloc", table_name="election_results", schema="core")
    op.drop_index("idx_election_results_committee", table_name="election_results", schema="core")
    op.drop_index(
        "idx_election_results_region_election", table_name="election_results", schema="core"
    )
    op.drop_table("election_results", schema="core")
    op.drop_table("committees", schema="core")
    op.drop_table("socioeconomic_variables", schema="core")
    op.drop_table("data_sources", schema="core")
    op.drop_table("political_blocs", schema="core")
    op.drop_index("idx_elections_year_type", table_name="elections", schema="core")
    op.drop_table("elections", schema="core")
    op.drop_table("regions", schema="core")
    op.execute("DROP SCHEMA IF EXISTS ml")
    op.execute("DROP SCHEMA IF EXISTS analytics")
    op.execute("DROP SCHEMA IF EXISTS core")
    op.execute("DROP SCHEMA IF EXISTS raw")
