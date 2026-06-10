from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db.database import get_db, DBStation
from app.core.scenario_engine import scenario_engine
from app.models.train import TrainPosition, TrainStatus, TrainRouteNode
from app.services.live_rail_data import live_rail_data
from app.services.rapidapi_irctc import rapidapi_irctc

router = APIRouter()

SUPPORTED_RAPIDAPI_ENDPOINTS: Dict[str, str] = {
    "search-station": "/api/v1/searchStation",
    "search-train": "/api/v1/searchTrain",
    "trains-between-stations-v3": "/api/v3/trainBetweenStations",
    "train-live-status": "/api/v1/liveTrainStatus",
    "train-schedule": "/api/v1/getTrainSchedule",
    "train-schedule-v2": "/api/v2/getTrainSchedule",
    "pnr-status-v3": "/api/v3/getPNRStatus",
    "seat-availability": "/api/v1/checkSeatAvailability",
    "seat-availability-v2": "/api/v2/checkSeatAvailability",
    "train-classes": "/api/v1/getTrainClasses",
    "fare": "/api/v2/getFare",
    "trains-by-station": "/api/v3/getTrainsByStation",
    "live-station": "/api/v3/getLiveStation",
}


speed_locks = {
    "DLI-GZB": 110,
    "GZB-ALJN": 130,
    "ALJN-CNB": 130,
}


def drop_empty_params(params: Dict[str, Optional[str | int]]) -> Dict[str, str | int]:
    return {key: value for key, value in params.items() if value not in (None, "")}

# Helper to generate mock route details for the scenario trains
def get_mock_route_for_train(train_no: str, delay: int) -> List[TrainRouteNode]:
    # Time formats as HH:MM
    if train_no == "12002":
        # NDLS-BCT Shatabdi
        return [
            TrainRouteNode(
                station_code="NDLS",
                station_name="New Delhi",
                scheduled_departure="06:00",
                actual_departure=f"06:{delay:02d}" if delay < 60 else "07:00",
                delay_departure=delay,
                status="ARRIVED" if delay > 0 else "SCHEDULED"
            ),
            TrainRouteNode(
                station_code="MTJ",
                station_name="Mathura Jn",
                scheduled_arrival="07:20",
                scheduled_departure="07:22",
                actual_arrival=f"07:{20+delay:02d}" if (20+delay) < 60 else "08:10",
                delay_arrival=delay,
                status="SCHEDULED"
            ),
            TrainRouteNode(
                station_code="AGC",
                station_name="Agra Cantt",
                scheduled_arrival="08:10",
                scheduled_departure="08:15",
                status="SCHEDULED"
            )
        ]
    elif train_no == "22415":
        # NDLS-BSB Vande Bharat
        return [
            TrainRouteNode(
                station_code="NDLS",
                station_name="New Delhi",
                scheduled_departure="15:00",
                actual_departure="15:00",
                status="DEPARTED"
            ),
            TrainRouteNode(
                station_code="ALJN",
                station_name="Aligarh",
                scheduled_arrival="16:20",
                scheduled_departure="16:22",
                actual_arrival=f"16:{20+delay:02d}",
                delay_arrival=delay,
                status="ARRIVED" if delay > 0 else "SCHEDULED"
            ),
            TrainRouteNode(
                station_code="CNB",
                station_name="Kanpur Central",
                scheduled_arrival="18:30",
                status="SCHEDULED"
            )
        ]
    elif train_no == "BOXN-902":
        # Coal Freight
        return [
            TrainRouteNode(
                station_code="GZB",
                station_name="Ghaziabad",
                scheduled_departure="14:00",
                actual_departure="14:05",
                delay_departure=5,
                status="DEPARTED"
            ),
            TrainRouteNode(
                station_code="ALJN",
                station_name="Aligarh",
                scheduled_arrival="16:00",
                actual_arrival=f"16:{delay:02d}",
                delay_arrival=delay,
                status="ARRIVED" if delay > 10 else "SCHEDULED"
            )
        ]
    return []


@router.get("", response_model=List[TrainPosition])
async def list_trains(db: AsyncSession = Depends(get_db)):
    if settings.RAPIDAPI_IRCTC_KEY:
        live_trains = await live_rail_data.live_watchlist_snapshot()
        return [
            TrainPosition(
                train_no=train["train_no"],
                train_name=train["train_name"],
                at_station=train["current_station"],
                delay_minutes=train["current_delay"],
                data_source=train["data_source"],
                data_quality=train["data_quality"],
                recorded_at=datetime.now(timezone.utc),
            )
            for train in live_trains
        ]

    if settings.SCENARIO_MODE:
        state = scenario_engine.get_state()
        result = []
        for t in state["trains"]:
            result.append(
                TrainPosition(
                    train_no=t["train_no"],
                    train_name=t["train_name"],
                    at_station=t["current_station"],
                    delay_minutes=t["current_delay"],
                    data_source="cache" if settings.SCENARIO_MODE else "ntes",
                    data_quality=1.0,
                    recorded_at=datetime.now(timezone.utc)
                )
            )
        return result
    else:
        # DB mode query (if live data ingested)
        # For hackathon, return seeded list if DB empty
        return [
            TrainPosition(
                train_no="12002",
                train_name="NDLS-BCT Shatabdi Express",
                at_station="NDLS",
                delay_minutes=0,
                data_source="db",
                data_quality=1.0,
                recorded_at=datetime.now(timezone.utc)
            )
        ]


@router.get("/live", response_model=List[TrainPosition])
async def list_live_trains(
    zone: Optional[str] = None,
    min_delay: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    trains = await list_trains(db)
    return [train for train in trains if train.delay_minutes >= min_delay]


@router.get("/between")
async def trains_between(
    from_station: str = Query(..., alias="from", min_length=2, max_length=10),
    to_station: str = Query(..., alias="to", min_length=2, max_length=10),
    date: Optional[str] = Query(None),
):
    return await rapidapi_irctc.get(
        "/api/v3/trainBetweenStations",
        drop_empty_params({
            "fromStationCode": from_station.upper(),
            "toStationCode": to_station.upper(),
            "dateOfJourney": date,
        }),
    )


@router.get("/speed-lock")
async def get_speed_locks():
    return speed_locks


@router.post("/speed-lock")
async def update_speed_lock(section_code: str, speed_limit: int):
    if section_code not in speed_locks:
        raise HTTPException(status_code=404, detail="Section code not found")
    speed_locks[section_code] = speed_limit
    return {"section_code": section_code, "speed_limit": speed_limit}


@router.get("/rapidapi/search-station")
async def rapidapi_search_station(query: str = Query(..., min_length=2)):
    return await rapidapi_irctc.get("/api/v1/searchStation", {"query": query})


@router.get("/rapidapi/search-train")
async def rapidapi_search_train(query: str = Query(..., min_length=2)):
    return await rapidapi_irctc.get("/api/v1/searchTrain", {"query": query})


@router.get("/rapidapi/trains-between-stations")
async def rapidapi_trains_between_stations(
    from_station_code: str = Query(..., min_length=2, max_length=10),
    to_station_code: str = Query(..., min_length=2, max_length=10),
    date_of_journey: Optional[str] = Query(None, description="Optional provider date parameter, usually YYYY-MM-DD"),
):
    return await rapidapi_irctc.get(
        "/api/v3/trainBetweenStations",
        drop_empty_params({
            "fromStationCode": from_station_code.upper(),
            "toStationCode": to_station_code.upper(),
            "dateOfJourney": date_of_journey,
        }),
    )


@router.get("/rapidapi/live-status")
async def rapidapi_live_train_status(
    train_no: str = Query(..., min_length=4, max_length=6),
    start_day: int = Query(0, ge=0, le=4, description="0=today, 1=yesterday, up to 4 for longer routes"),
):
    return await rapidapi_irctc.get(
        "/api/v1/liveTrainStatus",
        {"trainNo": train_no, "startDay": start_day},
    )


@router.get("/rapidapi/train-schedule")
async def rapidapi_train_schedule(train_no: str = Query(..., min_length=4, max_length=6)):
    return await rapidapi_irctc.get("/api/v1/getTrainSchedule", {"trainNo": train_no})


@router.get("/rapidapi/pnr-status")
async def rapidapi_pnr_status(pnr_number: str = Query(..., min_length=10, max_length=10)):
    return await rapidapi_irctc.get("/api/v3/getPNRStatus", {"pnrNumber": pnr_number})


@router.get("/rapidapi/seat-availability")
async def rapidapi_seat_availability(
    train_no: str = Query(..., min_length=4, max_length=6),
    from_station_code: str = Query(..., min_length=2, max_length=10),
    to_station_code: str = Query(..., min_length=2, max_length=10),
    class_type: str = Query(..., min_length=2, max_length=4),
    quota: str = Query("GN", min_length=2, max_length=4),
    date: Optional[str] = Query(None, description="Optional provider journey date parameter"),
):
    return await rapidapi_irctc.get(
        "/api/v1/checkSeatAvailability",
        drop_empty_params({
            "trainNo": train_no,
            "fromStationCode": from_station_code.upper(),
            "toStationCode": to_station_code.upper(),
            "classType": class_type.upper(),
            "quota": quota.upper(),
            "date": date,
        }),
    )


@router.get("/rapidapi/seat-availability-v2")
async def rapidapi_seat_availability_v2(
    train_no: str = Query(..., min_length=4, max_length=6),
    from_station_code: str = Query(..., min_length=2, max_length=10),
    to_station_code: str = Query(..., min_length=2, max_length=10),
    class_type: str = Query(..., min_length=2, max_length=4),
    quota: str = Query("GN", min_length=2, max_length=4),
    date: Optional[str] = Query(None, description="Optional provider journey date parameter"),
):
    return await rapidapi_irctc.get(
        "/api/v2/checkSeatAvailability",
        drop_empty_params({
            "trainNo": train_no,
            "fromStationCode": from_station_code.upper(),
            "toStationCode": to_station_code.upper(),
            "classType": class_type.upper(),
            "quota": quota.upper(),
            "date": date,
        }),
    )


@router.get("/rapidapi/train-classes")
async def rapidapi_train_classes(train_no: str = Query(..., min_length=4, max_length=6)):
    return await rapidapi_irctc.get("/api/v1/getTrainClasses", {"trainNo": train_no})


@router.get("/rapidapi/fare")
async def rapidapi_fare(
    train_no: str = Query(..., min_length=4, max_length=6),
    from_station_code: str = Query(..., min_length=2, max_length=10),
    to_station_code: str = Query(..., min_length=2, max_length=10),
):
    return await rapidapi_irctc.get(
        "/api/v2/getFare",
        {
            "trainNo": train_no,
            "fromStationCode": from_station_code.upper(),
            "toStationCode": to_station_code.upper(),
        },
    )


@router.get("/rapidapi/trains-by-station")
async def rapidapi_trains_by_station(station_code: str = Query(..., min_length=2, max_length=10)):
    return await rapidapi_irctc.get("/api/v3/getTrainsByStation", {"stationCode": station_code.upper()})


@router.get("/rapidapi/live-station")
async def rapidapi_live_station(
    station_code: Optional[str] = Query(None, min_length=2, max_length=10),
    hours: int = Query(1, ge=1, le=24),
):
    return await rapidapi_irctc.get(
        "/api/v3/getLiveStation",
        drop_empty_params({
            "stationCode": station_code.upper() if station_code else None,
            "hours": hours,
        }),
    )


@router.get("/rapidapi/endpoints")
async def rapidapi_supported_endpoints():
    return {
        "provider": "rapidapi-irctc",
        "endpoints": SUPPORTED_RAPIDAPI_ENDPOINTS,
        "usage": "/api/v1/trains/rapidapi/{endpoint_key}?providerParam=value",
    }


@router.get("/rapidapi/{endpoint_key}")
async def rapidapi_passthrough(endpoint_key: str, request: Request):
    provider_path = SUPPORTED_RAPIDAPI_ENDPOINTS.get(endpoint_key)
    if not provider_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": f"RapidAPI endpoint '{endpoint_key}' is not configured",
                "supported_endpoints": list(SUPPORTED_RAPIDAPI_ENDPOINTS.keys()),
            },
        )

    return await rapidapi_irctc.get(provider_path, dict(request.query_params))


@router.get("/{train_no}", response_model=TrainStatus)
async def get_train_status(train_no: str, db: AsyncSession = Depends(get_db)):
    if settings.RAPIDAPI_IRCTC_KEY:
        try:
            live_train = await live_rail_data.live_train_snapshot(train_no)
            route_nodes = get_mock_route_for_train(train_no, live_train["current_delay"])
            return TrainStatus(
                train_no=live_train["train_no"],
                train_name=live_train["train_name"],
                current_station=live_train["current_station"],
                current_delay=live_train["current_delay"],
                last_updated=datetime.now(timezone.utc),
                route=route_nodes,
            )
        except Exception:
            pass

    if settings.SCENARIO_MODE:
        state = scenario_engine.get_state()
        train_data = None
        for t in state["trains"]:
            if t["train_no"] == train_no:
                train_data = t
                break
        
        if not train_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Train {train_no} not found in current operational context"
            )
            
        route_nodes = get_mock_route_for_train(train_no, train_data["current_delay"])
        
        return TrainStatus(
            train_no=train_data["train_no"],
            train_name=train_data["train_name"],
            current_station=train_data["current_station"],
            current_delay=train_data["current_delay"],
            last_updated=datetime.now(timezone.utc),
            route=route_nodes
        )
    else:
        # Query from DB/cache. Fallback to base mock.
        if train_no in ["12002", "22415", "BOXN-902"]:
            route_nodes = get_mock_route_for_train(train_no, 0)
            return TrainStatus(
                train_no=train_no,
                train_name="Shatabdi Express" if train_no == "12002" else "Vande Bharat" if train_no == "22415" else "Coal Freight",
                current_station="NDLS",
                current_delay=0,
                last_updated=datetime.now(timezone.utc),
                route=route_nodes
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Train {train_no} not found"
        )
