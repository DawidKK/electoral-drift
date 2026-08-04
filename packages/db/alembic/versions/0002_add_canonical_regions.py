"""add canonical regions

Revision ID: 0002_add_canonical_regions
Revises: 0001_initial_schema
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_canonical_regions"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "canonical_regions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("base_teryt_code", sa.String(length=6), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.UniqueConstraint("base_teryt_code", name="uq_canonical_regions_base_teryt_code"),
        schema="core",
    )
    op.add_column(
        "regions",
        sa.Column("canonical_region_id", sa.BigInteger(), nullable=True),
        schema="core",
    )
    op.create_foreign_key(
        "fk_regions_canonical_region_id",
        "regions",
        "canonical_regions",
        ["canonical_region_id"],
        ["id"],
        source_schema="core",
        referent_schema="core",
    )
    op.create_index(
        "idx_regions_canonical_region_id",
        "regions",
        ["canonical_region_id"],
        schema="core",
    )

    # Existing installations receive an immediately usable mapping. The latest election-backed
    # version supplies the display name; the CLI applies the same rule after future imports.
    op.execute(
        """
        INSERT INTO core.canonical_regions (base_teryt_code, name)
        SELECT DISTINCT ON (LEFT(region.teryt_code, 6))
            LEFT(region.teryt_code, 6),
            region.name
        FROM core.regions AS region
        LEFT JOIN core.election_results AS result ON result.region_id = region.id
        LEFT JOIN core.elections AS election ON election.id = result.election_id
        WHERE region.teryt_code ~ '^[0-9]{7}$'
        ORDER BY
            LEFT(region.teryt_code, 6),
            election.election_year DESC NULLS LAST,
            region.id DESC
        """
    )
    op.execute(
        """
        UPDATE core.regions AS region
        SET canonical_region_id = canonical.id
        FROM core.canonical_regions AS canonical
        WHERE canonical.base_teryt_code = LEFT(region.teryt_code, 6)
        """
    )


def downgrade() -> None:
    op.drop_index("idx_regions_canonical_region_id", table_name="regions", schema="core")
    op.drop_constraint(
        "fk_regions_canonical_region_id", "regions", schema="core", type_="foreignkey"
    )
    op.drop_column("regions", "canonical_region_id", schema="core")
    op.drop_table("canonical_regions", schema="core")
