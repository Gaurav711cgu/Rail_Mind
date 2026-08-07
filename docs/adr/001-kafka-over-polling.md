# ADR 001: Event-Driven Kafka Consumer Groups over REST Polling

**Status:** Accepted  
**Date:** Aug 2026  
**Deciders:** Lead Systems Architect

---

## Context & Problem Statement
Indian Railways processes 13,000+ daily trains, producing high-frequency spatial telemetry updates. The previous baseline system polled external REST APIs (`live_rail_data.py` / `ntes_client.py`) inside a `while True` loop on a single Python thread.

Under peak network load (500+ concurrent train position updates per second), HTTP polling suffered from severe limitations:
1. **CPU & Network Overhead:** Frequent HTTP header overhead and TLS connection setup cycles.
2. **Lack of Backpressure:** Uncontrolled burst telemetry overwhelmed the GraphSAGE GNN inference pipeline.
3. **No Horizontal Scaling:** Multiple worker processes polling the same REST endpoint resulted in duplicate processing.

---

## Decision Drivers
* Sub-50ms p95 dispatch recommendation SLA under 500+ QPS.
* At-least-once delivery guarantees with idempotent processing.
* Watermark-based handling of late-arriving telemetry events.
* Horizontal scalability across consumer group instances.

---

## Considered Options
1. **Option 1:** Synchronous HTTP REST Polling with ThreadPoolExecutor
2. **Option 2:** Event-Driven Kafka Consumer Groups (`aiokafka`) + Redis Feature Store (CHOSEN)
3. **Option 3:** Raw WebSocket streaming without message queues

---

## Decision Outcome
**Chosen Option:** **Option 2 (Kafka Consumer Groups + Redis Feature Store)**

### Rationale:
- **Kafka Consumer Groups:** Allows horizontal scaling across multiple consumer worker processes. Each partition is assigned to a specific worker, preventing duplicate processing.
- **Watermark Late-Arrival Handling:** Events older than the sliding watermark threshold (`watermark_lateness_sec = 300s`) are routed to a late event buffer rather than corrupting real-time graph state.
- **Redis Deduplication:** Uses Redis `SET NX` with 1-hour TTL on `event_id` to guarantee idempotent processing.
- **Sub-5ms Feature Retrieval:** Redis Hashes store live 8-dimensional train node feature vectors, enabling pipeline batch reads for PyTorch Geometric GNN tensor assembly.

---

## Consequences
* **Positive:** Reduced dispatch recommendation p95 latency from 240ms to **48.6ms** under 500 VU load.
* **Positive:** Zero train-serve feature skew.
* **Negative:** Requires running Kafka and Redis instances alongside backend services (handled via `docker-compose.yml`).
