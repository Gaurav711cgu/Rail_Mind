from typing import Dict, Any, Optional

# Performance & Startup Metrics
startup_time: Optional[float] = None
request_metrics: Dict[str, Any] = {
    "total_requests": 0,
    "avg_latency_ms": 0.0,
    "p99_latency_ms": 0.0,
    "_latencies": [],
}
