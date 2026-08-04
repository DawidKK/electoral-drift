# Dokumentacja Flow Aplikacji

## Instrukcja Dla Codexa

Cel tego dokumentu: utrzymywać czytelną, chronologiczną dokumentację przepływu danych i
odpowiedzialności w aplikacji `electoral-drift`.

Przy każdym nowym feature aktualizuj ten plik według zasad:

- Dodaj nowy wpis na początku sekcji `Logi Flow`.
- Każdy wpis powinien zawierać:
  - krótki opis funkcjonalności,
  - diagram Mermaid pokazujący flow tylko dla tej funkcjonalności,
  - krótki opis diagramu w punktach.
- Dokument pisz po polsku.
- Diagramy Mermaid trzymaj możliwie proste i opisowe.
- Sortuj wpisy w `Logi Flow` malejąco według daty z nagłówka: najnowsze na górze,
  najstarsze na dole.
- Po każdym feature zaktualizuj sekcję `Aktualny Flow Całej Aplikacji`, umieszczoną między
  tą instrukcją a sekcją `Logi Flow`.
- Nie usuwaj starszych logów, chyba że użytkownik wyraźnie o to poprosi.
- Używaj nazw katalogów i funkcji zgodnych z aktualnym kodem.

## Aktualny Flow Całej Aplikacji

Ten diagram pokazuje aktualny przepływ całej aplikacji na wysokim poziomie. Powinien być
aktualizowany po każdym dodanym feature.

```mermaid
flowchart TD
    subgraph sources["Źródła danych"]
        raw_elections["PKW Sejm CSV<br/>data/raw/elections/sejm"]
        raw_terc["Historyczne TERC<br/>data/raw/teryt/terc"]
        interim_totals["Interim<br/>gmina-totals"]
        interim_results["Interim<br/>committee-results"]
        processed_regions["Processed<br/>regions.csv"]
        processed_results["Processed<br/>year-sejm-gminy.csv"]
    end

    subgraph ingestion["packages/ingestion"]
        regions_import["Import regionów<br/>electoral_ingestion/regions.py"]
        sejm_transform["Transformacja raw -> interim<br/>sejm_interim.py"]
        processed_transform["Transformacja interim -> processed<br/>sejm_processed.py"]
        elections_import["Import wyborów<br/>electoral_ingestion/elections.py"]
    end

    subgraph db_pkg["packages/db"]
        db_models["Modele SQLAlchemy"]
        db_session["Session / Engine"]
        alembic["Migracje Alembic"]
        canonical_batch["Canonical regions batch<br/>electoral-rebuild-canonical-regions"]
    end

    subgraph postgres["PostgreSQL"]
        core_canonical_regions["core.canonical_regions"]
        core_regions["core.regions"]
        core_blocs["core.political_blocs"]
        core_elections["core.elections"]
        core_committees["core.committees"]
        core_results["core.election_results"]
    end

    subgraph api["apps/api"]
        api_main["Composition root<br/>app/main.py"]

        subgraph health_feature["features/health"]
            health_router["router.py<br/>GET /health"]
        end

        subgraph regions_feature["features/regions"]
            regions_router["router.py<br/>endpointy /regions"]
            regions_dependencies["dependencies.py<br/>RegionQueries + Session"]
            regions_queries["queries.py<br/>zapytania regionów i timeline"]
            regions_schemas["schemas.py<br/>RegionRead / Timeline DTO"]
        end

        subgraph elections_feature["features/elections"]
            elections_router["router.py<br/>endpointy /elections"]
            elections_dependencies["dependencies.py<br/>ElectionQueries + Session"]
            elections_queries["queries.py<br/>katalog i wyniki wyborów"]
            elections_schemas["schemas.py<br/>ElectionRead / Result DTO"]
        end

        subgraph analytics_feature["features/analytics"]
            analytics_router["router.py<br/>endpointy /analytics"]
            analytics_dependencies["dependencies.py<br/>AnalyticsQueries + Session"]
            analytics_queries["queries.py<br/>ranking i zmienne politycznie gminy"]
            analytics_schemas["schemas.py<br/>RegionStabilityRead DTO"]
        end

        api_infrastructure["infrastructure/database.py<br/>request-scoped DB Session"]
    end

    subgraph analytics["analytics"]
        region_summary["region_election_summary"]
        stability_batch["Batch<br/>calculate_region_stability()"]
        region_stability["region_political_stability"]
    end

    subgraph quality["Python development quality"]
        developer["Zmiana API / DB / ML"]
        tdd_skill["$python-api-tdd<br/>Plan -> RED -> GREEN -> review"]
        quality_gates["pytest + Ruff + mypy<br/>Import Linter"]
    end

    client["Klient HTTP<br/>przeglądarka / curl / dashboard"]
    json["Odpowiedź JSON"]

    developer --> tdd_skill
    tdd_skill --> quality_gates
    quality_gates -. "weryfikuje" .-> api
    quality_gates -. "weryfikuje" .-> db_pkg

    raw_elections --> sejm_transform
    sejm_transform --> interim_totals
    sejm_transform --> interim_results
    interim_totals --> processed_transform
    interim_results --> processed_transform
    raw_terc --> processed_transform
    processed_transform --> processed_regions
    processed_transform --> processed_results
    processed_regions --> regions_import
    processed_results --> elections_import
    regions_import --> db_session
    elections_import --> db_session
    db_models --> db_session
    alembic --> postgres
    core_regions --> canonical_batch
    core_elections --> canonical_batch
    core_results --> canonical_batch
    canonical_batch --> core_canonical_regions
    canonical_batch --> core_regions
    db_session --> core_regions
    db_session --> core_blocs
    db_session --> core_elections
    db_session --> core_committees
    db_session --> core_results

    client --> api_main
    api_main --> health_router
    api_main --> regions_router
    api_main --> elections_router
    api_main --> analytics_router

    health_router --> json

    regions_router --> regions_dependencies
    regions_dependencies --> regions_queries
    regions_dependencies --> api_infrastructure
    regions_queries --> regions_schemas
    regions_schemas --> regions_router
    regions_router --> json

    elections_router --> elections_dependencies
    elections_dependencies --> elections_queries
    elections_dependencies --> api_infrastructure
    elections_queries --> elections_schemas
    elections_schemas --> elections_router
    elections_router --> json

    analytics_router --> analytics_dependencies
    analytics_dependencies --> analytics_queries
    analytics_dependencies --> api_infrastructure
    analytics_queries --> analytics_schemas
    analytics_schemas --> analytics_router
    analytics_router --> json

    api_infrastructure --> db_session
    db_session --> core_regions
    db_session --> core_elections
    db_session --> core_results
    core_results --> region_summary
    region_summary --> stability_batch
    stability_batch --> region_stability
    core_regions --> regions_queries
    core_canonical_regions --> regions_queries
    core_elections --> regions_queries
    core_results --> regions_queries
    region_summary --> regions_queries

    core_regions --> elections_queries
    core_elections --> elections_queries
    core_committees --> elections_queries
    core_results --> elections_queries

    core_regions --> analytics_queries
    region_stability --> analytics_queries
```

Najważniejsze zasady aktualnego flow:

- Ingestion zapisuje dane do bazy.
- API czyta dane z bazy i zwraca JSON.
- API jest podzielone na niezależne feature’y, które posiadają własne routery, schematy i zapytania.
- Diagram pokazuje osobno przepływ `health`, `regions`, `elections` i `analytics`; tylko trzy ostatnie
  korzystają z sesji bazodanowej.
- Modele SQLAlchemy nie opuszczają `queries.py`, a routery nie zależą od implementacji persystencji.
- `packages/db` jest wspólną warstwą dla ingestion i API.
- Migracje Alembic definiują strukturę PostgreSQL.
- Wyniki wyborów zależą od wcześniej zaimportowanych regionów i seedowanych bloków politycznych.
- Komenda `electoral-rebuild-canonical-regions` grupuje historyczne wersje TERYT po pierwszych
  sześciu cyfrach i przypisuje im wspólny `canonical_region_id`.
- Pełne siedmiocyfrowe kody pozostają w `core.regions`; canonical region jest dodatkową warstwą
  tożsamości analitycznej, a nie zamiennikiem faktu historycznego.
- API regionów zwraca `canonical_region_id`, ale timeline i snapshot stabilności nadal są liczone
  dla historycznego `region_id`.
- Endpoint timeline czyta zagregowane wyniki po blokach, zamiast wysyłać cały zbiór danych.
- Komenda `electoral-rebuild-stability` atomowo zastępuje snapshot analityczny.
- Endpointy stabilności czytają gotowy snapshot i nie uruchamiają obliczeń w requestach HTTP.
- Zmiany Python w API i DB przechodzą przez zaakceptowany plan, TDD, self-review oraz
  automatyczne bramki jakości i architektury.
- Import Linter wymusza kierunek zależności, a REP, CCP i CRP są sprawdzane semantycznie
  podczas planowania i self-review.
- Frontend/dashboard nie jest jeszcze zaimplementowany.

## Logi Flow

### 2026-08-04 - Canonical Regions: Wspólna Tożsamość Historycznych Kodów TERYT

Dodano odtwarzalne mapowanie historycznych, siedmiocyfrowych wersji TERYT na wspólną jednostkę
analityczną. Źródłowe regiony i wyniki pozostają niezmienione, a API udostępnia identyfikator
canonical region obok historycznego kodu.

```mermaid
flowchart LR
    historical["core.regions<br/>pełne TERYT 7 cyfr"]
    elections["core.election_results<br/>+ core.elections"]
    command["CLI batch<br/>electoral-rebuild-canonical-regions"]
    grouping["Grupowanie<br/>pierwsze 6 cyfr TERYT"]
    canonical["core.canonical_regions<br/>stabilna tożsamość"]
    mapping["core.regions.canonical_region_id"]
    api["GET /regions...<br/>RegionRead"]

    historical --> command
    elections --> command
    command --> grouping
    grouping --> canonical
    canonical --> mapping
    mapping --> historical
    historical --> api
```

Opis diagramu:

- `core.canonical_regions.base_teryt_code` przechowuje pierwsze sześć cyfr kodu TERYT.
- Wersje takie jak `0603112` i `0603113` zachowują osobne rekordy, ale wskazują ten sam
  `canonical_region_id`.
- Nazwa canonical region pochodzi z wersji występującej w najnowszych zaimportowanych wyborach;
  remis roku rozstrzyga deterministycznie większy `region_id`.
- Batch ładuje regiony i istniejące mapowania zbiorczo, działa w jednej transakcji i jest
  idempotentny.
- Po każdym przyszłym imporcie regionów lub wyborów należy ponownie uruchomić komendę batch.
- Pierwsza wersja crosswalku obsługuje zmianę ostatniej cyfry TERYT. Zmiany pierwszych sześciu
  cyfr, podziały, połączenia i zmiany granic wymagają osobno zweryfikowanego mapowania.
- Timeline i stabilność polityczna nie agregują jeszcze wyników po `canonical_region_id`; ta
  decyzja pozostaje osobnym etapem analitycznym.

### 2026-07-28 - TERC: Historyczna Tożsamość Gmin I Filtr Regionów Specjalnych

Pipeline wykorzystuje teraz snapshot TERC właściwy dla roku wyborów. Rekordy zagraniczne i statki
są usuwane przed interim, a każda prawdziwa gmina musi otrzymać pełny siedmiocyfrowy identyfikator
TERC przed zapisaniem processed.

```mermaid
flowchart LR
    pkw["Raw PKW<br/>kod 6-cyfrowy"]
    filter["Filtr<br/>zagranica i statki"]
    interim["Interim<br/>prawdziwe jednostki"]
    terc["TERC dla roku<br/>WOJ + POW + GMI + RODZ"]
    match["Ścisłe dopasowanie<br/>kod PKW -> TERC"]
    processed["Processed<br/>pełny kod 7-cyfrowy"]

    pkw --> filter
    filter --> interim
    interim --> match
    terc --> match
    match --> processed
```

Opis diagramu:

- Sztuczne kody PKW dla zagranicy i statków nie są traktowane jako gminy.
- Każdy rok wyborczy korzysta z odpowiadającego mu snapshotu TERC.
- Do mapowania dopuszczane są całe gminy, dzielnice Warszawy i historyczne delegatury.
- Brak lub wieloznaczne dopasowanie zatrzymuje batch.
- Nazwa, typ jednostki i województwo pochodzą z oficjalnego słownika.

### 2026-07-28 - Sejm: Transformacja Interim Do Processed

Dodano batch budujący z plików interim wyniki gotowe dla importera bazy oraz wspólny słownik
gmin. Proces jawnie mapuje źródłowe nazwy komitetów na czytelne nazwy i bloki polityczne,
oblicza udziały głosów i frekwencję oraz sprawdza sumy kontrolne.

```mermaid
flowchart LR
    totals["Interim<br/>gmina-totals"]
    committees["Interim<br/>committee-results"]
    terc["Historyczny TERC<br/>dla roku wyborów"]
    transform["CLI<br/>electoral-transform-sejm-processed"]
    mapping["Jawne mapowanie<br/>committee -> bloc"]
    validation["Walidacja<br/>sumy, klucze, procenty"]
    regions["Processed<br/>regions.csv"]
    results["Processed<br/>year-sejm-gminy.csv"]
    region_import["CLI<br/>electoral-import-regions"]
    election_import["CLI<br/>electoral-import-elections"]

    totals --> transform
    committees --> transform
    terc --> transform
    transform --> mapping
    mapping --> validation
    validation --> regions
    validation --> results
    regions --> region_import
    results --> election_import
```

Opis diagramu:

- Batch przetwarza wszystkie pary plików interim dostępne w katalogu.
- Nieznana nazwa komitetu zatrzymuje proces zamiast trafiać automatycznie do `other`.
- Głosy komitetów muszą sumować się do liczby ważnych głosów w każdej gminie.
- Processed używa pełnego siedmiocyfrowego kodu ze snapshotu TERC właściwego dla wyborów.
- `regions.csv` należy zaimportować przed wynikami poszczególnych wyborów.

### 2026-07-28 - Sejm: Transformacja Raw Do Interim

Dodano powtarzalną transformację plików PKW z wyborów do Sejmu w latach 2015, 2019 i 2023.
Źródłowy szeroki rekord gminy jest rozdzielany na rekord sumaryczny gminy oraz długie rekordy
wyników komitetów. Transformacja nie wykonuje jeszcze mapowania do kanonicznego TERYT ani bloków
politycznych.

```mermaid
flowchart LR
    raw["PKW CSV<br/>data/raw/elections/sejm"]
    command["CLI<br/>electoral-transform-sejm-interim"]
    parser["sejm_interim.py<br/>format właściwy dla roku"]
    validation["Normalizacja<br/>liczby, TERYT, rekordy zagraniczne"]
    totals["Interim CSV<br/>gmina-totals"]
    committees["Interim CSV<br/>committee-results"]

    raw --> command
    command --> parser
    parser --> validation
    validation --> totals
    validation --> committees
```

Opis diagramu:

- Komenda rozpoznaje rok na podstawie nazwy pliku i stosuje właściwy schemat PKW.
- Kody źródłowe gmin są zapisywane jako sześciocyfrowy tekst.
- Rekordy zagraniczne bez TERYT są pomijane i raportowane.
- Wartości wspólne dla gminy nie są duplikowane w każdym rekordzie komitetu.
- Nazwy komitetów pozostają źródłowe; normalizacja domenowa nastąpi w warstwie processed.

### 2026-07-27 - API: Lekkie Moduły Feature’owe

API przeorganizowano z przekrojowych katalogów technicznych na niezależne moduły `health`,
`regions`, `elections` i `analytics`. Każdy feature posiada własny router, kontrakty odpowiedzi,
zapytania oraz składanie zależności.

```mermaid
flowchart LR
    main["Composition root<br/>app/main.py"]
    router["Feature router<br/>HTTP"]
    dependency["Feature dependency<br/>składanie query"]
    query["Feature queries<br/>SQLAlchemy i mapowanie DTO"]
    infrastructure["Infrastructure<br/>request-scoped Session"]
    database["electoral_db<br/>modele i sesja"]
    response["Feature schema<br/>JSON"]
    contracts["Import Linter<br/>granice modułów"]

    main --> router
    router --> dependency
    dependency --> query
    dependency --> infrastructure
    infrastructure --> database
    query --> database
    query --> response
    response --> router
    contracts -. "weryfikuje" .-> router
    contracts -. "weryfikuje" .-> infrastructure
```

Opis diagramu:

- `main.py` rejestruje routery, ale nie zawiera logiki feature’ów ani zapytań.
- Router zna lokalny query service i schematy, lecz nie importuje SQLAlchemy ani `electoral_db`.
- `queries.py` jest granicą persystencji: wykonuje zapytania i zwraca feature’owe DTO.
- `dependencies.py` łączy query service z sesją tworzoną w `infrastructure/database.py`.
- Feature’y nie importują się wzajemnie; regionowe wybory są projekcją należącą do `regions`.
- Testy endpointów podmieniają query service zamiast imitować wewnętrzne API SQLAlchemy.
- Import Linter pilnuje niezależności feature’ów i kierunku zależności infrastruktury.

### 2026-07-25 - Stabilność Polityczna Regionów

Dodano powtarzalny proces batch, który przelicza zwycięstwa znormalizowanych bloków
politycznych na podstawie danych PKW. API odczytuje gotowy snapshot stabilności i nie wykonuje
obliczeń analitycznych podczas requestu.

```mermaid
flowchart LR
    results["Wyniki PKW<br/>core.election_results"]
    summary["Widok bloków<br/>analytics.region_election_summary"]
    command["CLI batch<br/>electoral-rebuild-stability"]
    calculator["Reguły domenowe<br/>calculate_region_stability()"]
    stability["Snapshot<br/>analytics.region_political_stability"]
    ranking["GET<br/>/analytics/stability-ranking"]
    swing["GET<br/>/analytics/swing-counties"]
    response["JSON<br/>metryki regionów"]

    results --> summary
    summary --> command
    command --> calculator
    calculator --> stability
    stability --> ranking
    stability --> swing
    ranking --> response
    swing --> response
```

Opis diagramu:

- Wyniki komitetów są najpierw agregowane do stabilnych bloków politycznych.
- Komenda batch porządkuje wybory chronologicznie i rozstrzyga zwycięzcę w każdym regionie.
- Remis nie jest liczony jako zwycięstwo żadnego bloku.
- Snapshot zawiera liczby zwycięstw, zmiany zwycięzcy, marginesy, trend, zmienność i etykietę.
- Jedna zmiana zwycięzcy oznacza `emerging_shift`, a co najmniej dwie oznaczają `swing`.
- Endpoint `swing-counties` zachowuje dotychczasową nazwę kontraktu, ale zwraca gminy oznaczone
  jako `swing` lub `emerging_shift`.

### 2026-07-25 - Python: TDD I Bramka Jakości Architektury

Dodano repozytoryjny skill `$python-api-tdd` dla API, warstwy DB i przyszłego pakietu ML.
Skill wymaga zaakceptowanego planu, potwierdzonego testu RED, minimalnej implementacji GREEN,
refaktoryzacji, przeglądu REP/CCP/CRP oraz kompletnej bramki jakości.

```mermaid
flowchart LR
    task["Zmiana Python<br/>API / DB / ML"]
    plan["Plan<br/>zależności i testy"]
    approval["Akceptacja<br/>użytkownika"]
    red["RED<br/>oczekiwany błąd testu"]
    green["GREEN<br/>minimalna implementacja"]
    review["Refactor i self-review<br/>REP / CCP / CRP / komentarze"]
    tests["pytest"]
    ruff["Ruff<br/>lint i format-check"]
    types["mypy"]
    imports["Import Linter"]
    done["Gotowa zmiana<br/>raport wyników"]

    task --> plan
    plan --> approval
    approval --> red
    red --> green
    green --> review
    review --> tests
    tests --> ruff
    ruff --> types
    types --> imports
    imports --> done
```

Opis diagramu:

- Implementacja nie rozpoczyna się przed jawną akceptacją planu.
- RED musi potwierdzić brak oczekiwanego zachowania, a nie błąd konfiguracji testu.
- GREEN zawiera najmniejszą poprawną implementację, po której następuje refaktoryzacja.
- Self-review sprawdza prostotę, komentarze oraz semantyczną zgodność z REP, CCP i CRP.
- `pytest`, Ruff, mypy i Import Linter są obowiązkowymi bramkami końcowymi.
- Import Linter pilnuje kierunku zależności między API i DB; REP, CCP i CRP wymagają także
  przeglądu semantycznego.
- Po wdrożeniu skilla 19 testów przeszło, 1 test integracyjny został pominięty, a linting,
  formatowanie, typowanie i oba kontrakty importów zakończyły się sukcesem.
- Kontrola negatywna potwierdziła, że Import Linter wykrywa zabronioną zależność.

### 2026-07-17 - Timeline Regionu: Gotowy Widok Pod Frontend

Dodano endpoint `GET /regions/{teryt_code}/timeline`. Backend czyta zagregowane dane z
widoku `analytics.region_election_summary` i układa je w małą strukturę gotową pod wykres
historii politycznej jednego regionu.

```mermaid
flowchart LR
    request["HTTP<br/>GET /regions/{teryt_code}/timeline"]
    router["Region Feature Router<br/>features/regions/router.py"]
    service["RegionQueries<br/>get_timeline()"]
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
    router["Election Feature Router<br/>features/elections/router.py"]
    service["ElectionQueries<br/>list_results()"]
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
    router["Region Feature Router<br/>features/regions/router.py"]
    service["RegionQueries<br/>list_regions()"]
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
