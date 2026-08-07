"""
RailMind Sliding Window Stream Processor.
Buffers incoming train telemetry events across sliding time windows and triggers
GraphSAGE GNN cascade re-evaluations whenever delay deltas exceed operational thresholds.
"""

import asyncio
import logging
import time
from collections import deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SlidingWindowStreamProcessor:
    """
    Sliding window buffer for real-time train telemetry.
    Aggregates per-train state and detects delay cascades.
    """

    def __init__(self, window_size_sec: float = 300.0, delay_trigger_threshold_min: float = 5.0):
        self.window_size_sec = window_size_sec
        self.delay_trigger_threshold_min = delay_trigger_threshold_min

        # Sliding window buffer: deque of (timestamp, event_data)
        self._window: deque = deque()
        self._train_last_delay: Dict[str, float] = {}

    def push_event(self, event: Dict[str, Any]) -> bool:
        """
        Pushes a new telemetry event into the sliding window.
        Returns True if the event triggers a GNN cascade re-evaluation.
        """
        now = time.time()
        self._window.append((now, event))

        # Evict expired events outside sliding window
        cutoff = now - self.window_size_sec
        while self._window and self._window[0][0] < cutoff:
            self._window.popleft()

        train_id = str(event.get("train_id", ""))
        current_delay = float(event.get("delay_minutes", 0.0))

        # Calculate delay delta since last recorded state
        last_delay = self._train_last_delay.get(train_id, 0.0)
        delay_delta = abs(current_delay - last_delay)
        self._train_last_delay[train_id] = current_delay

        # Trigger condition: delay changed by more than threshold (e.g., 5+ minutes)
        if delay_delta >= self.delay_trigger_threshold_min:
            logger.info(
                f"Stream trigger fired for Train {train_id}: "
                f"delay delta {delay_delta:.1f}m >= threshold {self.delay_trigger_threshold_min}m"
            )
            return True

        return False

    def get_active_train_count(self) -> int:
        """Returns unique train count within current sliding window."""
        active_trains = {event.get("train_id") for _, event in self._window if event.get("train_id")}
        return len(active_trains)

    def get_window_snapshot(self) -> List[Dict[str, Any]]:
        """Returns snapshot of all events in active sliding window."""
        return [event for _, event in self._window]
