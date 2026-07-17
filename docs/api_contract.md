# API Contract

This document tracks the public API surface as it is introduced.

## Health

`GET /health`

Response:

```json
{
  "status": "ok"
}
```

## Regions

`GET /regions`

Returns counties or other territorial units from `core.regions`, ordered by TERYT code.

Response item:

```json
{
  "id": 1,
  "teryt_code": "0264011",
  "name": "Wroclaw",
  "region_type": "city_county",
  "voivodeship": "dolnoslaskie"
}
```

Percentages exposed by future election endpoints should follow the database convention:
`42.3` means 42.3 percent, not `0.423`.

`GET /regions/{teryt_code}`

Returns one region by its TERYT code.

Response:

```json
{
  "id": 1,
  "teryt_code": "0264011",
  "name": "Wroclaw",
  "region_type": "city_county",
  "voivodeship": "dolnoslaskie"
}
```

Missing region response:

```json
{
  "detail": "Region not found."
}
```

`GET /regions/{teryt_code}/elections`

Returns elections that have imported result rows for a region.

`GET /regions/{teryt_code}/timeline`

Returns a product-ready political timeline for one region, grouped by election and
political bloc.

Response:

```json
{
  "region": {
    "id": 1,
    "teryt_code": "0264011",
    "name": "Wroclaw",
    "region_type": "city_county",
    "voivodeship": "dolnoslaskie"
  },
  "timeline": [
    {
      "election_id": 5,
      "election_year": 2023,
      "election_type": "parliamentary",
      "blocs": [
        {
          "bloc_name": "ko_bloc",
          "votes": 120000,
          "vote_share": "42.1000"
        },
        {
          "bloc_name": "pis_bloc",
          "votes": 100000,
          "vote_share": "35.1200"
        }
      ]
    }
  ]
}
```

## Elections

`GET /elections`

Returns known elections.

Response item:

```json
{
  "id": 1,
  "election_date": "2023-10-15",
  "election_year": 2023,
  "election_type": "parliamentary",
  "round": 1,
  "description": "Sejm 2023"
}
```

`GET /elections/{election_id}/results`

Returns committee-level result facts for one election.

Response item:

```json
{
  "region_id": 1,
  "teryt_code": "0264011",
  "region_name": "Wroclaw",
  "committee_id": 10,
  "committee_name": "Koalicja Obywatelska",
  "bloc_name": "ko_bloc",
  "votes": 120000,
  "vote_share": "42.1000",
  "turnout": "74.5000",
  "eligible_voters": 300000,
  "valid_votes": 285000
}
```
