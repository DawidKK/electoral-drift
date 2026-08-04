# Mapowanie TERYT i TERC

Ten dokument wyjaśnia, w jaki sposób projekt przypisuje wyniki wyborów PKW do polskich gmin.
Jest przeznaczony dla osoby, która nie zna rejestru TERYT ani geografii wyborczej.

## Po co potrzebujemy mapowania?

Pliki Państwowej Komisji Wyborczej zawierają wyniki głosowania, ale nie są kompletnym
słownikiem jednostek administracyjnych. PKW podaje między innymi:

- skrócony kod gminy,
- nazwę gminy,
- liczbę uprawnionych,
- liczbę ważnych głosów,
- głosy oddane na poszczególne komitety.

Do analizy potrzebujemy pewności, że kod oznacza prawdziwą gminę oraz jaki jest jej rodzaj.
Potrzebujemy również stabilnego sposobu łączenia wyborów z danymi GUS i BDL. Dlatego wyniki PKW
są sprawdzane za pomocą oficjalnego rejestru TERYT.

## TERYT i TERC — co oznaczają te nazwy?

**TERYT** to Krajowy Rejestr Urzędowy Podziału Terytorialnego Kraju prowadzony przez Główny
Urząd Statystyczny.

TERYT składa się z kilku systemów. W tym projekcie używamy systemu **TERC**, czyli wykazu
identyfikatorów i nazw jednostek podziału terytorialnego:

- województw,
- powiatów,
- gmin,
- dzielnic Warszawy,
- historycznych delegatur niektórych miast.

Nie potrzebujemy obecnie:

- `SIMC`, czyli katalogu miejscowości, wsi i części miejscowości;
- `ULIC`, czyli katalogu ulic;
- wersji adresowej TERYT.

Analizujemy całe gminy, a nie adresy lub pojedyncze miejscowości.

Oficjalny opis systemu znajduje się na stronie
[GUS — charakterystyka TERC](https://eteryt.stat.gov.pl/eTeryt/rejestr_teryt/ogolna_charakterystyka_systemow_rejestru/ogolna_charakterystyka_systemow_rejestru.aspx?contrast=default).

## Jak zbudowany jest kod?

### Sześciocyfrowy kod PKW

Wyniki PKW posługują się kodem złożonym z sześciu cyfr:

```text
02 01 01
│  │  └── numer gminy
│  └───── numer powiatu
└──────── numer województwa
```

Przykład:

```text
020101
```

Kod wskazuje obszar gminy, ale nie zawiera informacji o jej rodzaju.

### Siedmiocyfrowy kod TERC

Pełny identyfikator TERC ma dodatkową, siódmą cyfrę:

```text
02 01 01 1
│  │  │  └── rodzaj jednostki
│  │  └───── numer gminy
│  └──────── numer powiatu
└─────────── numer województwa
```

Przykład:

```text
0201011
```

Ostatnia cyfra ma następujące znaczenie:

| Kod | Rodzaj jednostki | Wartość w projekcie |
|---:|---|---|
| `1` | gmina miejska | `urban_municipality` |
| `2` | gmina wiejska | `rural_municipality` |
| `3` | gmina miejsko-wiejska jako całość | `urban_rural_municipality` |
| `4` | miasto w gminie miejsko-wiejskiej | nie jest używane |
| `5` | obszar wiejski gminy miejsko-wiejskiej | nie jest używane |
| `8` | dzielnica miasta stołecznego Warszawy | `warsaw_district` |
| `9` | delegatura miasta | `city_delegation` |

PKW podaje wynik dla całej gminy miejsko-wiejskiej. Dlatego pipeline wybiera rekord typu `3`,
a nie osobne rekordy typu `4` i `5`. Rozdzielenie wyniku między miasto i obszar wiejski
zmieniłoby znaczenie danych źródłowych.

## Przykład mapowania

W pliku PKW dla Bolesławca znajduje się:

```text
kod PKW: 020101
nazwa PKW: m. Bolesławiec
```

W historycznym TERC znajdujemy:

```text
WOJ=02
POW=01
GMI=01
RODZ=1
NAZWA=Bolesławiec
NAZWA_DOD=gmina miejska
```

Pipeline buduje:

```text
020101 + 1 = 0201011
```

Do processed trafia więc oficjalna nazwa i rodzaj:

```csv
teryt_code,name,region_type,voivodeship
0201011,Bolesławiec,urban_municipality,dolnośląskie
```

## Dlaczego używamy historycznych plików TERC?

Podział administracyjny Polski zmienia się. Gmina może:

- zmienić rodzaj, na przykład z wiejskiej na miejsko-wiejską;
- zmienić nazwę;
- zostać utworzona albo zlikwidowana;
- zmienić przynależność administracyjną.

Aktualny słownik nie zawsze zawiera jednostkę istniejącą podczas dawnych wyborów. Nie powinno się
więc opisywać wyborów z 2015 roku za pomocą samego słownika z 2026 roku.

Projekt używa osobnych snapshotów:

```text
data/raw/teryt/terc/
├── 2015-01-01.csv
├── 2019-01-01.csv
└── 2023-01-01.csv
```

Mapowanie wygląda następująco:

```text
wyniki Sejmu 2015 → TERC 2015-01-01
wyniki Sejmu 2019 → TERC 2019-01-01
wyniki Sejmu 2023 → TERC 2023-01-01
```

Dzięki temu nazwa, rodzaj gminy i pełny kod odpowiadają podziałowi administracyjnemu właściwemu
dla danego okresu.

## Co dzieje się, gdy rodzaj gminy się zmienia?

Zmiana ostatniej cyfry oznacza zmianę pełnego identyfikatora TERC. Przykładowo ta sama jednostka
terytorialna może w różnych latach występować jako:

```text
1234562 → gmina wiejska
1234563 → gmina miejsko-wiejska
```

W warstwie źródłowej są to dwa historyczne identyfikatory. Pipeline ich automatycznie nie scala,
ponieważ takie scalenie jest decyzją analityczną, a nie faktem pochodzącym z PKW lub GUS.

Projekt przechowuje obecnie podstawowy **crosswalk historyczny**, który opisuje:

```text
historyczny kod TERC → `core.canonical_regions`
```

Komenda `electoral-rebuild-canonical-regions` łączy wersje o tych samych pierwszych sześciu
cyfrach i zachowuje pełne kody źródłowe. Nie scala automatycznie zmian pierwszych sześciu cyfr,
podziałów, połączeń ani zmian granic; wymagają one osobno zweryfikowanego mapowania.

## Jakie rekordy są usuwane?

Pipeline usuwa wyłącznie rekordy, które nie opisują polskiej gminy ani innej obsługiwanej
jednostki terytorialnej.

### Głosowanie za granicą

Głosy zagraniczne są prawdziwymi wynikami wyborów, ale nie można przypisać ich do polskiej gminy.
W zależności od roku PKW zapisywała je:

- bez kodu TERYT;
- pod technicznym kodem `149901`.

Rekord `zagranica` nie występuje w TERC, ponieważ nie jest jednostką administracyjną Polski.

### Głosowanie na statkach

Głosowanie na polskich statkach również jest prawdziwą częścią ogólnopolskiego wyniku, ale nie
opisuje mieszkańców konkretnej gminy. PKW używała między innymi kodów:

```text
149801 → statki
229801 → Statki Gdynia
229901 → Statki Gdańsk
```

Kody te są identyfikatorami technicznymi PKW, a nie kodami gmin w TERC.

### Dlaczego je usuwamy?

Projekt odpowiada na pytania o zmianę preferencji politycznych w polskich gminach. Przypisanie
zagranicy lub statków do fikcyjnej gminy:

- tworzyłoby nieistniejące regiony;
- zniekształcałoby rankingi stabilności;
- uniemożliwiałoby połączenie z danymi społeczno-ekonomicznymi GUS;
- powodowałoby błędy na mapach;
- zaburzałoby zbiór ML.

Rekordy nie są usuwane z plików `data/raw`. Oryginalne dane PKW pozostają niezmienione.
Są pomijane wyłącznie podczas tworzenia warstwy interim przeznaczonej do analiz gminnych.

## Ile rekordów zostało pominiętych?

W aktualnych plikach źródłowych:

| Wybory | Rekordy bez TERYT | Zagranica lub statki ze sztucznym kodem |
|---:|---:|---:|
| 2015 | 0 | 3 |
| 2019 | 0 | 2 |
| 2023 | 91 | 0 |

W 2023 roku PKW przechowuje osobny rekord dla każdego państwa lub obszaru głosowania
zagranicznego. Wszystkie mają pusty kod gminy.

## Jak działa pipeline?

```text
oryginalny CSV PKW
        │
        ▼
raw → zachowanie danych bez zmian
        │
        ▼
filtr zagranicy, statków i rekordów bez kodu gminy
        │
        ▼
interim → sześciocyfrowy kod źródłowy PKW
        │
        ├──────── historyczny TERC właściwy dla roku
        │
        ▼
ścisłe mapowanie kodu PKW do jednego rekordu TERC
        │
        ▼
processed → pełny kod, oficjalna nazwa i rodzaj jednostki
        │
        ▼
import do core.regions i core.election_results
```

Transformacja zatrzymuje się, gdy:

- brakuje pliku TERC dla danego roku;
- kod PKW nie występuje w odpowiednim TERC;
- kod pasuje do więcej niż jednej całej jednostki;
- data snapshotu nie odpowiada rokowi wyborów;
- głosy komitetów nie sumują się do liczby ważnych głosów.

Takie podejście zapobiega cichym, trudnym do wykrycia błędom geograficznym.

## Gdzie znajdują się reguły?

- `electoral_ingestion/sejm_interim.py` — filtruje rekordy spoza analizowanej geografii
  i zachowuje sześciocyfrowy kod PKW;
- `electoral_ingestion/sejm_processed.py` — wczytuje historyczny TERC, wykonuje ścisłe mapowanie
  i buduje pliki gotowe do importu;
- `data/raw/teryt/terc` — niezmienione snapshoty TERC;
- `data/interim/elections/sejm` — oczyszczone dane źródłowe;
- `data/processed/elections/sejm` — dane z pełnymi kodami gotowe do bazy.

## Najważniejsze zasady

1. Kod TERYT jest zawsze tekstem, nigdy liczbą — dzięki temu nie tracimy zer wiodących.
2. Nie dopisujemy siódmej cyfry na podstawie nazwy lub zgadywania.
3. Każde wybory korzystają ze słownika TERC właściwego dla swojego roku.
4. Raw pozostaje niezmienione; filtrowanie odbywa się dopiero w interim.
5. Zagranica i statki nie są błędnymi głosami — są poza zakresem analizy gminnej.
6. Historyczne kody łączymy analitycznie tylko przez jawny, odtwarzalny crosswalk.
