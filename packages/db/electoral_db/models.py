from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Date,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from electoral_db.base import Base


class Region(Base):
    __tablename__ = "regions"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    teryt_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    region_type: Mapped[str] = mapped_column(Text, nullable=False)
    voivodeship: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)

    election_results: Mapped[list[ElectionResult]] = relationship(back_populates="region")
    socioeconomic_observations: Mapped[list[SocioeconomicObservation]] = relationship(
        back_populates="region"
    )


class Election(Base):
    __tablename__ = "elections"
    __table_args__ = (
        Index("idx_elections_year_type", "election_year", "election_type"),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    election_date: Mapped[date] = mapped_column(Date, nullable=False)
    election_year: Mapped[int] = mapped_column(Integer, nullable=False)
    election_type: Mapped[str] = mapped_column(Text, nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    description: Mapped[str | None] = mapped_column(Text)

    committees: Mapped[list[Committee]] = relationship(back_populates="election")
    election_results: Mapped[list[ElectionResult]] = relationship(back_populates="election")


class PoliticalBloc(Base):
    __tablename__ = "political_blocs"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    committees: Mapped[list[Committee]] = relationship(back_populates="bloc")


class Committee(Base):
    __tablename__ = "committees"
    __table_args__ = (
        UniqueConstraint("name", "election_id", name="uq_committees_name_election"),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    election_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.elections.id"), nullable=False
    )
    bloc_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("core.political_blocs.id"))

    election: Mapped[Election] = relationship(back_populates="committees")
    bloc: Mapped[PoliticalBloc | None] = relationship(back_populates="committees")
    election_results: Mapped[list[ElectionResult]] = relationship(back_populates="committee")


class DataSource(Base):
    __tablename__ = "data_sources"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    downloaded_at: Mapped[datetime | None]
    description: Mapped[str | None] = mapped_column(Text)


class ElectionResult(Base):
    __tablename__ = "election_results"
    __table_args__ = (
        UniqueConstraint(
            "region_id", "election_id", "committee_id", name="uq_election_results_fact"
        ),
        Index("idx_election_results_region_election", "region_id", "election_id"),
        Index("idx_election_results_committee", "committee_id"),
        Index("idx_election_results_bloc", "bloc_id"),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    region_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.regions.id"), nullable=False
    )
    election_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.elections.id"), nullable=False
    )
    committee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.committees.id"), nullable=False
    )
    bloc_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("core.political_blocs.id"))
    votes: Mapped[int | None] = mapped_column(Integer)
    vote_share: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    turnout: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    eligible_voters: Mapped[int | None] = mapped_column(Integer)
    valid_votes: Mapped[int | None] = mapped_column(Integer)
    source_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("core.data_sources.id"))

    region: Mapped[Region] = relationship(back_populates="election_results")
    election: Mapped[Election] = relationship(back_populates="election_results")
    committee: Mapped[Committee] = relationship(back_populates="election_results")


class SocioeconomicVariable(Base):
    __tablename__ = "socioeconomic_variables"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)

    observations: Mapped[list[SocioeconomicObservation]] = relationship(
        back_populates="variable"
    )


class SocioeconomicObservation(Base):
    __tablename__ = "socioeconomic_observations"
    __table_args__ = (
        UniqueConstraint(
            "region_id", "variable_id", "year", name="uq_socioeconomic_observations_fact"
        ),
        Index("idx_socio_region_year", "region_id", "year"),
        Index("idx_socio_variable_year", "variable_id", "year"),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    region_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.regions.id"), nullable=False
    )
    variable_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.socioeconomic_variables.id"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric)
    source_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("core.data_sources.id"))
    source_note: Mapped[str | None] = mapped_column(Text)

    region: Mapped[Region] = relationship(back_populates="socioeconomic_observations")
    variable: Mapped[SocioeconomicVariable] = relationship(back_populates="observations")


class RegionPoliticalStability(Base):
    __tablename__ = "region_political_stability"
    __table_args__ = {"schema": "analytics"}

    region_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.regions.id"), primary_key=True
    )
    pis_wins: Mapped[int | None] = mapped_column(Integer)
    ko_wins: Mapped[int | None] = mapped_column(Integer)
    other_wins: Mapped[int | None] = mapped_column(Integer)
    switch_count: Mapped[int | None] = mapped_column(Integer)
    avg_winner_margin: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    avg_abs_pis_ko_margin: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    pis_ko_margin_trend: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    volatility_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    stability_label: Mapped[str | None] = mapped_column(Text)


class ModelingDataset(Base):
    __tablename__ = "modeling_dataset"
    __table_args__ = (
        UniqueConstraint("region_id", "election_id", name="uq_modeling_dataset_region_election"),
        {"schema": "ml"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    region_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.regions.id"), nullable=False
    )
    election_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.elections.id"), nullable=False
    )
    previous_pis_vote_share: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    previous_ko_vote_share: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    previous_pis_ko_margin: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    unemployment_level: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    unemployment_delta_4y: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    income_level: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    income_delta_4y: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    dominicantes_level: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    dominicantes_delta_4y: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    age_65_plus_level: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    age_65_plus_delta_4y: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    migration_balance_level: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    migration_balance_delta_4y: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    target_pis_vote_share: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    target_ko_vote_share: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    target_pis_ko_margin: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    target_margin_delta: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    target_winner_changed: Mapped[bool | None]


class ModelRun(Base):
    __tablename__ = "model_runs"
    __table_args__ = {"schema": "ml"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    train_period: Mapped[str | None] = mapped_column(Text)
    test_period: Mapped[str | None] = mapped_column(Text)
    params: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    predictions: Mapped[list[Prediction]] = relationship(back_populates="model_run")


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint("model_run_id", "region_id", "election_id", name="uq_predictions_fact"),
        {"schema": "ml"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    model_run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ml.model_runs.id"), nullable=False
    )
    region_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.regions.id"), nullable=False
    )
    election_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.elections.id"), nullable=False
    )
    predicted_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    actual_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    residual: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))

    model_run: Mapped[ModelRun] = relationship(back_populates="predictions")
