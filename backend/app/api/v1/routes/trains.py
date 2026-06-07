from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db.database import get_db, DBStation
from app.core.scenario_engine import scenario_engine
from app.models.train import TrainPosition, TrainStatus, TrainRouteNode

router = APIRouter()

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
                    recorded_at=datetime.utcnow()
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
                recorded_at=datetime.utcnow()
            )
        ]


@router.get("/{train_no}", response_model=TrainStatus)
async def get_train_status(train_no: str, db: AsyncSession = Depends(get_db)):
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
            last_updated=datetime.utcnow(),
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
                last_updated=datetime.utcnow(),
                route=route_nodes
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Train {train_no} not found"
        )
