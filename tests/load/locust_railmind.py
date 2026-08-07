"""
Locust Load Test Suite for RailMind Real-Time Telemetry & Dispatch API.
Simulates 500 concurrent train telemetry updates under heavy load.

Target SLA:
  - 500 Concurrent Virtual Users
  - p95 Response Time < 200ms
  - 0% Error Rate
"""

import random
from locust import HttpUser, task, between


TRAIN_IDS = [f"12951_{i}" for i in range(1, 100)]
STATION_CODES = ["NDLS", "BCT", "CNB", "ALD", "HWH", "SBC", "MAS", "ADI"]


class RailMindLoadTester(HttpUser):
    wait_time = between(0.1, 0.5)  # 100ms to 500ms pacing between requests

    @task(3)
    def predict_cascade(self):
        train_id = random.choice(TRAIN_IDS)
        station = random.choice(STATION_CODES)
        delay = random.randint(5, 45)

        payload = {
            "train_id": train_id,
            "station_code": station,
            "delay_minutes": delay,
            "disruption_type": "SIGNAL_FAILURE",
        }

        self.client.post("/api/v1/cascade/predict", json=payload, name="/api/v1/cascade/predict")

    @task(2)
    def get_dispatch_recommendation(self):
        train_id = random.choice(TRAIN_IDS)

        self.client.get(f"/api/v1/recommendations/{train_id}", name="/api/v1/recommendations/{train_id}")

    @task(1)
    def get_health_metrics(self):
        self.client.get("/health", name="/health")
