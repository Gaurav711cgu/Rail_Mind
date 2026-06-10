from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db.database import get_db, DBDisruption
from app.core.scenario_engine import scenario_engine
from app.models.disruption import Disruption
from app.api.v1.routes.auth import require_roles

router = APIRouter()


@router.get("", response_model=List[Disruption])
async def list_disruptions(db: AsyncSession = Depends(get_db)):
    if settings.SCENARIO_MODE:
        state = scenario_engine.get_state()
        result = []
        for d in state["disruptions"]:
            result.append(
                Disruption(
                    id=d["id"],
                    train_no=d["train_no"],
                    section_from=d["section_from"],
                    section_to=d["section_to"],
                    disruption_type=d["disruption_type"],
                    severity=d["severity"],
                    cascade_depth=d["cascade_depth"],
                    trains_affected=[
                        t["train_no"] for t in state["trains"] if t["current_delay"] > 0
                    ],
                    passengers_affected=4820 if d["severity"] == "CRITICAL" else 140,
                    status=d["status"],
                    detected_at=datetime.utcnow(),
                )
            )
        return result
    else:
        result = await db.execute(select(DBDisruption))
        db_disruptions = result.scalars().all()
        return [
            Disruption(
                id=d.id,
                train_no=d.train_no,
                section_from=d.section_from,
                section_to=d.section_to,
                disruption_type=d.disruption_type,
                severity=d.severity,
                cascade_depth=d.cascade_depth,
                trains_affected=[],
                passengers_affected=d.passengers_affected,
                status=d.status,
                detected_at=d.detected_at,
                resolved_at=d.resolved_at,
            )
            for d in db_disruptions
        ]


@router.get("/{disruption_id}", response_model=Disruption)
async def get_disruption(disruption_id: str, db: AsyncSession = Depends(get_db)):
    if settings.SCENARIO_MODE:
        state = scenario_engine.get_state()
        disruption_data = None
        for d in state["disruptions"]:
            if d["id"] == disruption_id:
                disruption_data = d
                break

        if not disruption_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Disruption {disruption_id} not found",
            )

        return Disruption(
            id=disruption_data["id"],
            train_no=disruption_data["train_no"],
            section_from=disruption_data["section_from"],
            section_to=disruption_data["section_to"],
            disruption_type=disruption_data["disruption_type"],
            severity=disruption_data["severity"],
            cascade_depth=disruption_data["cascade_depth"],
            trains_affected=[
                t["train_no"] for t in state["trains"] if t["current_delay"] > 0
            ],
            passengers_affected=4820
            if disruption_data["severity"] == "CRITICAL"
            else 140,
            status=disruption_data["status"],
            detected_at=datetime.utcnow(),
        )
    else:
        result = await db.execute(
            select(DBDisruption).where(DBDisruption.id == disruption_id)
        )
        d = result.scalars().first()
        if not d:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Disruption {disruption_id} not found",
            )
        return Disruption(
            id=d.id,
            train_no=d.train_no,
            section_from=d.section_from,
            section_to=d.section_to,
            disruption_type=d.disruption_type,
            severity=d.severity,
            cascade_depth=d.cascade_depth,
            trains_affected=[],
            passengers_affected=d.passengers_affected,
            status=d.status,
            detected_at=d.detected_at,
            resolved_at=d.resolved_at,
        )


@router.post("", response_model=Disruption)
async def create_disruption(
    disruption: Disruption,
    db: AsyncSession = Depends(get_db),
    _controller=Depends(require_roles("CONTROLLER", "ADMIN")),
):
    db_disruption = DBDisruption(
        id=disruption.id or f"disp-{int(datetime.utcnow().timestamp())}",
        train_no=disruption.train_no,
        section_from=disruption.section_from,
        section_to=disruption.section_to,
        disruption_type=disruption.disruption_type,
        severity=disruption.severity,
        cascade_depth=disruption.cascade_depth,
        trains_affected_json="[]",
        passengers_affected=disruption.passengers_affected,
        status="ACTIVE",
        detected_at=datetime.utcnow(),
    )
    db.add(db_disruption)
    await db.commit()
    await db.refresh(db_disruption)

    return Disruption(
        id=db_disruption.id,
        train_no=db_disruption.train_no,
        section_from=db_disruption.section_from,
        section_to=db_disruption.section_to,
        disruption_type=db_disruption.disruption_type,
        severity=db_disruption.severity,
        cascade_depth=db_disruption.cascade_depth,
        trains_affected=[],
        passengers_affected=db_disruption.passengers_affected,
        status=db_disruption.status,
        detected_at=db_disruption.detected_at,
    )
