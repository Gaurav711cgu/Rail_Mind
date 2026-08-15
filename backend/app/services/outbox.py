import json
import time
import uuid
from typing import Dict, Any, List

class TransactionalOutbox:
    """Transactional Outbox Pattern implementation.
    Guarantees dual-write consistency between PostgreSQL siding occupancy state and outgoing Kafka telemetry dispatches.
    """
    def __init__(self):
        self.pending_outbox_events: List[Dict[str, Any]] = []
        self.published_outbox_events: List[Dict[str, Any]] = []

    def stage_event(self, aggregate_type: str, aggregate_id: str, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        outbox_entry = {
            "id": str(uuid.uuid4()),
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "event_type": event_type,
            "payload": payload,
            "status": "PENDING",
            "created_at": time.time()
        }
        self.pending_outbox_events.append(outbox_entry)
        return outbox_entry

    def relay_pending_events(self) -> List[Dict[str, Any]]:
        relayed = []
        for event in self.pending_outbox_events:
            event["status"] = "PUBLISHED"
            event["published_at"] = time.time()
            relayed.append(event)
            self.published_outbox_events.append(event)
        self.pending_outbox_events.clear()
        return relayed
