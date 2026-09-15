#!/bin/bash
set -e

# System landscape
tld add "Electoral Drift" --ref electoral-drift --kind system --description "Analiza i modelowanie zmian poparcia wyborczego na poziomie gmin."
tld add "Analityk / klient HTTP" --ref analyst --kind person --position-x -600 --position-y 0
tld add "PKW" --ref pkw --kind "external system" --description "Źródło plików CSV z wynikami wyborów do Sejmu." --position-x -600 --position-y 240
tld add "GUS / BDL" --ref gus-bdl --kind "external system" --description "Źródło wskaźnika P2670 i kolejnych danych społeczno-ekonomicznych." --position-x -600 --position-y 480
tld connect --from analyst --to electoral-drift --label "odpytuje dane i analitykę" --view root
tld connect --from pkw --to electoral-drift --label "dostarcza wyniki wyborów" --view root
tld connect --from gus-bdl --to electoral-drift --label "dostarcza dane społeczno-ekonomiczne" --view root

# Current application flow
tld add "Analityk / klient HTTP" --ref analyst --kind person --parent electoral-drift --position-x 1500 --position-y 0
tld add "PKW" --ref pkw --kind "external system" --parent electoral-drift --position-x 0 --position-y 0
tld add "GUS / BDL" --ref gus-bdl --kind "external system" --parent electoral-drift --position-x 0 --position-y 260
tld add "Repozytorium plików danych" --ref data-files --kind container --parent electoral-drift --description "Wersjonowane lub odtwarzalne pliki raw, interim i processed." --position-x 300 --position-y 130
tld add "Pipeline ingestion" --ref ingestion --kind container --parent electoral-drift --technology Python --description "Waliduje i transformuje PKW, TERC oraz GUS/BDL, a następnie uruchamia importy batch." --position-x 600 --position-y 130
tld add "Pakiet bazodanowy" --ref db-package --kind container --parent electoral-drift --technology SQLAlchemy --description "Modele, sesje, migracje i batchowe obliczenia analityczne." --position-x 900 --position-y 130
tld add "PostgreSQL" --ref postgres --kind database --parent electoral-drift --technology PostgreSQL --description "Trwałe warstwy core, analytics i ml." --position-x 1200 --position-y 130
tld add "FastAPI API" --ref api --kind container --parent electoral-drift --technology FastAPI --description "Publiczny odczyt regionów, wyborów, timeline i stabilności." --position-x 1200 --position-y -130
tld add "pgAdmin" --ref pgadmin --kind component --parent electoral-drift --description "Narzędzie administracyjne uruchamiane przez Docker Compose." --position-x 1200 --position-y 390
tld add "Bramki jakości" --ref quality-gates --kind component --parent electoral-drift --technology pytest --description "TDD, pytest, Ruff, mypy oraz Import Linter dla zmian Python." --position-x 900 --position-y -130
tld connect --from pkw --to data-files --label "publikuje CSV wyborcze" --view electoral-drift
tld connect --from gus-bdl --to data-files --label "publikuje P2670" --view electoral-drift
tld connect --from data-files --to ingestion --label "raw → interim → processed" --view electoral-drift
tld connect --from ingestion --to db-package --label "używa modeli i sesji" --view electoral-drift
tld connect --from db-package --to postgres --label "migruje, zapisuje i odczytuje" --view electoral-drift
tld connect --from api --to db-package --label "wykonuje zapytania odczytowe" --view electoral-drift
tld connect --from analyst --to api --label "HTTP / JSON" --direction both --view electoral-drift
tld connect --from pgadmin --to postgres --label "administruje" --view electoral-drift
tld connect --from quality-gates --to api --label "weryfikuje" --view electoral-drift
tld connect --from quality-gates --to db-package --label "weryfikuje" --view electoral-drift

# API overview
tld add "Analityk / klient HTTP" --ref analyst --kind person --parent api --position-x 0 --position-y 150
tld add "Composition root" --ref api-main --kind component --parent api --technology FastAPI --description "app/main.py rejestruje kompletne routery feature’ów." --position-x 300 --position-y 150
tld add "Health" --ref api-health --kind component --parent api --description "GET /health bez dostępu do bazy." --position-x 600 --position-y 0
tld add "Regions" --ref api-regions --kind component --parent api --description "Regiony, wybory regionu i timeline bloków." --position-x 600 --position-y 120
tld add "Elections" --ref api-elections --kind component --parent api --description "Katalog wyborów i wyniki komitetów." --position-x 600 --position-y 240
tld add "Analytics" --ref api-analytics --kind component --parent api --description "Ranking stabilności oraz gminy swing/emerging shift." --position-x 600 --position-y 360
tld add "Request-scoped DB Session" --ref api-db-session --kind component --parent api --technology SQLAlchemy --description "infrastructure/database.py udostępnia sesję na czas requestu." --position-x 900 --position-y 240
tld add "Pakiet bazodanowy" --ref db-package --kind container --parent api --technology SQLAlchemy --position-x 1200 --position-y 240
tld connect --from analyst --to api-main --label "wysyła request / odbiera JSON" --direction both --view api
tld connect --from api-main --to api-health --label "rejestruje router" --view api
tld connect --from api-main --to api-regions --label "rejestruje router" --view api
tld connect --from api-main --to api-elections --label "rejestruje router" --view api
tld connect --from api-main --to api-analytics --label "rejestruje router" --view api
tld connect --from api-regions --to api-db-session --label "pobiera sesję" --view api
tld connect --from api-elections --to api-db-session --label "pobiera sesję" --view api
tld connect --from api-analytics --to api-db-session --label "pobiera sesję" --view api
tld connect --from api-db-session --to db-package --label "deleguje cykl życia sesji" --view api

# API: regions
tld add "Regions router" --ref regions-router --kind component --parent api-regions --technology FastAPI --description "GET /regions, /{teryt_code}, /elections i /timeline." --position-x 0 --position-y 120
tld add "RegionQueries" --ref regions-queries --kind component --parent api-regions --technology SQLAlchemy --description "Zapytania i mapowanie ORM/SQL na DTO regionów." --position-x 300 --position-y 120
tld add "Region DTO" --ref regions-schemas --kind component --parent api-regions --description "Pydantic schemas dla regionu, wyborów regionu i timeline." --position-x 600 --position-y 0
tld add "Request-scoped DB Session" --ref api-db-session --kind component --parent api-regions --technology SQLAlchemy --position-x 0 --position-y 360
tld add "core.regions" --ref core-regions --kind database --parent api-regions --technology PostgreSQL --position-x 600 --position-y 120
tld add "core.canonical_regions" --ref core-canonical-regions --kind database --parent api-regions --technology PostgreSQL --position-x 600 --position-y 240
tld add "core.elections + election_results" --ref core-election-facts --kind database --parent api-regions --technology PostgreSQL --position-x 600 --position-y 360
tld add "analytics.region_election_summary" --ref analytics-summary --kind database --parent api-regions --technology PostgreSQL --position-x 600 --position-y 480
tld connect --from regions-router --to regions-queries --label "wywołuje use case" --view api-regions
tld connect --from api-db-session --to regions-queries --label "wstrzykuje sesję" --view api-regions
tld connect --from regions-queries --to regions-schemas --label "buduje DTO" --view api-regions
tld connect --from regions-queries --to core-regions --label "czyta region" --view api-regions
tld connect --from regions-queries --to core-canonical-regions --label "zwraca canonical_region_id" --view api-regions
tld connect --from regions-queries --to core-election-facts --label "czyta wybory regionu" --view api-regions
tld connect --from regions-queries --to analytics-summary --label "czyta timeline bloków" --view api-regions

# API: elections
tld add "Elections router" --ref elections-router --kind component --parent api-elections --technology FastAPI --description "GET /elections i /{election_id}/results." --position-x 0 --position-y 120
tld add "ElectionQueries" --ref elections-queries --kind component --parent api-elections --technology SQLAlchemy --description "Katalog wyborów oraz połączone fakty wyników." --position-x 300 --position-y 120
tld add "Election DTO" --ref elections-schemas --kind component --parent api-elections --description "Pydantic schemas katalogu i wyniku komitetu." --position-x 600 --position-y 0
tld add "Request-scoped DB Session" --ref api-db-session --kind component --parent api-elections --technology SQLAlchemy --position-x 0 --position-y 360
tld add "core.elections" --ref core-elections --kind database --parent api-elections --technology PostgreSQL --position-x 600 --position-y 120
tld add "core.election_results" --ref core-election-results --kind database --parent api-elections --technology PostgreSQL --position-x 600 --position-y 240
tld add "core.regions" --ref core-regions --kind database --parent api-elections --technology PostgreSQL --position-x 900 --position-y 120
tld add "core.committees + political_blocs" --ref core-election-dictionaries --kind database --parent api-elections --technology PostgreSQL --position-x 900 --position-y 240
tld connect --from elections-router --to elections-queries --label "wywołuje use case" --view api-elections
tld connect --from api-db-session --to elections-queries --label "wstrzykuje sesję" --view api-elections
tld connect --from elections-queries --to elections-schemas --label "buduje DTO" --view api-elections
tld connect --from elections-queries --to core-elections --label "czyta katalog" --view api-elections
tld connect --from elections-queries --to core-election-results --label "czyta fakty" --view api-elections
tld connect --from core-election-results --to core-regions --label "łączy region" --view api-elections
tld connect --from core-election-results --to core-election-dictionaries --label "łączy komitet i blok" --view api-elections

# API: analytics
tld add "Analytics router" --ref analytics-router --kind component --parent api-analytics --technology FastAPI --description "GET /analytics/stability-ranking i /swing-counties." --position-x 0 --position-y 120
tld add "AnalyticsQueries" --ref analytics-queries --kind component --parent api-analytics --technology SQLAlchemy --description "Odczytuje i filtruje gotowy snapshot stabilności." --position-x 300 --position-y 120
tld add "Stability DTO" --ref analytics-schemas --kind component --parent api-analytics --description "Publiczny kontrakt metryk stabilności." --position-x 600 --position-y 0
tld add "Request-scoped DB Session" --ref api-db-session --kind component --parent api-analytics --technology SQLAlchemy --position-x 0 --position-y 360
tld add "analytics.region_political_stability" --ref analytics-stability --kind database --parent api-analytics --technology PostgreSQL --position-x 600 --position-y 180
tld add "core.regions" --ref core-regions --kind database --parent api-analytics --technology PostgreSQL --position-x 900 --position-y 180
tld connect --from analytics-router --to analytics-queries --label "wywołuje ranking lub filtr" --view api-analytics
tld connect --from api-db-session --to analytics-queries --label "wstrzykuje sesję" --view api-analytics
tld connect --from analytics-queries --to analytics-schemas --label "buduje DTO" --view api-analytics
tld connect --from analytics-queries --to analytics-stability --label "czyta snapshot" --view api-analytics
tld connect --from analytics-stability --to core-regions --label "łączy nazwę i TERYT" --view api-analytics

# Ingestion overview
tld add "Ingestion CLI" --ref ingestion-cli --kind component --parent ingestion --technology Python --description "Entry pointy transformacji i importów batch." --position-x 0 --position-y 180
tld add "Pipeline Sejm" --ref sejm-pipeline --kind component --parent ingestion --technology Python --position-x 300 --position-y 0
tld add "Pipeline TERC" --ref terc-pipeline --kind component --parent ingestion --technology Python --position-x 300 --position-y 180
tld add "Pipeline GUS/BDL P2670" --ref unemployment-pipeline --kind component --parent ingestion --technology Python --position-x 300 --position-y 360
tld add "Import regionów" --ref regions-import --kind component --parent ingestion --technology SQLAlchemy --position-x 600 --position-y 60
tld add "Import wyborów" --ref elections-import --kind component --parent ingestion --technology SQLAlchemy --position-x 600 --position-y 180
tld add "Import P2670" --ref socioeconomic-import --kind component --parent ingestion --technology SQLAlchemy --position-x 600 --position-y 300
tld add "Pakiet bazodanowy" --ref db-package --kind container --parent ingestion --technology SQLAlchemy --position-x 900 --position-y 180
tld connect --from ingestion-cli --to sejm-pipeline --label "uruchamia transformacje" --view ingestion
tld connect --from ingestion-cli --to terc-pipeline --label "buduje słownik historyczny" --view ingestion
tld connect --from ingestion-cli --to unemployment-pipeline --label "uruchamia transformacje" --view ingestion
tld connect --from sejm-pipeline --to regions-import --label "dostarcza regions.csv" --view ingestion
tld connect --from sejm-pipeline --to elections-import --label "dostarcza wyniki gmin" --view ingestion
tld connect --from terc-pipeline --to regions-import --label "dostarcza słownik regionów" --view ingestion
tld connect --from unemployment-pipeline --to socioeconomic-import --label "dostarcza obserwacje" --view ingestion
tld connect --from regions-import --to db-package --label "zapisuje regiony" --view ingestion
tld connect --from elections-import --to db-package --label "zapisuje wybory i wyniki" --view ingestion
tld connect --from socioeconomic-import --to db-package --label "zapisuje P2670" --view ingestion

# Sejm pipeline
tld add "PKW Sejm CSV" --ref raw-elections --kind database --parent sejm-pipeline --description "data/raw/elections/sejm" --position-x 0 --position-y 120
tld add "Raw → interim" --ref sejm-interim-transform --kind component --parent sejm-pipeline --technology Python --description "sejm_interim.py" --position-x 300 --position-y 120
tld add "gmina-totals" --ref interim-totals --kind database --parent sejm-pipeline --position-x 600 --position-y 0
tld add "committee-results" --ref interim-results --kind database --parent sejm-pipeline --position-x 600 --position-y 180
tld add "Historyczny TERC" --ref raw-terc --kind database --parent sejm-pipeline --position-x 600 --position-y 360
tld add "Interim → processed" --ref sejm-processed-transform --kind component --parent sejm-pipeline --technology Python --description "sejm_processed.py mapuje TERC i komitety na bloki." --position-x 900 --position-y 180
tld add "regions.csv" --ref processed-regions --kind database --parent sejm-pipeline --position-x 1200 --position-y 60
tld add "year-sejm-gminy.csv" --ref processed-election-results --kind database --parent sejm-pipeline --position-x 1200 --position-y 300
tld add "Import regionów" --ref regions-import --kind component --parent sejm-pipeline --technology SQLAlchemy --position-x 1500 --position-y 60
tld add "Import wyborów" --ref elections-import --kind component --parent sejm-pipeline --technology SQLAlchemy --position-x 1500 --position-y 300
tld connect --from raw-elections --to sejm-interim-transform --label "normalizuje eksport" --view sejm-pipeline
tld connect --from sejm-interim-transform --to interim-totals --label "zapisuje sumy gmin" --view sejm-pipeline
tld connect --from sejm-interim-transform --to interim-results --label "zapisuje wyniki komitetów" --view sejm-pipeline
tld connect --from interim-totals --to sejm-processed-transform --label "dostarcza sumy" --view sejm-pipeline
tld connect --from interim-results --to sejm-processed-transform --label "dostarcza głosy" --view sejm-pipeline
tld connect --from raw-terc --to sejm-processed-transform --label "mapuje sześciocyfrowy PKW na pełny TERC" --view sejm-pipeline
tld connect --from sejm-processed-transform --to processed-regions --label "tworzy słownik" --view sejm-pipeline
tld connect --from sejm-processed-transform --to processed-election-results --label "tworzy importer-ready fakty" --view sejm-pipeline
tld connect --from processed-regions --to regions-import --label "wejście importu" --view sejm-pipeline
tld connect --from processed-election-results --to elections-import --label "wejście importu" --view sejm-pipeline

# TERC pipeline
tld add "Historyczne snapshoty TERC" --ref raw-terc --kind database --parent terc-pipeline --description "data/raw/teryt/terc" --position-x 0 --position-y 120
tld add "Walidacja snapshotu" --ref terc-loader --kind component --parent terc-pipeline --technology Python --description "terc.py zachowuje siedmiocyfrowe kody i datę snapshotu." --position-x 300 --position-y 120
tld add "Historyczny słownik regionów" --ref historical-regions-transform --kind component --parent terc-pipeline --technology Python --description "terc_regions.py scala roczne snapshoty bez łączenia po nazwie." --position-x 600 --position-y 120
tld add "historyczne regions.csv" --ref historical-regions-file --kind database --parent terc-pipeline --position-x 900 --position-y 120
tld add "Import regionów" --ref regions-import --kind component --parent terc-pipeline --technology SQLAlchemy --position-x 1200 --position-y 120
tld add "core.regions" --ref core-regions --kind database --parent terc-pipeline --technology PostgreSQL --position-x 1500 --position-y 120
tld connect --from raw-terc --to terc-loader --label "czyta dokładny STAN_NA" --view terc-pipeline
tld connect --from terc-loader --to historical-regions-transform --label "zwraca wspierane typy regionów" --view terc-pipeline
tld connect --from historical-regions-transform --to historical-regions-file --label "zapisuje importer-ready CSV" --view terc-pipeline
tld connect --from historical-regions-file --to regions-import --label "wejście importu" --view terc-pipeline
tld connect --from regions-import --to core-regions --label "insert lub zgodny no-op" --view terc-pipeline

# GUS/BDL P2670 pipeline
tld add "Raw BDL P2670" --ref raw-unemployment --kind database --parent unemployment-pipeline --description "Szeroki CSV 2014–2025 w data/raw/features." --position-x 0 --position-y 120
tld add "Raw → interim" --ref unemployment-interim-transform --kind component --parent unemployment-pipeline --technology Python --description "bdl_unemployment.py normalizuje do municipality-year." --position-x 300 --position-y 120
tld add "Interim P2670" --ref interim-unemployment --kind database --parent unemployment-pipeline --position-x 600 --position-y 0
tld add "Historyczny TERC" --ref raw-terc --kind database --parent unemployment-pipeline --position-x 600 --position-y 240
tld add "Interim → processed" --ref unemployment-processed-transform --kind component --parent unemployment-pipeline --technology Python --description "Waliduje każdą obserwację względem snapshotu TERC." --position-x 900 --position-y 120
tld add "Processed P2670" --ref processed-unemployment --kind database --parent unemployment-pipeline --position-x 1200 --position-y 120
tld add "Import P2670" --ref socioeconomic-import --kind component --parent unemployment-pipeline --technology SQLAlchemy --position-x 1500 --position-y 120
tld add "core.regions" --ref core-regions --kind database --parent unemployment-pipeline --technology PostgreSQL --position-x 1800 --position-y 0
tld add "Socioeconomic facts" --ref core-socioeconomic --kind database --parent unemployment-pipeline --technology PostgreSQL --description "data_sources, socioeconomic_variables i socioeconomic_observations." --position-x 1800 --position-y 240
tld connect --from raw-unemployment --to unemployment-interim-transform --label "normalizuje szeroki CSV" --view unemployment-pipeline
tld connect --from unemployment-interim-transform --to interim-unemployment --label "zapisuje long" --view unemployment-pipeline
tld connect --from interim-unemployment --to unemployment-processed-transform --label "dostarcza obserwacje" --view unemployment-pipeline
tld connect --from raw-terc --to unemployment-processed-transform --label "waliduje TERC dla roku" --view unemployment-pipeline
tld connect --from unemployment-processed-transform --to processed-unemployment --label "zapisuje zwalidowane obserwacje" --view unemployment-pipeline
tld connect --from processed-unemployment --to socioeconomic-import --label "wejście importu" --view unemployment-pipeline
tld connect --from core-regions --to socioeconomic-import --label "musi zawierać wszystkie TERC" --view unemployment-pipeline
tld connect --from socioeconomic-import --to core-socioeconomic --label "atomowy insert lub no-op" --view unemployment-pipeline

# Database package and runtime boundaries
tld add "SQLAlchemy Session / Engine" --ref db-session --kind component --parent db-package --technology SQLAlchemy --position-x 0 --position-y 180
tld add "Modele ORM" --ref db-models --kind component --parent db-package --technology SQLAlchemy --position-x 300 --position-y 60
tld add "Migracje Alembic" --ref alembic --kind component --parent db-package --description "Tworzą schematy i obiekty PostgreSQL." --position-x 300 --position-y 300
tld add "Canonical regions batch" --ref canonical-batch --kind component --parent db-package --technology Python --description "electoral-rebuild-canonical-regions" --position-x 600 --position-y 60
tld add "Stability batch" --ref stability-batch --kind component --parent db-package --technology Python --description "electoral-rebuild-stability" --position-x 600 --position-y 300
tld add "PostgreSQL" --ref postgres --kind database --parent db-package --technology PostgreSQL --position-x 900 --position-y 180
tld add "pgAdmin" --ref pgadmin --kind component --parent db-package --position-x 900 --position-y 420
tld connect --from db-session --to postgres --label "zarządza połączeniami i transakcjami" --view db-package
tld connect --from db-models --to db-session --label "mapuje operacje ORM" --view db-package
tld connect --from alembic --to postgres --label "ewoluuje schemat" --view db-package
tld connect --from canonical-batch --to db-session --label "czyta i aktualizuje regiony" --view db-package
tld connect --from stability-batch --to db-session --label "odtwarza snapshot analityczny" --view db-package
tld connect --from pgadmin --to postgres --label "administruje" --view db-package

# PostgreSQL schemas
tld add "Migracje Alembic" --ref alembic --kind component --parent postgres --position-x 0 --position-y 180
tld add "Schemat core" --ref core-schema --kind database --parent postgres --technology PostgreSQL --description "Znormalizowane fakty i słowniki." --position-x 300 --position-y 60
tld add "Schemat analytics" --ref analytics-schema --kind database --parent postgres --technology PostgreSQL --description "Widok agregujący i snapshot stabilności." --position-x 300 --position-y 240
tld add "Schemat ml" --ref ml-schema --kind database --parent postgres --technology PostgreSQL --description "Tabele ML istnieją, ale packages/ml i job treningowy nie są jeszcze zaimplementowane." --position-x 300 --position-y 420
tld add "SQLAlchemy Session / Engine" --ref db-session --kind component --parent postgres --technology SQLAlchemy --position-x 600 --position-y 60
tld add "Canonical regions batch" --ref canonical-batch --kind component --parent postgres --technology Python --position-x 600 --position-y 240
tld add "Stability batch" --ref stability-batch --kind component --parent postgres --technology Python --position-x 600 --position-y 420
tld add "API query services" --ref api-query-services --kind component --parent postgres --technology SQLAlchemy --position-x 900 --position-y 180
tld connect --from alembic --to core-schema --label "tworzy i migruje" --view postgres
tld connect --from alembic --to analytics-schema --label "tworzy widok i tabelę" --view postgres
tld connect --from alembic --to ml-schema --label "tworzy tabele" --view postgres
tld connect --from db-session --to core-schema --label "zapisuje i odczytuje" --view postgres
tld connect --from canonical-batch --to core-schema --label "odtwarza mapowanie canonical" --view postgres
tld connect --from stability-batch --to analytics-schema --label "czyta summary i zapisuje snapshot" --view postgres
tld connect --from api-query-services --to core-schema --label "czyta fakty i słowniki" --view postgres
tld connect --from api-query-services --to analytics-schema --label "czyta timeline i stabilność" --view postgres

# Core schema
tld add "canonical_regions" --ref core-canonical-regions --kind database --parent core-schema --technology PostgreSQL --position-x 0 --position-y 0
tld add "regions" --ref core-regions --kind database --parent core-schema --technology PostgreSQL --position-x 300 --position-y 0
tld add "elections" --ref core-elections --kind database --parent core-schema --technology PostgreSQL --position-x 0 --position-y 240
tld add "political_blocs" --ref core-political-blocs --kind database --parent core-schema --technology PostgreSQL --position-x 300 --position-y 240
tld add "committees" --ref core-committees --kind database --parent core-schema --technology PostgreSQL --position-x 600 --position-y 240
tld add "election_results" --ref core-election-results --kind database --parent core-schema --technology PostgreSQL --position-x 900 --position-y 120
tld add "data_sources" --ref core-data-sources --kind database --parent core-schema --technology PostgreSQL --position-x 600 --position-y 480
tld add "socioeconomic_variables" --ref core-socioeconomic-variables --kind database --parent core-schema --technology PostgreSQL --position-x 300 --position-y 480
tld add "socioeconomic_observations" --ref core-socioeconomic-observations --kind database --parent core-schema --technology PostgreSQL --position-x 900 --position-y 480
tld connect --from core-regions --to core-canonical-regions --label "należy do stabilnej tożsamości" --view core-schema
tld connect --from core-committees --to core-elections --label "należy do wyborów" --view core-schema
tld connect --from core-committees --to core-political-blocs --label "mapuje interpretację bloku" --view core-schema
tld connect --from core-election-results --to core-regions --label "wynik gminy" --view core-schema
tld connect --from core-election-results --to core-elections --label "wynik wyborów" --view core-schema
tld connect --from core-election-results --to core-committees --label "wynik komitetu" --view core-schema
tld connect --from core-election-results --to core-data-sources --label "opcjonalne pochodzenie" --view core-schema
tld connect --from core-socioeconomic-observations --to core-regions --label "obserwacja gminy" --view core-schema
tld connect --from core-socioeconomic-observations --to core-socioeconomic-variables --label "wartość zmiennej" --view core-schema
tld connect --from core-socioeconomic-observations --to core-data-sources --label "pochodzenie pliku" --view core-schema

# Analytics schema
tld add "core election facts" --ref core-election-facts --kind database --parent analytics-schema --technology PostgreSQL --position-x 0 --position-y 120
tld add "region_election_summary" --ref analytics-summary --kind database --parent analytics-schema --technology PostgreSQL --description "Widok agregujący wyniki komitetów do bloków." --position-x 300 --position-y 120
tld add "calculate_region_stability" --ref stability-calculator --kind component --parent analytics-schema --technology Python --description "Czyste, deterministyczne reguły domenowe." --position-x 600 --position-y 0
tld add "electoral-rebuild-stability" --ref stability-batch --kind component --parent analytics-schema --technology Python --position-x 600 --position-y 240
tld add "region_political_stability" --ref analytics-stability --kind database --parent analytics-schema --technology PostgreSQL --description "Atomowo zastępowany snapshot per historyczny region_id." --position-x 900 --position-y 120
tld add "AnalyticsQueries" --ref analytics-queries --kind component --parent analytics-schema --technology SQLAlchemy --position-x 1200 --position-y 0
tld add "RegionQueries timeline" --ref regions-queries --kind component --parent analytics-schema --technology SQLAlchemy --position-x 1200 --position-y 240
tld connect --from core-election-facts --to analytics-summary --label "agreguje wyniki do bloków" --view analytics-schema
tld connect --from analytics-summary --to stability-batch --label "dostarcza chronologiczne wyniki" --view analytics-schema
tld connect --from stability-batch --to stability-calculator --label "liczy metryki per region" --view analytics-schema
tld connect --from stability-batch --to analytics-stability --label "atomowo zastępuje snapshot" --view analytics-schema
tld connect --from analytics-stability --to analytics-queries --label "zasila rankingi" --view analytics-schema
tld connect --from analytics-summary --to regions-queries --label "zasila timeline" --view analytics-schema

# ML schema: implemented storage, no producer yet
tld add "modeling_dataset" --ref ml-modeling-dataset --kind database --parent ml-schema --technology PostgreSQL --description "Odtwarzalny kontrakt zbioru modelowego; brak implementacji buildera." --position-x 300 --position-y 0
tld add "model_runs" --ref ml-model-runs --kind database --parent ml-schema --technology PostgreSQL --description "Metadane treningu; brak implementacji joba treningowego." --position-x 300 --position-y 180
tld add "predictions" --ref ml-predictions --kind database --parent ml-schema --technology PostgreSQL --description "Predykcje modelu; brak implementacji producenta i API." --position-x 600 --position-y 180
tld add "Migracje Alembic" --ref alembic --kind component --parent ml-schema --position-x 0 --position-y 180
tld connect --from alembic --to ml-modeling-dataset --label "tworzy tabelę" --view ml-schema
tld connect --from alembic --to ml-model-runs --label "tworzy tabelę" --view ml-schema
tld connect --from ml-model-runs --to ml-predictions --label "identyfikuje model" --view ml-schema
tld connect --from ml-modeling-dataset --to ml-predictions --label "identyfikuje region i wybory" --view ml-schema

# Development quality view
tld add "Zmiana API / DB / ML" --ref python-change --kind component --parent quality-gates --position-x 0 --position-y 120
tld add '$python-api-tdd' --ref python-api-tdd --kind component --parent quality-gates --description "Plan → RED → GREEN → self-review." --position-x 300 --position-y 120
tld add "pytest" --ref pytest --kind component --parent quality-gates --technology pytest --position-x 600 --position-y 0
tld add "Ruff" --ref ruff --kind component --parent quality-gates --position-x 600 --position-y 120
tld add "mypy" --ref mypy --kind component --parent quality-gates --position-x 600 --position-y 240
tld add "Import Linter" --ref import-linter --kind component --parent quality-gates --position-x 900 --position-y 120
tld connect --from python-change --to python-api-tdd --label "obowiązkowy workflow" --view quality-gates
tld connect --from python-api-tdd --to pytest --label "uruchamia testy" --view quality-gates
tld connect --from python-api-tdd --to ruff --label "sprawdza lint i format" --view quality-gates
tld connect --from python-api-tdd --to mypy --label "sprawdza typy API i DB" --view quality-gates
tld connect --from pytest --to import-linter --label "uzupełnia kontrolę architektury" --view quality-gates

# Correction: make repeated transformation stages distinguishable across pipeline views.
tld remove connector --from raw-unemployment --to unemployment-interim-transform --label "normalizuje szeroki CSV" --view unemployment-pipeline
tld remove connector --from unemployment-interim-transform --to interim-unemployment --label "zapisuje long" --view unemployment-pipeline
tld remove connector --from interim-unemployment --to unemployment-processed-transform --label "dostarcza obserwacje" --view unemployment-pipeline
tld remove connector --from raw-terc --to unemployment-processed-transform --label "waliduje TERC dla roku" --view unemployment-pipeline
tld remove connector --from unemployment-processed-transform --to processed-unemployment --label "zapisuje zwalidowane obserwacje" --view unemployment-pipeline
tld remove element unemployment-interim-transform
tld remove element unemployment-processed-transform
tld add "P2670 raw → interim" --ref unemployment-interim-transform --kind component --parent unemployment-pipeline --technology Python --description "bdl_unemployment.py normalizuje do municipality-year." --position-x 300 --position-y 120
tld add "P2670 interim → processed" --ref unemployment-processed-transform --kind component --parent unemployment-pipeline --technology Python --description "Waliduje każdą obserwację względem snapshotu TERC." --position-x 900 --position-y 120
tld connect --from raw-unemployment --to unemployment-interim-transform --label "normalizuje szeroki CSV" --view unemployment-pipeline
tld connect --from unemployment-interim-transform --to interim-unemployment --label "zapisuje long" --view unemployment-pipeline
tld connect --from interim-unemployment --to unemployment-processed-transform --label "dostarcza obserwacje" --view unemployment-pipeline
tld connect --from raw-terc --to unemployment-processed-transform --label "waliduje TERC dla roku" --view unemployment-pipeline
tld connect --from unemployment-processed-transform --to processed-unemployment --label "zapisuje zwalidowane obserwacje" --view unemployment-pipeline

# Level 1 validates structure and relationships without requiring technology on domain concepts.
tld validate --strictness 1
tld plan --target local --strictness 1
