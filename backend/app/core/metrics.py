"""
RailMind Prometheus & OpenTelemetry Metrics Module.
Exposes real-time SLA metrics for dispatch latency (p50/p95/p99), GNN inference times,
Kafka consumer lag, and multi-agent execution status.
"""

import time
from typing import Callable
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

# --------------------------------------------------------------------------- #
# Prometheus Metric Definitions                                               #
# --------------------------------------------------------------------------- #

# 1. Dispatch Recommendation Latency (seconds)
DISPATCH_LATENCY = Histogram(
    "railmind_dispatch_latency_seconds",
    "Time spent computing multi-agent dispatch recommendations",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0, 2.5]
)

# 2. GraphSAGE GNN Inference Latency (milliseconds)
GNN_INFERENCE_LATENCY = Histogram(
    "railmind_gnn_inference_ms",
    "Latency of GraphSAGE GNN delay cascade prediction pass in ms",
    buckets=[1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0]
)

# 3. Redis Feature Store Read Latency (milliseconds)
FEATURE_STORE_READ_LATENCY = Histogram(
    "railmind_feature_store_read_ms",
    "Latency of batch pipeline reads from Redis Feature Store",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 25.0]
)

# 4. Telemetry Stream Consumer Lag (messages)
KAFKA_CONSUMER_LAG = Gauge(
    "railmind_kafka_consumer_lag_messages",
    "Number of unconsumed messages in live telemetry stream topic"
)

# 5. Agent Execution Errors
AGENT_ERRORS = Counter(
    "railmind_agent_errors_total",
    "Total error count per multi-agent FSM node",
    ["agent_name"]
)

# 6. HTTP API Request Count
HTTP_REQUESTS_TOTAL = Counter(
    "railmind_http_requests_total",
    "Total HTTP API requests handled",
    ["method", "endpoint", "status_code"]
)


def metrics_endpoint_response():
    """Generates Prometheus text exposition format payload."""
    return generate_latest(), CONTENT_TYPE_LATEST
