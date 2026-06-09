---
title: Rail_Mind
emoji: 🚂
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# RailMind Backend Service

Autonomous agentic dispatching engine and ML telemetry pipeline for Indian Railways. 

This Space runs a Docker container hosting the FastAPI server. It is linked to the Vercel operator console.

## RapidAPI IRCTC Provider

RailMind can proxy the unofficial RapidAPI IRCTC provider from the backend so API keys never need to live in frontend code.

1. Copy `.env.example` to `.env`.
2. Set `RAPIDAPI_IRCTC_KEY` to your RapidAPI key.
3. Set `SCENARIO_MODE=false` and `REAL_DATA_REQUIRED=true` for production/live-only operation, or keep `SCENARIO_MODE=true` to use scenario controls as disruption simulation on top of live train telemetry.
4. Set `LIVE_TRAIN_WATCHLIST` to the comma-separated train numbers you want the live operations console to track.
5. Restart the backend.

Telemetry behavior:

- If `RAPIDAPI_IRCTC_KEY` is configured, `/api/v1/cascade/scenario` replaces synthetic scenario train positions with RapidAPI live status snapshots. Scenario steps still control disruptions, recommendations, logs, and audit story progression.
- If `RAPIDAPI_IRCTC_KEY` is missing and `REAL_DATA_REQUIRED=false`, the app falls back to built-in scenario train positions.
- If `REAL_DATA_REQUIRED=true`, RapidAPI failures return a `502` instead of silently serving synthetic telemetry.

Useful routes:

- `GET /api/v1/trains/rapidapi/endpoints`
- `GET /api/v1/health/data-freshness`
- `GET /api/v1/trains/live`
- `GET /api/v1/trains/rapidapi/search-station?query=BJU`
- `GET /api/v1/trains/rapidapi/search-train?query=190`
- `GET /api/v1/trains/rapidapi/trains-between-stations?from_station_code=BVI&to_station_code=NDLS`
- `GET /api/v1/trains/rapidapi/live-status?train_no=19038&start_day=1`
- `GET /api/v1/trains/rapidapi/train-schedule?train_no=12936`
- `GET /api/v1/trains/rapidapi/pnr-status?pnr_number=1234567890`
- `GET /api/v1/trains/rapidapi/seat-availability?train_no=19038&from_station_code=ST&to_station_code=BVI&class_type=2A&quota=GN`
- `GET /api/v1/trains/rapidapi/seat-availability-v2?train_no=19038&from_station_code=ST&to_station_code=BVI&class_type=2A&quota=GN`
- `GET /api/v1/trains/rapidapi/train-classes?train_no=19038`
- `GET /api/v1/trains/rapidapi/fare?train_no=19038&from_station_code=ST&to_station_code=BVI`
- `GET /api/v1/trains/rapidapi/trains-by-station?station_code=NDLS`
- `GET /api/v1/trains/rapidapi/live-station?station_code=NDLS&hours=1`
- `GET /api/v1/trains/rapidapi/{endpoint_key}?providerParam=value`

The generic route is whitelisted for the provider endpoints visible in RapidAPI: station search, train search, trains between stations, live train status, train schedule, PNR status, seat availability, train classes, fare, trains by station, and live station.
