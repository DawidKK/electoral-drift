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

## Aktualny Flow Całej Aplikacji

Ten diagram pokazuje aktualny przepływ całej aplikacji na wysokim poziomie. Powinien być
aktualizowany po każdym dodanym feature.

```mermaid
flowchart TD
    subgraph sources["Źródła danych"]
        raw_regions["CSV regionów<br/>data/raw/regions.csv"]
    end

    subgraph ingestion["packages/ingestion"]
        regions_import["Import regionów<br/>electoral_ingestion/regions.py"]
    end

    subgraph db_pkg["packages/db"]
        db_models["Modele SQLAlchemy"]
        db_session["Session / Engine"]
        alembic["Migracje Alembic"]
    end

    subgraph postgres["PostgreSQL"]
        core_regions["core.regions"]
    end

    subgraph api["apps/api"]
        api_router["Routery FastAPI"]
        api_service["Serwisy API"]
        api_schema["Schematy Pydantic"]
    end

    client["Klient HTTP<br/>przeglądarka / curl / dashboard"]
    json["Odpowiedź JSON"]

    raw_regions --> regions_import
    regions_import --> db_session
    db_models --> db_session
    alembic --> postgres
    db_session --> core_regions

    client --> api_router
    api_router --> api_service
    api_service --> db_session
    db_session --> core_regions
    core_regions --> api_service
    api_service --> api_schema
    api_schema --> json
```

Najważniejsze zasady aktualnego flow:

- Ingestion zapisuje dane do bazy.
- API czyta dane z bazy i zwraca JSON.
- `packages/db` jest wspólną warstwą dla ingestion i API.
- Migracje Alembic definiują strukturę PostgreSQL.
- Frontend/dashboard nie jest jeszcze zaimplementowany.
