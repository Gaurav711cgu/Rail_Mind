import logging
from typing import Dict, Any

logger = logging.getLogger("RailMind.BackpressureController")

class BackpressureController:
    """Lag-aware Kafka consumer backpressure controller.
    Monitors consumer lag and dynamically pauses/resumes non-critical telemetry streams
    to prevent memory bloat during GraphSAGE delay cascade inference spikes.
    """
    def __init__(self, high_watermark_lag: int = 5000, low_watermark_lag: int = 1000):
        self.high_watermark_lag = high_watermark_lag
        self.low_watermark_lag = low_watermark_lag
        self.is_paused = False

    def evaluate_lag(self, current_lag: int) -> Dict[str, Any]:
        if current_lag >= self.high_watermark_lag and not self.is_paused:
            self.is_paused = True
            logger.warning(f"Consumer lag high ({current_lag} > {self.high_watermark_lag}). Triggering BACKPRESSURE PAUSE.")
            return {"action": "PAUSE", "lag": current_lag, "is_paused": True}
        elif current_lag <= self.low_watermark_lag and self.is_paused:
            self.is_paused = False
            logger.info(f"Consumer lag recovered ({current_lag} < {self.low_watermark_lag}). Triggering BACKPRESSURE RESUME.")
            return {"action": "RESUME", "lag": current_lag, "is_paused": False}
        
        return {"action": "NONE", "lag": current_lag, "is_paused": self.is_paused}
