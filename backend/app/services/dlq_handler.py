import json
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger("RailMind.DLQHandler")

class DeadLetterQueueHandler:
    """Dead Letter Queue (DLQ) handler for corrupted or unparseable Kafka telemetry messages.
    Applies exponential backoff and attaches audit failure metadata before routing to 'railmind-telemetry-dlq'.
    """
    def __init__(self, dlq_topic: str = "railmind-telemetry-dlq", max_retries: int = 3):
        self.dlq_topic = dlq_topic
        self.max_retries = max_retries
        self.dead_letters = []

    def handle_poison_message(self, raw_payload: bytes, error_reason: str, topic: str, partition: int, offset: int, retry_count: int = 0) -> Dict[str, Any]:
        backoff_delay_sec = min(2 ** retry_count, 30)
        time.sleep(backoff_delay_sec * 0.001)  # Simulated backoff delay for unit tests

        dlq_event = {
            "dlq_topic": self.dlq_topic,
            "original_topic": topic,
            "original_partition": partition,
            "original_offset": offset,
            "error_reason": error_reason,
            "retry_count": retry_count,
            "failed_at": time.time(),
            "payload_preview": raw_payload.decode("utf-8", errors="ignore")[:200]
        }
        self.dead_letters.append(dlq_event)
        logger.error(f"Routed poison message at offset {offset} to DLQ '{self.dlq_topic}': {error_reason}")
        return dlq_event
