from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
from app.config import settings
from app.models.recommendation import DispatchRec

router = APIRouter()

# Simple in-memory storage for recommendations to allow approval/override state changes
# In production, this would query/update the PostgreSQL DB.
_mock_recommendations = [
    DispatchRec(
        id="rec-hold-001",
        disruption_id="disp-001",
        type="HOLD",
        target_train="BOXN-902",
        target_section="GZB-ALJN loop line",
        reasoning="Hold Coal Freight (BOXN-902) to clear track block for high-priority Shatabdi 12002. Reduces net cascade delay by 120 minutes. Escalated due to manual check rule on freight priorities.",
        confidence=0.78,
        tier=2,
        is_approved=False,
        generated_at=datetime.now(timezone.utc)
    )
]

class OverridePayload(BaseModel):
    reason: str

@router.get("/active", response_model=List[DispatchRec])
async def get_active_recommendations():
    """
    Returns pending/active dispatch recommendations.
    """
    return [rec for rec in _mock_recommendations if not rec.is_approved]

@router.get("", response_model=List[DispatchRec])
async def list_recommendations():
    """
    List all dispatch recommendations.
    """
    return _mock_recommendations

@router.post("/{id}/approve", response_model=DispatchRec)
async def approve_recommendation(id: str):
    """
    Approve an escalated recommendation.
    """
    for rec in _mock_recommendations:
        if rec.id == id:
            rec.is_approved = True
            rec.tier = 1  # Auto-resolved now
            return rec
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Recommendation with ID {id} not found."
    )

@router.post("/{id}/override", response_model=DispatchRec)
async def override_recommendation(id: str, payload: OverridePayload):
    """
    Override an escalated recommendation with a custom reasoning.
    """
    for rec in _mock_recommendations:
        if rec.id == id:
            rec.is_approved = True
            rec.override_reason = payload.reason
            rec.reasoning += f" [User Override: {payload.reason}]"
            return rec
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Recommendation with ID {id} not found."
    )
