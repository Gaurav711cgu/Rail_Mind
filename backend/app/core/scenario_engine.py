import hashlib
import numpy as np
from typing import Dict, Any


class ScenarioEngine:
    def __init__(self):
        self.current_step = 0
        self.max_steps = 6
        self.scenario_name = "NDLS Signal Failure Delay Cascade"
        self._init_scenario_steps()

    def reset(self):
        self.current_step = 0
        return self.get_state()

    def next_step(self) -> int:
        if self.current_step < self.max_steps:
            self.current_step += 1
        return self.current_step

    def get_state(self) -> Dict[str, Any]:
        step_data = self.steps.get(self.current_step, self.steps[0])

        # Dynamically enrich step data with real model inference if available
        try:
            from app.ml.gnn_cascade import RailwayGNN
            import torch
            from pathlib import Path

            weights_path = Path(__file__).resolve().parent.parent / "ml" / "artifacts" / "gnn_cascade.pt"
            if weights_path.exists():
                checkpoint = torch.load(weights_path, map_location="cpu", weights_only=False)  # nosec B614
                model = RailwayGNN(**checkpoint.get("config", {}))
                model.load_state_dict(checkpoint["state_dict"])
                model.eval()

                x = torch.zeros((50, 8))
                edge_index = torch.zeros((2, 2), dtype=torch.long)
                edge_attr = torch.zeros((2, 6))

                # Inject train delays into GNN graph
                for t in step_data.get("trains", []):
                    st_id = sum(ord(c) for c in t.get("current_station", "NDLS")) % 50
                    x[st_id, 3] = float(t.get("current_delay", 0))

                with torch.no_grad():
                    res = model(x, edge_index, edge_attr, time_of_day=0.5)
                    probs = res["cascade_probability"].numpy() if isinstance(res, dict) else np.array([0.5] * 50)

                step_data["gnn_inference"] = {
                    "active_gnn_model": "RailwayGNN (GraphSAGE + GAT, 128-dim)",
                    "weights_file": "gnn_cascade.pt",
                    "max_cascade_probability": round(float(probs.max()), 4),
                    "mean_network_risk": round(float(probs.mean()), 4),
                }
        except Exception:
            pass

        return {
            "scenario_name": self.scenario_name,
            "step": self.current_step,
            "max_steps": self.max_steps,
            "title": step_data["title"],
            "description": step_data["description"],
            "trains": step_data["trains"],
            "disruptions": step_data["disruptions"],
            "recommendations": step_data["recommendations"],
            "logs": step_data["logs"],
            "audit_entries": step_data["audit_entries"],
            "gnn_inference": step_data.get("gnn_inference", None),
        }

    def _init_scenario_steps(self):
        # We will create pre-defined high-fidelity operational states for the demo
        self.steps = {}

        # Step 0: Nominal State
        self.steps[0] = {
            "title": "Nominal Operation — Sector North",
            "description": "All trains are running within standard operational thresholds. Signaling systems are normal. Kavach is active on the 100km Delhi-Agra corridor.",
            "trains": [
                {
                    "train_no": "12002",
                    "train_name": "NDLS-BCT Shatabdi Express",
                    "current_station": "NDLS",
                    "current_delay": 0,
                    "status": "BOARDING",
                    "latitude": 28.643,
                    "longitude": 77.222,
                },
                {
                    "train_no": "22415",
                    "train_name": "New Delhi-Varanasi Vande Bharat",
                    "current_station": "ALJN",
                    "current_delay": 0,
                    "status": "RUNNING",
                    "latitude": 27.892,
                    "longitude": 78.078,
                },
                {
                    "train_no": "BOXN-902",
                    "train_name": "Coal Freight Wagon",
                    "current_station": "GZB",
                    "current_delay": 5,
                    "status": "RUNNING",
                    "latitude": 28.672,
                    "longitude": 77.436,
                },
            ],
            "disruptions": [],
            "recommendations": [],
            "logs": [
                "[MonitorAgent] Ingestion check completed. 3 active trains tracked in Sector North.",
                "[ConflictDetector] No route conflicts detected. Capacity utilization: 34%.",
                "[AuditAgent] Nominal state snapshot verified. Hash chain matches signature.",
            ],
            "audit_entries": [],
        }

        # Step 1: Disruption Detected (Signal Failure)
        self.steps[1] = {
            "title": "Ingested Anomaly: NDLS Electronic Interlocking Signal Fault",
            "description": "An electronic interlocking failure occurs on the exit track of New Delhi (NDLS) station, trapping train 12002 (Shatabdi Express) at platform 3. Delay is climbing immediately.",
            "trains": [
                {
                    "train_no": "12002",
                    "train_name": "NDLS-BCT Shatabdi Express",
                    "current_station": "NDLS",
                    "current_delay": 25,
                    "status": "HELD",
                    "latitude": 28.643,
                    "longitude": 77.222,
                },
                {
                    "train_no": "22415",
                    "train_name": "New Delhi-Varanasi Vande Bharat",
                    "current_station": "ALJN",
                    "current_delay": 0,
                    "status": "RUNNING",
                    "latitude": 27.892,
                    "longitude": 78.078,
                },
                {
                    "train_no": "BOXN-902",
                    "train_name": "Coal Freight Wagon",
                    "current_station": "GZB",
                    "current_delay": 5,
                    "status": "RUNNING",
                    "latitude": 28.672,
                    "longitude": 77.436,
                },
            ],
            "disruptions": [
                {
                    "id": "disp-001",
                    "train_no": "12002",
                    "section_from": "NDLS",
                    "section_to": "GZB",
                    "disruption_type": "SIGNAL_FAILURE",
                    "severity": "MEDIUM",
                    "cascade_depth": 0,
                    "status": "ACTIVE",
                }
            ],
            "recommendations": [],
            "logs": [
                "[MonitorAgent] ANOMALY: Train 12002 departure delay exceeded 20m variance thresholds.",
                "[MonitorAgent] Source verified: Interlocking status code 0x4F (Red Alert).",
                "[ConflictDetector] Creating section disruption alert for route NDLS -> GZB.",
                "[AuditAgent] Logged disruption disp-001. Current Hash: " + self._hash("disp-001-step1"),
            ],
            "audit_entries": [
                {
                    "agent": "MonitorAgent",
                    "action": "ANOMALY_INGESTED",
                    "target": "12002",
                    "reasoning": "Train 12002 held at platform 3 due to exit interlocking failure. Delay: 25 min.",
                    "confidence": 1.0,
                    "hash": self._hash("disp-001-step1"),
                }
            ],
        }

        # Step 2: Route Conflict Detection
        self.steps[2] = {
            "title": "Conflict Identified: Shared Downstream Track Corridor",
            "description": "Conflict Detector Agent projects that the delayed Shatabdi Express (12002) will attempt to exit onto the same section (NDLS-GZB-ALJN) currently occupied by the Coal Freight (BOXN-902), leading to immediate safety blocking.",
            "trains": [
                {
                    "train_no": "12002",
                    "train_name": "NDLS-BCT Shatabdi Express",
                    "current_station": "NDLS",
                    "current_delay": 35,
                    "status": "HELD",
                    "latitude": 28.643,
                    "longitude": 77.222,
                },
                {
                    "train_no": "22415",
                    "train_name": "New Delhi-Varanasi Vande Bharat",
                    "current_station": "ALJN",
                    "current_delay": 0,
                    "status": "RUNNING",
                    "latitude": 27.892,
                    "longitude": 78.078,
                },
                {
                    "train_no": "BOXN-902",
                    "train_name": "Coal Freight Wagon",
                    "current_station": "GZB",
                    "current_delay": 10,
                    "status": "APPROACHING_CONFLICT",
                    "latitude": 28.672,
                    "longitude": 77.436,
                },
            ],
            "disruptions": [
                {
                    "id": "disp-001",
                    "train_no": "12002",
                    "section_from": "NDLS",
                    "section_to": "GZB",
                    "disruption_type": "SIGNAL_FAILURE",
                    "severity": "HIGH",
                    "cascade_depth": 1,
                    "status": "ACTIVE",
                }
            ],
            "recommendations": [],
            "logs": [
                "[ConflictDetector] Downstream path conflict calculated on GZB-ALJN section between 12002 and BOXN-902.",
                "[ConflictDetector] Overlap window: 19:40 - 20:15. P(conflict) = 0.94.",
                "[AuditAgent] Logged route conflict event. Current Hash: " + self._hash("conflict-step2"),
            ],
            "audit_entries": [
                {
                    "agent": "ConflictDetector",
                    "action": "CONFLICT_DETECTED",
                    "target": "GZB-ALJN Section",
                    "reasoning": "BOXN-902 occupancy conflicts with rescheduled 12002 path. Safety separation rules violated.",
                    "confidence": 0.94,
                    "hash": self._hash("conflict-step2"),
                }
            ],
        }

        # Step 3: Cascade Delay Prediction
        self.steps[3] = {
            "title": "Cascade Simulation: 5 Affected Downstream Trains",
            "description": "Cascade Predictor Agent runs a BFS timetable analysis. If the conflict is unresolved, the delay will cascade to Vande Bharat (22415) and 3 other passenger services. Impact: 4,800+ passengers, 180 total delay minutes.",
            "trains": [
                {
                    "train_no": "12002",
                    "train_name": "NDLS-BCT Shatabdi Express",
                    "current_station": "NDLS",
                    "current_delay": 40,
                    "status": "HELD",
                    "latitude": 28.643,
                    "longitude": 77.222,
                },
                {
                    "train_no": "22415",
                    "train_name": "New Delhi-Varanasi Vande Bharat",
                    "current_station": "ALJN",
                    "current_delay": 15,
                    "status": "DELAYED",
                    "latitude": 27.892,
                    "longitude": 78.078,
                },
                {
                    "train_no": "BOXN-902",
                    "train_name": "Coal Freight Wagon",
                    "current_station": "GZB",
                    "current_delay": 10,
                    "status": "APPROACHING_CONFLICT",
                    "latitude": 28.672,
                    "longitude": 77.436,
                },
            ],
            "disruptions": [
                {
                    "id": "disp-001",
                    "train_no": "12002",
                    "section_from": "NDLS",
                    "section_to": "ALJN",
                    "disruption_type": "DELAY_CASCADE",
                    "severity": "CRITICAL",
                    "cascade_depth": 3,
                    "status": "ACTIVE",
                }
            ],
            "recommendations": [],
            "logs": [
                "[CascadePredictor] Simulating delay transfer function across timetable nodes.",
                "[CascadePredictor] Predicted delay addition: 22415 (+15m), 12301 Rajdhani (+20m), 12560 Shramik (+45m).",
                "[CascadePredictor] Passenger volume analysis: estimated 4,820 passengers impacted by cumulative delays.",
                "[AuditAgent] Logged cascade model output. Current Hash: " + self._hash("cascade-step3"),
            ],
            "audit_entries": [
                {
                    "agent": "CascadePredictor",
                    "action": "CASCADE_PROJECTED",
                    "target": "Sector North Timetable",
                    "reasoning": "Delay propagates through 4 downstream services. Cumulative delay: 180 min.",
                    "confidence": 0.91,
                    "hash": self._hash("cascade-step3"),
                }
            ],
        }

        # Step 4: Dispatchhold recommendation & Escalation (Tier 2)
        self.steps[4] = {
            "title": "Dispatch Agent Action: Tier-2 Escalated Hold Recommendation",
            "description": "Dispatch Agent recommends holding Coal Freight (BOXN-902) at Aligarh (ALJN) loop line for 22 minutes. Confidence is 0.78, which is below the auto-execution threshold of 0.85. Escalating to human controller.",
            "trains": [
                {
                    "train_no": "12002",
                    "train_name": "NDLS-BCT Shatabdi Express",
                    "current_station": "NDLS",
                    "current_delay": 40,
                    "status": "PROCEEDING",
                    "latitude": 28.643,
                    "longitude": 77.222,
                },
                {
                    "train_no": "22415",
                    "train_name": "New Delhi-Varanasi Vande Bharat",
                    "current_station": "ALJN",
                    "current_delay": 15,
                    "status": "DELAYED",
                    "latitude": 27.892,
                    "longitude": 78.078,
                },
                {
                    "train_no": "BOXN-902",
                    "train_name": "Coal Freight Wagon",
                    "current_station": "GZB",
                    "current_delay": 10,
                    "status": "HELD_AT_LOOP",
                    "latitude": 28.672,
                    "longitude": 77.436,
                },
            ],
            "disruptions": [
                {
                    "id": "disp-001",
                    "train_no": "12002",
                    "section_from": "NDLS",
                    "section_to": "ALJN",
                    "disruption_type": "DELAY_CASCADE",
                    "severity": "CRITICAL",
                    "cascade_depth": 3,
                    "status": "ACTIVE",
                }
            ],
            "recommendations": [
                {
                    "id": "rec-001",
                    "disruption_id": "disp-001",
                    "type": "HOLD",
                    "target_train": "BOXN-902",
                    "target_section": "GZB-ALJN loop line",
                    "reasoning": "Hold Coal Freight (BOXN-902) to clear track block for high-priority Shatabdi 12002. Reduces net cascade delay by 120 minutes. Escalated due to manual check rule on freight priorities.",
                    "confidence": 0.78,
                    "tier": 2,
                    "is_approved": False,
                }
            ],
            "logs": [
                "[DispatchAgent] Invoking Claude Sonnet hold-proceed resolution model.",
                "[DispatchAgent] Optimal hold target identified: BOXN-902 at GZB loop line.",
                "[DispatchAgent] Confidence score 0.78 < threshold 0.85. Triggering manual Tier-2 Escalation Alert.",
                "[AuditAgent] Logged dispatch recommendation rec-001. Current Hash: " + self._hash("dispatch-step4"),
            ],
            "audit_entries": [
                {
                    "agent": "DispatchAgent",
                    "action": "RECOMMENDATION_ISSUED",
                    "target": "rec-001",
                    "reasoning": "Escalated HOLD recommendation issued for BOXN-902. Waiting for human controller approval.",
                    "confidence": 0.78,
                    "hash": self._hash("dispatch-step4"),
                }
            ],
        }

        # Step 5: Passenger Rerouting & Advisories
        self.steps[5] = {
            "title": "Advisory Issued: Passenger Rerouting with RAC Confirmation Probabilities",
            "description": "Notification Agent intercepts passenger records. Generates alternative route guidance via Vande Bharat (22415) with an ML-calculated RAC confirmation probability of 88% to protect passenger schedules.",
            "trains": [
                {
                    "train_no": "12002",
                    "train_name": "NDLS-BCT Shatabdi Express",
                    "current_station": "GZB",
                    "current_delay": 40,
                    "status": "RUNNING",
                    "latitude": 28.672,
                    "longitude": 77.436,
                },
                {
                    "train_no": "22415",
                    "train_name": "New Delhi-Varanasi Vande Bharat",
                    "current_station": "ALJN",
                    "current_delay": 15,
                    "status": "DELAYED",
                    "latitude": 27.892,
                    "longitude": 78.078,
                },
                {
                    "train_no": "BOXN-902",
                    "train_name": "Coal Freight Wagon",
                    "current_station": "ALJN",
                    "current_delay": 32,
                    "status": "HELD_AT_LOOP",
                    "latitude": 27.892,
                    "longitude": 78.078,
                },
            ],
            "disruptions": [
                {
                    "id": "disp-001",
                    "train_no": "12002",
                    "section_from": "NDLS",
                    "section_to": "ALJN",
                    "disruption_type": "DELAY_CASCADE",
                    "severity": "CRITICAL",
                    "cascade_depth": 3,
                    "status": "ACTIVE",
                }
            ],
            "recommendations": [
                {
                    "id": "rec-001",
                    "disruption_id": "disp-001",
                    "type": "HOLD",
                    "target_train": "BOXN-902",
                    "target_section": "GZB-ALJN loop line",
                    "reasoning": "Hold Coal Freight (BOXN-902) to clear track block for high-priority Shatabdi 12002. Reduces net cascade delay by 120 minutes. Escalated due to manual check rule on freight priorities.",
                    "confidence": 0.78,
                    "tier": 2,
                    "is_approved": False,
                }
            ],
            "logs": [
                "[NotificationAgent] Generating rerouting advisories for 140 passengers stranded on NDLS corridors.",
                "[NotificationAgent] Calling RAC Predictor model to calculate confirmation chances for Vande Bharat 22415.",
                "[NotificationAgent] RAC Predictor returned confirmation score: 88.4%.",
                "[NotificationAgent] Advisory published. Disseminated to passenger panels.",
                "[AuditAgent] Logged rerouting advisories. Current Hash: " + self._hash("advisory-step5"),
            ],
            "audit_entries": [
                {
                    "agent": "NotificationAgent",
                    "action": "ADVISORY_ISSUED",
                    "target": "NDLS Corridor Passengers",
                    "reasoning": "Rerouted passengers to Vande Bharat 22415 with 88% RAC confirmation probability.",
                    "confidence": 0.90,
                    "hash": self._hash("advisory-step5"),
                }
            ],
        }

        # Step 6: Resolved (Manual approval)
        self.steps[6] = {
            "title": "Resolution: Section Controller Approves Recommendation",
            "description": "The human controller reviews the escalation and approves the HOLD recommendation. BOXN-902 stays in loop, Shatabdi 12002 exits the corridor, and the delay cascade is successfully mitigated. Punctuality index restored.",
            "trains": [
                {
                    "train_no": "12002",
                    "train_name": "NDLS-BCT Shatabdi Express",
                    "current_station": "ALJN",
                    "current_delay": 5,
                    "status": "RUNNING",
                    "latitude": 27.892,
                    "longitude": 78.078,
                },
                {
                    "train_no": "22415",
                    "train_name": "New Delhi-Varanasi Vande Bharat",
                    "current_station": "VGLJ",
                    "current_delay": 0,
                    "status": "RUNNING",
                    "latitude": 25.448,
                    "longitude": 78.568,
                },
                {
                    "train_no": "BOXN-902",
                    "train_name": "Coal Freight Wagon",
                    "current_station": "ALJN",
                    "current_delay": 32,
                    "status": "DEPARTING_LOOP",
                    "latitude": 27.892,
                    "longitude": 78.078,
                },
            ],
            "disruptions": [
                {
                    "id": "disp-001",
                    "train_no": "12002",
                    "section_from": "NDLS",
                    "section_to": "ALJN",
                    "disruption_type": "DELAY_CASCADE",
                    "severity": "LOW",
                    "cascade_depth": 0,
                    "status": "RESOLVED",
                }
            ],
            "recommendations": [
                {
                    "id": "rec-001",
                    "disruption_id": "disp-001",
                    "type": "HOLD",
                    "target_train": "BOXN-902",
                    "target_section": "GZB-ALJN loop line",
                    "reasoning": "Hold Coal Freight (BOXN-902) to clear track block for high-priority Shatabdi 12002. Reduces net cascade delay by 120 minutes. Escalated due to manual check rule on freight priorities.",
                    "confidence": 0.78,
                    "tier": 2,
                    "is_approved": True,
                }
            ],
            "logs": [
                "[DispatchAgent] Action Approved: Hold recommendation approved by User 'Controller_Northern'.",
                "[MonitorAgent] Verification: Shatabdi 12002 past GZB junction block. Speeds recovering.",
                "[ConflictDetector] No active section conflicts in corridor.",
                "[AuditAgent] Logged manual override/approval event. Audit chain successfully sealed.",
                "[AuditAgent] Final verification: chain validated successfully. 6/6 blocks verified.",
            ],
            "audit_entries": [
                {
                    "agent": "Controller_Northern",
                    "action": "ACTION_APPROVED",
                    "target": "rec-001",
                    "reasoning": "Approved hold for BOXN-902. Normalizing passenger traffic priority.",
                    "confidence": 1.0,
                    "hash": self._hash("resolved-step6"),
                }
            ],
        }

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


# Singleton instance
scenario_engine = ScenarioEngine()
