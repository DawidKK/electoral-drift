# Dokumentacja Flow Aplikacji

## Instrukcja Dla Codexa

Cel tego dokumentu: utrzymywać czytelną, chronologiczną dokumentację przepływu danych i
odpowiedzialności w aplikacji `electoral-drift`.

Przy każdym nowym feature aktualizuj ten plik według zasad:

- Dodaj nowy wpis w sekcji `Logi Flow`.
- Każdy wpis powinien zawierać:
  - krótki opis funkcjonalności,
  - diagram Mermaid pokazujący flow tylko dla tej funkcjonalności,
  - krótki opis diagramu w punktach.
- Dokument pisz po polsku.
- Diagramy Mermaid trzymaj możliwie proste i opisowe.
- Po każdym feature zaktualizuj sekcję `Aktualny Flow Całej Aplikacji` na dole pliku.
- Nie usuwaj starszych logów, chyba że użytkownik wyraźnie o to poprosi.
- Używaj nazw katalogów i funkcji zgodnych z aktualnym kodem.

## Logi Flow

### 2026-07-16 - Regiony: Import CSV I Odczyt Przez API

Dodano pierwszy pełny przepływ dla danych regionów. Regiony można zaimportować z pliku CSV do
tabeli `core.regions`, a następnie pobrać przez endpointy FastAPI.

```mermaid
flowchart LR
    csv["CSV<br/>data/raw/regions.csv"]
    cli["CLI<br/>electoral-import-regions"]
    loader["Ingestion<br/>load_regions_csv()"]
    normalizer["Ingestion<br/>normalize_region_row()"]
    importer["Ingestion<br/>import_regions()"]
    session["DB Session<br/>packages/db"]
    table["PostgreSQL<br/>core.regions"]
    request["HTTP<br/>GET /regions"]
    router["API Router<br/>apps/api/app/routers/regions.py"]
    service["API Service<br/>list_regions()"]
    schema["API Schema<br/>RegionRead"]
    response["JSON<br/>lista regionów"]

    csv --> cli
    cli --> loader
    loader --> normalizer
    normalizer --> importer
    importer --> session
    session --> table

    request --> router
    router --> service
    service --> session
    session --> table
    table --> service
    service --> schema
    schema --> response
```

Opis diagramu:

- Plik CSV jest wejściem dla procesu ingestion.
- Komenda `electoral-import-regions` uruchamia import regionów.
- `load_regions_csv()` czyta plik CSV.
- `normalize_region_row()` waliduje pojedynczy wiersz i pilnuje, aby `teryt_code` został tekstem.
- `import_regions()` zapisuje nowe regiony albo aktualizuje istniejące po `teryt_code`.
- API nie importuje CSV podczas requestu.
- Endpoint `GET /regions` czyta dane już zapisane w `core.regions`.
- `RegionRead` określa publiczny kształt odpowiedzi JSON.

### 2026-07-16 - Wybory: Import Wyników I Odczyt Przez API

Dodano przepływ dla podstawowych danych wyborczych. Jeden plik CSV może utworzyć wybory,
komitety oraz wyniki komitetów w regionach.

```mermaid
flowchart LR
    csv["CSV<br/>data/raw/election_results.csv"]
    cli["CLI<br/>electoral-import-elections"]
    loader["Ingestion<br/>load_election_results_csv()"]
    normalizer["Ingestion<br/>normalize_election_result_row()"]
    importer["Ingestion<br/>import_election_results()"]
    regions["PostgreSQL<br/>core.regions"]
    blocs["PostgreSQL<br/>core.political_blocs"]
    elections["PostgreSQL<br/>core.elections"]
    committees["PostgreSQL<br/>core.committees"]
    results["PostgreSQL<br/>core.election_results"]
    request["HTTP<br/>GET /elections/{id}/results"]
    router["API Router<br/>apps/api/app/routers/elections.py"]
    service["API Service<br/>list_election_results()"]
    schema["API Schema<br/>ElectionResultRead"]
    response["JSON<br/>wyniki wyborów"]

    csv --> cli
    cli --> loader
    loader --> normalizer
    normalizer --> importer
    importer --> regions
    importer --> blocs
    importer --> elections
    importer --> committees
    importer --> results

    request --> router
    router --> service
    service --> results
    results --> service
    service --> schema
    schema --> response
```

Opis diagramu:

- Plik CSV jest wejściem dla importu wyników wyborczych.
- Importer wymaga, aby regiony i bloki polityczne istniały wcześniej w bazie.
- `import_election_results()` tworzy brakujące wybory i komitety.
- Wyniki są zapisywane do `core.election_results`.
- Import jest idempotentny: istniejący wynik jest aktualizowany albo oznaczany jako bez zmian.
- API czyta wyniki z bazy przez `GET /elections/{election_id}/results`.
- `ElectionResultRead` określa publiczny kształt odpowiedzi JSON.

### 2026-07-17 - Timeline Regionu: Gotowy Widok Pod Frontend

Dodano endpoint `GET /regions/{teryt_code}/timeline`. Backend czyta zagregowane dane z
widoku `analytics.region_election_summary` i układa je w małą strukturę gotową pod wykres
historii politycznej jednego regionu.

```mermaid
flowchart LR
    request["HTTP<br/>GET /regions/{teryt_code}/timeline"]
    router["API Router<br/>apps/api/app/routers/regions.py"]
    service["API Service<br/>get_region_timeline()"]
    region_lookup["core.regions<br/>sprawdzenie regionu po TERYT"]
    summary_view["analytics.region_election_summary<br/>wyniki po blokach"]
    grouping["Backend grouping<br/>election -> blocs"]
    schema["API Schema<br/>RegionTimelineRead"]
    response["JSON<br/>timeline regionu"]

    request --> router
    router --> service
    service --> region_lookup
    service --> summary_view
    summary_view --> grouping
    grouping --> schema
    schema --> response
```

Opis diagramu:

- Frontend pyta o historię jednego regionu, a nie o całą bazę wyników.
- Service najpierw sprawdza, czy `teryt_code` istnieje w `core.regions`.
- Dane liczbowe są czytane z `analytics.region_election_summary`, czyli z widoku po blokach.
- Backend układa płaskie rekordy w strukturę `election -> blocs`.
- Odpowiedź jest gotowa do wyświetlenia na wykresie lub w tabeli.
- API zwraca `404`, jeśli region o podanym `teryt_code` nie istnieje.

## Aktualny Flow Całej Aplikacji

Ten diagram pokazuje aktualny przepływ całej aplikacji na wysokim poziomie. Powinien być
aktualizowany po każdym dodanym feature.

```mermaid
flowchart TD
    subgraph sources["Źródła danych"]
        raw_regions["CSV regionów<br/>data/raw/regions.csv"]
        raw_elections["CSV wyników wyborów<br/>data/raw/election_results.csv"]
    end

    subgraph ingestion["packages/ingestion"]
        regions_import["Import regionów<br/>electoral_ingestion/regions.py"]
        elections_import["Import wyborów<br/>electoral_ingestion/elections.py"]
    end

    subgraph db_pkg["packages/db"]
        db_models["Modele SQLAlchemy"]
        db_session["Session / Engine"]
        alembic["Migracje Alembic"]
    end

    subgraph postgres["PostgreSQL"]
        core_regions["core.regions"]
        core_blocs["core.political_blocs"]
        core_elections["core.elections"]
        core_committees["core.committees"]
        core_results["core.election_results"]
    end

    subgraph api["apps/api"]
        api_router["Routery FastAPI"]
        api_service["Serwisy API"]
        api_schema["Schematy Pydantic"]
    end

    subgraph analytics["analytics"]
        region_summary["region_election_summary"]
    end

    client["Klient HTTP<br/>przeglądarka / curl / dashboard"]
    json["Odpowiedź JSON"]

    raw_regions --> regions_import
    raw_elections --> elections_import
    regions_import --> db_session
    elections_import --> db_session
    db_models --> db_session
    alembic --> postgres
    db_session --> core_regions
    db_session --> core_blocs
    db_session --> core_elections
    db_session --> core_committees
    db_session --> core_results

    client --> api_router
    api_router --> api_service
    api_service --> db_session
    db_session --> core_regions
    db_session --> core_elections
    db_session --> core_results
    core_results --> region_summary
    core_regions --> api_service
    core_elections --> api_service
    core_results --> api_service
    region_summary --> api_service
    api_service --> api_schema
    api_schema --> json
```

Najważniejsze zasady aktualnego flow:

- Ingestion zapisuje dane do bazy.
- API czyta dane z bazy i zwraca JSON.
- `packages/db` jest wspólną warstwą dla ingestion i API.
- Migracje Alembic definiują strukturę PostgreSQL.
- Wyniki wyborów zależą od wcześniej zaimportowanych regionów i seedowanych bloków politycznych.
- Endpoint timeline czyta zagregowane wyniki po blokach, zamiast wysyłać cały zbiór danych.
- Frontend/dashboard nie jest jeszcze zaimplementowany.
