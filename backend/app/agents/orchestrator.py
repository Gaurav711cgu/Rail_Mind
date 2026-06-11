"""
Agent Orchestrator — LangGraph StateGraph implementation.

Graph topology:
    monitor → conflict_detect → cascade_predict → dispatch → notify → audit → END

Conditional routing:
    - cascade_predict → dispatch   (normal path)
    - cascade_predict → notify     (if already escalated — skip auto-dispatch)
    - dispatch → notify            (always)
    - dispatch → audit             (if confidence < threshold, skip notify for speed)
"""

import asyncio
import logging
from typing import Annotated, Any, Dict, List, TypedDict
import operator

from langgraph.graph import StateGraph, END

from app.agents.monitor_agent import MonitorAgent
from app.agents.conflict_detector import ConflictDetector
from app.agents.cascade_predictor import CascadePredictor
from app.agents.dispatch_agent import DispatchAgent
from app.agents.notification_agent import NotificationAgent
from app.agents.audit_agent import AuditAgent
from app.services.stream_service import stream_service
from app.config import settings

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  Shared state schema (TypedDict with LangGraph reducers)                    #
# --------------------------------------------------------------------------- #
class AgentState(TypedDict):
    trains: List[Dict[str, Any]]
    disruptions: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    audit_entries: List[Dict[str, Any]]
    audit_chain: List[Dict[str, Any]]
    # Annotated with operator.add means LangGraph appends, never overwrites
    logs: Annotated[List[str], operator.add]
    escalated: bool
    step: int
    timestamp: str


# --------------------------------------------------------------------------- #
#  Node wrappers — each node calls the corresponding agent                    #
# --------------------------------------------------------------------------- #
_monitor = MonitorAgent()
_conflict = ConflictDetector()
_cascade = CascadePredictor()
_dispatch = DispatchAgent()
_notification = NotificationAgent()
_audit = AuditAgent()


def _update_health(agent_name: str, status: str, confidence: float = 1.0, error: str = None):
    import datetime

    try:
        orchestrator.agent_health[agent_name].update(
            {
                "last_run": datetime.datetime.utcnow().isoformat(),
                "last_confidence": confidence,
                "status": status,
                "last_error": error,
            }
        )
    except Exception:
        pass


async def _node_monitor(state: AgentState) -> Dict[str, Any]:
    try:
        _update_health("MonitorAgent", "running")
        updates, confidence, reasoning = await _monitor.process(state)
        _update_health("MonitorAgent", "healthy", confidence)
        log = f"[MonitorAgent] conf={confidence:.2f} | {reasoning}"
        await stream_service.publish(
            settings.REDIS_STREAM_POSITIONS,
            {
                "agent": "MonitorAgent",
                "confidence": confidence,
                "reasoning": reasoning,
                **{k: v for k, v in updates.items() if k != "trains"},
            },
        )
        return {**updates, "logs": [log]}
    except Exception as exc:
        _update_health("MonitorAgent", "degraded", error=str(exc))
        raise


async def _node_conflict(state: AgentState) -> Dict[str, Any]:
    try:
        _update_health("ConflictDetector", "running")
        updates, confidence, reasoning = await _conflict.process(state)
        _update_health("ConflictDetector", "healthy", confidence)
        log = f"[ConflictDetector] conf={confidence:.2f} | {reasoning}"
        if updates.get("disruptions"):
            await stream_service.publish(
                settings.REDIS_STREAM_DISRUPTIONS,
                {
                    "agent": "ConflictDetector",
                    "disruptions": updates["disruptions"],
                    "confidence": confidence,
                },
            )
        return {**updates, "logs": [log]}
    except Exception as exc:
        _update_health("ConflictDetector", "degraded", error=str(exc))
        raise


async def _node_cascade(state: AgentState) -> Dict[str, Any]:
    try:
        _update_health("CascadePredictor", "running")
        updates, confidence, reasoning = await _cascade.process(state)
        _update_health("CascadePredictor", "healthy", confidence)
        log = f"[CascadePredictor] conf={confidence:.2f} | {reasoning}"
        return {**updates, "logs": [log]}
    except Exception as exc:
        _update_health("CascadePredictor", "degraded", error=str(exc))
        raise


async def _node_dispatch(state: AgentState) -> Dict[str, Any]:
    try:
        _update_health("DispatchAgent", "running")
        updates, confidence, reasoning = await _dispatch.process(state)
        _update_health("DispatchAgent", "healthy", confidence)
        log = f"[DispatchAgent] conf={confidence:.2f} | {reasoning}"
        if updates.get("recommendations"):
            await stream_service.publish(
                settings.REDIS_STREAM_RECOMMENDATIONS,
                {
                    "agent": "DispatchAgent",
                    "recommendations": updates.get("recommendations", []),
                    "confidence": confidence,
                },
            )
        return {**updates, "logs": [log]}
    except Exception as exc:
        _update_health("DispatchAgent", "degraded", error=str(exc))
        raise


async def _node_notify(state: AgentState) -> Dict[str, Any]:
    try:
        _update_health("NotificationAgent", "running")
        updates, confidence, reasoning = await _notification.process(state)
        _update_health("NotificationAgent", "healthy", confidence)
        log = f"[NotificationAgent] conf={confidence:.2f} | {reasoning}"
        return {**updates, "logs": [log]}
    except Exception as exc:
        _update_health("NotificationAgent", "degraded", error=str(exc))
        raise


async def _node_audit(state: AgentState) -> Dict[str, Any]:
    try:
        _update_health("AuditAgent", "running")
        updates, confidence, reasoning = await _audit.process(state)
        _update_health("AuditAgent", "healthy", confidence)
        log = f"[AuditAgent] conf={confidence:.2f} | {reasoning}"
        if updates.get("audit_entries"):
            await stream_service.publish(
                settings.REDIS_STREAM_AUDIT,
                {
                    "agent": "AuditAgent",
                    "entries_added": len(updates.get("audit_entries", [])),
                },
            )
        return {**updates, "logs": [log]}
    except Exception as exc:
        _update_health("AuditAgent", "degraded", error=str(exc))
        raise


# --------------------------------------------------------------------------- #
#  Conditional routing                                                         #
# --------------------------------------------------------------------------- #
def _route_after_cascade(state: AgentState) -> str:
    """
    If the pipeline has already been escalated before reaching dispatch,
    skip dispatch and go directly to notify → audit.
    """
    if state.get("escalated"):
        return "notify"
    return "dispatch"


# --------------------------------------------------------------------------- #
#  Build the LangGraph                                                         #
# --------------------------------------------------------------------------- #
def _build_graph() -> Any:
    workflow = StateGraph(AgentState)

    workflow.add_node("monitor", _node_monitor)
    workflow.add_node("conflict_detect", _node_conflict)
    workflow.add_node("cascade_predict", _node_cascade)
    workflow.add_node("dispatch", _node_dispatch)
    workflow.add_node("notify", _node_notify)
    workflow.add_node("audit", _node_audit)

    workflow.set_entry_point("monitor")
    workflow.add_edge("monitor", "conflict_detect")
    workflow.add_edge("conflict_detect", "cascade_predict")
    workflow.add_conditional_edges(
        "cascade_predict",
        _route_after_cascade,
        {"dispatch": "dispatch", "notify": "notify"},
    )
    workflow.add_edge("dispatch", "notify")
    workflow.add_edge("notify", "audit")
    workflow.add_edge("audit", END)

    return workflow.compile()


_graph = _build_graph()


# --------------------------------------------------------------------------- #
#  Public interface                                                            #
# --------------------------------------------------------------------------- #
class AgentOrchestrator:
    """
    Wraps the compiled LangGraph.
    Provides run_pipeline() for explicit invocations (scenario mode)
    and a continuous background loop for real-time monitoring.
    """

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
        self.pipeline = [_monitor, _conflict, _cascade, _dispatch, _notification, _audit]
        self.agent_health = {
            agent.agent_name: {
                "last_run": None,
                "last_confidence": 1.0,
                "status": "healthy",
                "last_error": None,
            }
            for agent in self.pipeline
        }

    async def run_pipeline(self, initial_state: Any) -> Dict[str, Any]:
        """Run the full agent graph once and return the final state."""
        import datetime

        state: AgentState = {
            "trains": initial_state.get("trains", []),
            "disruptions": initial_state.get("disruptions", []),
            "recommendations": initial_state.get("recommendations", []),
            "audit_entries": initial_state.get("audit_entries", []),
            "audit_chain": initial_state.get("audit_chain", []),
            "logs": initial_state.get("logs", []),
            "escalated": initial_state.get("escalated", False),
            "step": initial_state.get("step", 0),
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

        try:
            result = await _graph.ainvoke(state)
            return dict(result)
        except Exception as exc:
            logger.error("[Orchestrator] Pipeline error: %s", exc, exc_info=True)
            state["logs"] = state.get("logs", []) + [f"[Orchestrator] ERROR: {exc}"]
            return dict(state)

    async def start(self) -> None:
        """Start the background monitoring loop (real-time mode)."""
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("[Orchestrator] Background monitoring loop started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[Orchestrator] Background monitoring loop stopped")

    async def _monitor_loop(self) -> None:
        """
        Polls every AGENT_MONITOR_POLL_INTERVAL_SEC seconds.
        In SCENARIO_MODE this is effectively a no-op (scenario steps are
        triggered explicitly via the /cascade/scenario/next endpoint).
        In live mode this drives the real-time agent pipeline.
        """
        import datetime
        from app.config import settings as cfg

        while self._running:
            try:
                if not cfg.SCENARIO_MODE:
                    state: AgentState = {
                        "trains": [],
                        "disruptions": [],
                        "recommendations": [],
                        "audit_entries": [],
                        "audit_chain": [],
                        "logs": [],
                        "escalated": False,
                        "step": 0,
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                    }
                    await self.run_pipeline(state)
            except Exception as exc:
                logger.warning("[Orchestrator] Monitor loop error: %s", exc)

            await asyncio.sleep(cfg.AGENT_MONITOR_POLL_INTERVAL_SEC)


# Singleton
orchestrator = AgentOrchestrator()
