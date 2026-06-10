import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.agents.monitor_agent import MonitorAgent
from app.agents.conflict_detector import ConflictDetector
from app.agents.cascade_predictor import CascadePredictor
from app.agents.dispatch_agent import DispatchAgent
from app.agents.notification_agent import NotificationAgent
from app.agents.audit_agent import AuditAgent

class AgentOrchestrator:
    """
    Coordinates state routing between specialized agents.
    Simulates a LangGraph state machine, feeding agent updates back into the shared context
    and logging actions for transparency.
    """
    def __init__(self):
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        # Register agents in the topology sequence
        self.pipeline = [
            MonitorAgent(),
            ConflictDetector(),
            CascadePredictor(),
            DispatchAgent(),
            NotificationAgent(),
            AuditAgent()
        ]
        self.agent_health = {
            agent.agent_name: {
                "last_run": None,
                "last_confidence": 1.0,
                "status": "healthy",
                "last_error": None
            }
            for agent in self.pipeline
        }

    async def run_pipeline(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the full multi-agent pipeline sequentially, updating state at each node.
        If an agent indicates a low confidence score (< 0.85) at a decision node,
        the pipeline flags the state as 'escalated' to trigger a human controller override.
        """
        state = dict(initial_state)
        state.setdefault("logs", [])
        state.setdefault("disruptions", [])
        state.setdefault("recommendations", [])
        state.setdefault("audit_chain", [])
        state.setdefault("escalated", False)
        
        state["logs"].append(f"[Orchestrator] Starting multi-agent pipeline at {initial_state.get('timestamp', 'nominal-time')}")
        
        for agent in self.pipeline:
            # Skip downstream execution if pipeline is halted for manual controller intervention
            if state["escalated"] and agent.agent_name not in ["NotificationAgent", "AuditAgent"]:
                state["logs"].append(f"[Orchestrator] Bypassing {agent.agent_name} - manual controller escalation active.")
                continue
                
            try:
                self.agent_health[agent.agent_name]["status"] = "running"
                updates, confidence, reasoning = await agent.process(state)
                
                # Apply updates to shared context state
                for key, val in updates.items():
                    state[key] = val
                    
                # Append log entry from agent execution
                log_msg = f"[{agent.agent_name}] Action completed. Confidence: {confidence:.2f}. Reasoning: {reasoning}"
                state["logs"].append(log_msg)
                
                # Update health info
                self.agent_health[agent.agent_name].update({
                    "last_run": datetime.utcnow().isoformat(),
                    "last_confidence": confidence,
                    "status": "healthy",
                    "last_error": None
                })
                
                # Check confidence threshold for escalation
                if confidence < 0.85 and agent.agent_name == "DispatchAgent":
                    state["escalated"] = True
                    state["logs"].append(f"[Orchestrator] Halted auto-execution. Escaled to local dispatcher controller.")
                    
            except Exception as e:
                err_msg = f"[Orchestrator] Error executing {agent.agent_name}: {str(e)}"
                state["logs"].append(err_msg)
                print(err_msg)
                self.agent_health[agent.agent_name].update({
                    "last_run": datetime.utcnow().isoformat(),
                    "status": "degraded",
                    "last_error": str(e)
                })
                
        state["logs"].append("[Orchestrator] Multi-agent execution cycle completed successfully.")
        return state

    async def _run_monitor_loop(self) -> None:
        from app.db.database import AsyncSessionLocal
        from sqlalchemy import select
        from app.db.database import DBTrain
        
        # Give DB seed a few seconds on startup before running monitor loop
        await asyncio.sleep(5)
        
        while self._running:
            try:
                async with AsyncSessionLocal() as session:
                    result = await session.execute(select(DBTrain))
                    db_trains = result.scalars().all()
                    
                    trains = []
                    for t in db_trains:
                        trains.append({
                            "train_no": t.train_no,
                            "train_name": t.train_name,
                            "source": t.source,
                            "destination": t.destination,
                            "current_station": t.current_station,
                            "next_station": t.next_station,
                            "status": t.status,
                            "current_delay": t.current_delay,
                            "schedule_deviation": t.schedule_deviation,
                            "kavach_enabled": t.kavach_enabled
                        })
                
                initial_state = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "trains": trains,
                    "disruptions": [],
                    "recommendations": []
                }
                
                await self.run_pipeline(initial_state)
                
            except Exception as e:
                print(f"[Orchestrator] Monitor loop error: {e}")
                
            await asyncio.sleep(60)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._monitor_task = asyncio.create_task(self._run_monitor_loop())
        print("[Orchestrator] Background monitoring loop started.")

    async def stop(self) -> None:
        self._running = False
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        print("[Orchestrator] Background monitoring loop stopped.")

# Singleton instance
orchestrator = AgentOrchestrator()
