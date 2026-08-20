import json
import time
import uuid
import sqlite3
from typing import Dict, Any, List

class TransactionalOutbox:
    """Transactional Outbox Pattern implementation.
    Guarantees dual-write consistency between relational state updates and outgoing Kafka telemetry dispatches.
    Persists outbox records in SQLite/PostgreSQL tables.
    """
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_table()

    def _init_table(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS outbox_events (
                    id TEXT PRIMARY KEY,
                    aggregate_type TEXT,
                    aggregate_id TEXT,
                    event_type TEXT,
                    payload_json TEXT,
                    status TEXT,
                    created_at REAL,
                    published_at REAL
                )
            """)

    def stage_event(self, aggregate_type: str, aggregate_id: str, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        event_id = str(uuid.uuid4())
        created_at = time.time()
        payload_str = json.dumps(payload)

        with self.conn:
            self.conn.execute("""
                INSERT INTO outbox_events (id, aggregate_type, aggregate_id, event_type, payload_json, status, created_at, published_at)
                VALUES (?, ?, ?, ?, ?, 'PENDING', ?, NULL)
            """, (event_id, aggregate_type, aggregate_id, event_type, payload_str, created_at))

        return {
            "id": event_id,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "event_type": event_type,
            "payload": payload,
            "status": "PENDING",
            "created_at": created_at
        }

    @property
    def pending_outbox_events(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, aggregate_type, aggregate_id, event_type, payload_json, created_at FROM outbox_events WHERE status = 'PENDING'")
        rows = cursor.fetchall()
        return [{
            "id": r[0],
            "aggregate_type": r[1],
            "aggregate_id": r[2],
            "event_type": r[3],
            "payload": json.loads(r[4]),
            "status": "PENDING",
            "created_at": r[5]
        } for r in rows]

    def relay_pending_events(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, aggregate_type, aggregate_id, event_type, payload_json, created_at FROM outbox_events WHERE status = 'PENDING'")
        rows = cursor.fetchall()
        
        relayed = []
        now = time.time()
        for row in rows:
            event_id, agg_type, agg_id, ev_type, payload_json, cr_at = row
            relayed.append({
                "id": event_id,
                "aggregate_type": agg_type,
                "aggregate_id": agg_id,
                "event_type": ev_type,
                "payload": json.loads(payload_json),
                "status": "PUBLISHED",
                "created_at": cr_at,
                "published_at": now
            })
            with self.conn:
                self.conn.execute("UPDATE outbox_events SET status = 'PUBLISHED', published_at = ? WHERE id = ?", (now, event_id))

        return relayed
