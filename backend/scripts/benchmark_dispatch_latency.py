"""Benchmark RailMind dispatch decision latency against a FIFO baseline.

This measures compute latency only: how long each resolver takes to produce a
dispatch decision for the same generated conflict set. It does not claim an
operational delay-minute reduction.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import io
import json
import logging
import statistics
import sys
import time
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.dispatch_agent import DispatchAgent
from app.config import settings


def generate_synthetic_conflicts(count: int = 200) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    sections = [("NDLS", "GZB"), ("GZB", "ALJN"), ("ALJN", "CNB"), ("BRC", "MMCT")]
    passenger_names = ["SHATABDI", "RAJDHANI", "VANDE BHARAT", "DURONTO"]

    for i in range(count):
        section_from, section_to = sections[i % len(sections)]
        passenger_delay = 18 + ((i * 7) % 62)
        freight_delay = 8 + ((i * 5) % 45)
        disruption_type = "DELAY_CASCADE"
        if i % 41 == 0:
            disruption_type = "SIGNAL_FAILURE"
        elif i % 29 == 0:
            disruption_type = "TRACK_FAULT"

        trains = [
            {
                "train_no": f"{12000 + i}",
                "train_name": passenger_names[i % len(passenger_names)],
                "train_type": "PASSENGER",
                "current_delay": passenger_delay,
                "current_station": section_from,
                "status": "DELAYED" if passenger_delay > 20 else "RUNNING",
            },
            {
                "train_no": f"BOXN-{900 + i}",
                "train_name": "Coal Freight",
                "train_type": "FREIGHT",
                "current_delay": freight_delay,
                "current_station": section_from,
                "status": "DELAYED" if freight_delay > 20 else "RUNNING",
            },
        ]

        conflicts.append(
            {
                "trains": trains,
                "disruptions": [
                    {
                        "id": f"bench-{i:03d}",
                        "train_no": trains[0]["train_no"],
                        "section_from": section_from,
                        "section_to": section_to,
                        "disruption_type": disruption_type,
                        "severity": "CRITICAL" if disruption_type != "DELAY_CASCADE" else "HIGH",
                        "cascade_depth": 1 + (i % 4),
                        "passengers_affected": 300 + (i * 37) % 4500,
                    }
                ],
                "recommendations": [],
                "audit_entries": [],
                "audit_chain": [],
                "logs": [],
                "outbox_events": [],
                "escalated": False,
                "step": i,
            }
        )

    return conflicts


def resolve_fifo(conflict: dict[str, Any]) -> dict[str, Any]:
    trains = conflict["trains"]
    first_train = trains[0] if trains else {"train_no": "UNKNOWN"}
    disruption = conflict["disruptions"][0]
    return {
        "type": "PROCEED",
        "target_train": first_train["train_no"],
        "target_section": f"{disruption['section_from']}-{disruption['section_to']}",
        "reasoning": "FIFO baseline: first train in conflict set proceeds first.",
    }


async def resolve_railmind(agent: DispatchAgent, conflict: dict[str, Any]) -> dict[str, Any]:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        updates, confidence, reasoning = await agent.process(conflict)
    recommendation = (updates.get("recommendations") or [{}])[-1]
    return {
        "type": recommendation.get("type", "NONE"),
        "target_train": recommendation.get("target_train"),
        "confidence": confidence,
        "reasoning": reasoning,
    }


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    index = min(int(round((pct / 100.0) * (len(ordered) - 1))), len(ordered) - 1)
    return ordered[index]


async def run_benchmark(count: int) -> dict[str, Any]:
    # Force deterministic fallback so benchmark results do not depend on network
    # availability or LLM provider latency.
    settings.ANTHROPIC_API_KEY = ""
    logging.getLogger("app.agents.dispatch_agent").disabled = True
    agent = DispatchAgent()
    conflicts = generate_synthetic_conflicts(count)

    fifo_times: list[float] = []
    railmind_times: list[float] = []

    # Warm-up to avoid first-call import/object effects.
    resolve_fifo(conflicts[0])
    await resolve_railmind(agent, conflicts[0])

    for conflict in conflicts:
        t0 = time.perf_counter()
        resolve_fifo(conflict)
        fifo_times.append((time.perf_counter() - t0) * 1000.0)

    for conflict in conflicts:
        t0 = time.perf_counter()
        await resolve_railmind(agent, conflict)
        railmind_times.append((time.perf_counter() - t0) * 1000.0)

    fifo_median = statistics.median(fifo_times)
    railmind_median = statistics.median(railmind_times)
    latency_reduction_pct = ((fifo_median - railmind_median) / fifo_median) * 100.0

    return {
        "benchmark": "dispatch_decision_latency",
        "sample_size": count,
        "baseline": "FIFO",
        "candidate": "RailMind DispatchAgent deterministic fallback",
        "unit": "milliseconds",
        "fifo_median_ms": round(fifo_median, 6),
        "railmind_median_ms": round(railmind_median, 6),
        "latency_reduction_pct": round(latency_reduction_pct, 3),
        "fifo_p95_ms": round(percentile(fifo_times, 95), 6),
        "railmind_p95_ms": round(percentile(railmind_times, 95), 6),
        "note": (
            "Negative latency_reduction_pct means RailMind is slower than FIFO "
            "in compute latency. This benchmark does not measure operational "
            "delay-minute savings."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    result = asyncio.run(run_benchmark(args.count))
    rendered = json.dumps(result, indent=2)
    print(rendered)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
