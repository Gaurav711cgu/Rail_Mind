import json
from datetime import datetime
from typing import List, Optional
import networkx as nx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.config import settings
from app.db.database import get_db, DBDisruption, DBRecommendation, DBAuditEntry
from app.core.scenario_engine import scenario_engine
from app.models.disruption import CascadeEvent, CascadeReport
from app.models.recommendation import DispatchRec

router = APIRouter()

# Helper to sync scenario state to the SQLite DB
async def sync_scenario_step_to_db(db: AsyncSession, state: dict):
    # 1. Sync Disruptions
    for d in state["disruptions"]:
        # Check if already exists
        result = await db.execute(select(DBDisruption).where(DBDisruption.id == d["id"]))
        existing = result.scalars().first()
        if not existing:
            db_disp = DBDisruption(
                id=d["id"],
                train_no=d["train_no"],
                section_from=d["section_from"],
                section_to=d["section_to"],
                disruption_type=d["disruption_type"],
                severity=d["severity"],
                cascade_depth=d["cascade_depth"],
                trains_affected_json=json.dumps([t["train_no"] for t in state["trains"] if t["current_delay"] > 0]),
                passengers_affected=4820 if d["severity"] == "CRITICAL" else 140,
                status=d["status"],
                detected_at=datetime.utcnow()
            )
            db.add(db_disp)
        else:
            existing.status = d["status"]
            existing.severity = d["severity"]
            existing.cascade_depth = d["cascade_depth"]
            if d["status"] == "RESOLVED":
                existing.resolved_at = datetime.utcnow()
    
    # 2. Sync Recommendations
    for r in state["recommendations"]:
        result = await db.execute(select(DBRecommendation).where(DBRecommendation.id == r["id"]))
        existing = result.scalars().first()
        if not existing:
            db_rec = DBRecommendation(
                id=r["id"],
                disruption_id=r["disruption_id"],
                type=r["type"],
                target_train=r["target_train"],
                target_section=r["target_section"],
                reasoning=r["reasoning"],
                confidence=r["confidence"],
                tier=r["tier"],
                is_approved=r["is_approved"],
                generated_at=datetime.utcnow()
            )
            db.add(db_rec)
        else:
            existing.is_approved = r["is_approved"]
            
    # 3. Sync Audit Log Entries
    for a in state["audit_entries"]:
        result = await db.execute(select(DBAuditEntry).where(DBAuditEntry.current_hash == a["hash"]))
        existing = result.scalars().first()
        if not existing:
            # Fetch previous entry to get the previous hash
            res_prev = await db.execute(select(DBAuditEntry).order_by(DBAuditEntry.id.desc()).limit(1))
            prev_entry = res_prev.scalars().first()
            prev_hash = prev_entry.current_hash if prev_entry else "0000000000000000000000000000000000000000000000000000000000000000"
            
            db_audit = DBAuditEntry(
                agent_name=a["agent"],
                action_type=a["action"],
                target=a["target"],
                reasoning=a["reasoning"],
                confidence=a["confidence"],
                timestamp=datetime.utcnow(),
                prev_hash=prev_hash,
                current_hash=a["hash"]
            )
            db.add(db_audit)
            
    await db.commit()


@router.get("/scenario")
async def get_scenario_state():
    return scenario_engine.get_state()


@router.post("/scenario/next")
async def next_scenario_step(db: AsyncSession = Depends(get_db)):
    step = scenario_engine.next_step()
    state = scenario_engine.get_state()
    if settings.SCENARIO_MODE:
        await sync_scenario_step_to_db(db, state)
    return state


@router.post("/scenario/reset")
async def reset_scenario(db: AsyncSession = Depends(get_db)):
    state = scenario_engine.reset()
    if settings.SCENARIO_MODE:
        # Clear dynamic tables to restart clean
        await db.execute(delete(DBDisruption))
        await db.execute(delete(DBRecommendation))
        await db.execute(delete(DBAuditEntry))
        await db.commit()
        await sync_scenario_step_to_db(db, state)
    return state


@router.get("/simulate", response_model=CascadeReport)
async def simulate_cascade(disruption_id: str, db: AsyncSession = Depends(get_db)):
    # Retrieve the target disruption
    if settings.SCENARIO_MODE:
        state = scenario_engine.get_state()
        disruption = None
        for d in state["disruptions"]:
            if d["id"] == disruption_id:
                disruption = d
                break
        if not disruption:
            raise HTTPException(status_code=404, detail="Disruption not found in scenario context")
            
        # Run graph network model using NetworkX to identify affected trains downstream
        G = nx.DiGraph()
        G.add_node("NDLS", name="New Delhi")
        G.add_node("GZB", name="Ghaziabad")
        G.add_node("ALJN", name="Aligarh")
        G.add_node("CNB", name="Kanpur Central")
        
        G.add_edge("NDLS", "GZB", distance=25)
        G.add_edge("GZB", "ALJN", distance=100)
        G.add_edge("ALJN", "CNB", distance=210)
        
        # Calculate reachability of cascade from the disruption node
        start_node = disruption["section_from"]
        affected_nodes = list(nx.bfs_tree(G, source=start_node))
        
        # Create CascadeEvents based on reachable nodes and active trains
        cascade_events = []
        confidence_factor = 0.95
        
        # Vande Bharat 22415 runs GZB -> ALJN -> CNB
        if "ALJN" in affected_nodes or "GZB" in affected_nodes:
            cascade_events.append(
                CascadeEvent(
                    train_no="22415",
                    station="ALJN",
                    delay_added_minutes=15,
                    confidence=0.91
                )
            )
            
        # Freight BOXN-902 runs GZB -> ALJN
        if "ALJN" in affected_nodes:
            cascade_events.append(
                CascadeEvent(
                    train_no="BOXN-902",
                    station="ALJN",
                    delay_added_minutes=32,
                    confidence=0.88
                )
            )
            
        return CascadeReport(
            root_disruption_id=disruption_id,
            cascade_depth=len(cascade_events),
            affected_trains=cascade_events,
            total_passengers_affected=4820 if disruption["severity"] == "CRITICAL" else 140,
            weather_factor=1.0,
            agent_confidence=confidence_factor,
            reasoning=f"BFS propagation tree starting from {start_node} identifies {len(cascade_events)} downstream conflicts."
        )
    else:
        # DB mode query placeholder
        raise HTTPException(status_code=501, detail="Live simulation requires real-time telemetry ingestion pipeline")


@router.post("/recommendations/{rec_id}/approve", response_model=DispatchRec)
async def approve_recommendation(rec_id: str, db: AsyncSession = Depends(get_db)):
    if settings.SCENARIO_MODE:
        # Update inside the scenario_engine memory representation
        state = scenario_engine.get_state()
        found = False
        for r in state["recommendations"]:
            if r["id"] == rec_id:
                r["is_approved"] = True
                found = True
                break
                
        # Also update DB representation
        result = await db.execute(select(DBRecommendation).where(DBRecommendation.id == rec_id))
        db_rec = result.scalars().first()
        if db_rec:
            db_rec.is_approved = True
            await db.commit()
            
        if not found and not db_rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")
            
        # Log this approval to the Audit log
        db_audit = DBAuditEntry(
            agent_name="Controller_Northern",
            action_type="ACTION_APPROVED",
            target=rec_id,
            reasoning="Approved hold recommendation manually via Controller Override Console.",
            confidence=1.0,
            timestamp=datetime.utcnow(),
            prev_hash=state["audit_entries"][-1]["hash"] if state["audit_entries"] else "0",
            current_hash=scenario_engine._hash(f"approved-{rec_id}")
        )
        db.add(db_audit)
        await db.commit()
        
        # Add to scenario log memory
        state["logs"].append(f"[DispatchAgent] Action Approved: Hold recommendation approved by User 'Controller_Northern'.")
        
        return DispatchRec(
            id=rec_id,
            disruption_id="disp-001",
            target_train="BOXN-902",
            target_section="GZB-ALJN loop line",
            reasoning="Hold Freight BOXN-902",
            confidence=0.78,
            tier=2,
            is_approved=True
        )
    else:
        result = await db.execute(select(DBRecommendation).where(DBRecommendation.id == rec_id))
        db_rec = result.scalars().first()
        if not db_rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        db_rec.is_approved = True
        await db.commit()
        await db.refresh(db_rec)
        return DispatchRec(
            id=db_rec.id,
            disruption_id=db_rec.disruption_id,
            type=db_rec.type,
            target_train=db_rec.target_train,
            target_section=db_rec.target_section,
            reasoning=db_rec.reasoning,
            confidence=db_rec.confidence,
            tier=db_rec.tier,
            is_approved=db_rec.is_approved,
            override_reason=db_rec.override_reason,
            generated_at=db_rec.generated_at
        )


@router.post("/recommendations/{rec_id}/override", response_model=DispatchRec)
async def override_recommendation(rec_id: str, override_reason: str, db: AsyncSession = Depends(get_db)):
    if settings.SCENARIO_MODE:
        state = scenario_engine.get_state()
        found = False
        for r in state["recommendations"]:
            if r["id"] == rec_id:
                r["is_approved"] = False
                r["override_reason"] = override_reason
                found = True
                break
                
        result = await db.execute(select(DBRecommendation).where(DBRecommendation.id == rec_id))
        db_rec = result.scalars().first()
        if db_rec:
            db_rec.is_approved = False
            db_rec.override_reason = override_reason
            await db.commit()
            
        if not found and not db_rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")
            
        # Log to Audit
        db_audit = DBAuditEntry(
            agent_name="Controller_Northern",
            action_type="RECOMMENDATION_OVERRIDDEN",
            target=rec_id,
            reasoning=f"Overridden: {override_reason}",
            confidence=1.0,
            timestamp=datetime.utcnow(),
            prev_hash=state["audit_entries"][-1]["hash"] if state["audit_entries"] else "0",
            current_hash=scenario_engine._hash(f"override-{rec_id}")
        )
        db.add(db_audit)
        await db.commit()
        
        state["logs"].append(f"[DispatchAgent] Action Overridden: Hold recommendation rejected with reason: {override_reason}")
        
        return DispatchRec(
            id=rec_id,
            disruption_id="disp-001",
            target_train="BOXN-902",
            target_section="GZB-ALJN loop line",
            reasoning="Hold Freight BOXN-902",
            confidence=0.78,
            tier=2,
            is_approved=False,
            override_reason=override_reason
        )
    else:
        result = await db.execute(select(DBRecommendation).where(DBRecommendation.id == rec_id))
        db_rec = result.scalars().first()
        if not db_rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        db_rec.is_approved = False
        db_rec.override_reason = override_reason
        await db.commit()
        await db.refresh(db_rec)
        return DispatchRec(
            id=db_rec.id,
            disruption_id=db_rec.disruption_id,
            type=db_rec.type,
            target_train=db_rec.target_train,
            target_section=db_rec.target_section,
            reasoning=db_rec.reasoning,
            confidence=db_rec.confidence,
            tier=db_rec.tier,
            is_approved=db_rec.is_approved,
            override_reason=db_rec.override_reason,
            generated_at=db_rec.generated_at
        )
