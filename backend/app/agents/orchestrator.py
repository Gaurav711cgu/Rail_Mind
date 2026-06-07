from typing import Dict, Any, List
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
        # Register agents in the topology sequence
        self.pipeline = [
            MonitorAgent(),
            ConflictDetector(),
            CascadePredictor(),
            DispatchAgent(),
            NotificationAgent(),
            AuditAgent()
        ]

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
                updates, confidence, reasoning = await agent.process(state)
                
                # Apply updates to shared context state
                for key, val in updates.items():
                    state[key] = val
                    
                # Append log entry from agent execution
                log_msg = f"[{agent.agent_name}] Action completed. Confidence: {confidence:.2f}. Reasoning: {reasoning}"
                state["logs"].append(log_msg)
                
                # Check confidence threshold for escalation
                if confidence < 0.85 and agent.agent_name == "DispatchAgent":
                    state["escalated"] = True
                    state["logs"].append(f"[Orchestrator] Halted auto-execution. Escaled to local dispatcher controller.")
                    
            except Exception as e:
                err_msg = f"[Orchestrator] Error executing {agent.agent_name}: {str(e)}"
                state["logs"].append(err_msg)
                print(err_msg)
                
        state["logs"].append("[Orchestrator] Multi-agent execution cycle completed successfully.")
        return state

# Singleton instance
orchestrator = AgentOrchestrator()
