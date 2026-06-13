# INPE KML Integration Plan

## Summary

`eventos_ativos.kml` is an INPE Programa Queimadas KML feed of active fire events. It is not CSV. The inspected file contains paired placemarks for each active event:

- polygon placemarks representing event/front areas
- point placemarks representing event focus/centroid locations

For the first Sentinela Verde integration, use the point placemarks as optional complementary fire detections. Keep the polygon/front placemarks for a later overlay feature.

## Observed KML Structure

- Root format: KML 2.2 with namespace `http://www.opengis.net/kml/2.2`.
- File name inspected: `INPE/eventos_ativos.kml`.
- Sample count: 1126 placemarks total.
- Placemark split: 563 polygon placemarks and 563 point placemarks.
- Minas Gerais point records in sample: 35.
- Event metadata is stored as escaped HTML inside `<description>`, not as clean `<ExtendedData>`.
- Coordinates use KML order: `longitude,latitude,altitude`.

Relevant fields observed in the description table:

- `Tipo`
- `Data início`
- `Data fim`
- `Duração`
- `Município`
- `Estado`
- `Máx. dias sem chuva`
- `Total de focos`
- `Dias com foco`
- `Último foco`
- `Frentes ativas (último dia)`
- `Desmatamento`
- `Vegetação`
- `Transição`

Observed `Tipo` values include:

- `Nova Queima Isolada`
- `Incêndio`
- `Possível início de incêndio`
- `Atividades Antrópicas`

## Implementation Changes

- Add an optional INPE KML client, controlled by environment variables such as `INPE_ENABLED`, `INPE_KML_URL`, `INPE_FETCH_INTERVAL_MINUTES`, and `INPE_REQUEST_TIMEOUT_MS`.
- Fetch INPE on a schedule, not per frontend request. Default interval should be 10 minutes to match the expected KML update cadence.
- Cache the last successful parse. If INPE fails, continue serving NASA FIRMS data normally.
- Parse KML with namespace-aware XML parsing.
- Select only point placemarks for v1. Ignore polygon placemarks until a dedicated event-front overlay is designed.
- Decode escaped HTML from `<description>` and extract table rows into metadata.
- Normalize point placemarks into the current fire event shape:
  - `latitude` and `longitude` from KML coordinates
  - `acq_date` and `acq_time` from `Último foco`
  - `satellite` as `INPE` unless the live feed exposes a real satellite field
  - `confidence` from `Tipo`
  - `frp` as `None`
  - `daynight` as empty/unknown
  - preserve INPE-specific fields in metadata if the app model is extended
- Filter by `Estado == MINAS GERAIS`, then confirm coordinates with the existing MG geometry helpers.
- Add source display in the popup so INPE events are clearly distinguished from NASA FIRMS detections.

## Deduplication Approach

Do not treat INPE active events as identical to NASA FIRMS raw hotspots by default. The inspected KML appears to expose aggregated active events/fronts rather than the same per-satellite record shape used by FIRMS.

For v1:

- Keep INPE as an optional complementary source layer or merged event list with conservative deduplication.
- If deduplicating against FIRMS, require close coordinates and close acquisition time.
- Avoid satellite/sensor equivalence rules until the live INPE feed exposes those values.
- Preserve source attribution so users can tell whether a marker came from NASA FIRMS, INPE, or both.

## Tests

Add small KML fixtures based on the inspected structure. Do not commit a large production fixture unless explicitly needed.

Required tests:

- valid KML point parsing
- polygon placemarks ignored for v1
- escaped HTML description table parsing
- invalid/missing coordinates rejected
- invalid/missing `Último foco` rejected or handled safely
- Minas Gerais filtering by `Estado`
- coordinate confirmation with existing MG geometry
- INPE disabled via config
- INPE fetch failure with and without cached data
- source label visible in frontend popup output

## Open Questions

- Confirm the official production URL for the generated KML before implementing network fetches.
- Confirm whether the production KML ever includes satellite/sensor fields not present in the inspected sample.
- Decide whether large raw KML samples should be committed, ignored, or replaced by small test fixtures.
