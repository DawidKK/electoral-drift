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
