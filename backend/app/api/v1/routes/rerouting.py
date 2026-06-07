from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.models.recommendation import ReroutingSuggestion, AlternativeTrain

router = APIRouter()

@router.get("/", response_model=List[ReroutingSuggestion])
async def list_rerouting_suggestions(disruption_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    if settings.SCENARIO_MODE:
        # Provide suggestions matching the scenario presentation
        # Vande Bharat 22415 is offered as an alternative for Shatabdi passengers
        suggestions = [
            ReroutingSuggestion(
                id="reroute-001",
                disruption_id=disruption_id or "disp-001",
                passenger_origin="NDLS",
                passenger_destination="ALJN",
                alternatives=[
                    AlternativeTrain(
                        train_no="22415",
                        departure_station="NDLS",
                        departure_time="15:00",
                        arrival_time="16:35",
                        seat_availability="RAC 14",
                        rac_confirmation_probability=0.88,
                        connection_required=False
                    )
                ],
                advisory_text="Stranded passengers at NDLS on train 12002 are advised to transfer to Vande Bharat 22415 leaving platform 9. Confirmed probability is 88% based on historical Monday cancellation rates.",
                generated_by_agent="NotificationAgent",
                confidence=0.90,
                generated_at=datetime.utcnow()
            )
        ]
        return suggestions
    else:
        # DB query placeholder
        return []


@router.get("/{disruption_id}", response_model=ReroutingSuggestion)
async def get_rerouting_for_disruption(disruption_id: str, db: AsyncSession = Depends(get_db)):
    suggestions = await list_rerouting_suggestions(disruption_id=disruption_id, db=db)
    if not suggestions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No suggestions found for disruption {disruption_id}"
        )
    return suggestions[0]
