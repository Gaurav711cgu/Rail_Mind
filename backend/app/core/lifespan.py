from contextlib import asynccontextmanager
import asyncio
import time
from fastapi import FastAPI

from app.db.database import init_db
from app.db.seed import seed_topology
from app.services.stream_service import stream_service
from app.agents.orchestrator import orchestrator
from app.core import state

@asynccontextmanager
async def lifespan(app: FastAPI):
    state.startup_time = time.time()

    # 1. Database
    print("[Lifespan] Initialising database schema...")
    await init_db()

    # 2. Redis Streams
    print("[Lifespan] Connecting to Redis Streams...")
    await stream_service.connect()

    # 3. Seed topology once
    await seed_topology()

    # 4. Start Redis stream consumer (background task)
    async def _on_telemetry_events(events):
        """Process telemetry events from the Redis stream."""
        for event_id, data in events:
            print(f"[StreamConsumer] event {event_id}: {data}")

    consumer_task = asyncio.create_task(stream_service.start_consumer(_on_telemetry_events))
    print("[Lifespan] Redis stream consumer started.")

    outbox_task = asyncio.create_task(stream_service.start_outbox_worker())
    print("[Lifespan] Transactional Outbox Worker started.")

    # 5. Start agent background monitoring loop
    print("[Lifespan] Starting agent orchestrator...")
    await orchestrator.start()

    print("[Lifespan] RailMind engine ready.")
    yield

    # Shutdown
    print("[Lifespan] Shutting down...")
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    outbox_task.cancel()
    try:
        await outbox_task
    except asyncio.CancelledError:
        pass
        
    await orchestrator.stop()
    await stream_service.disconnect()
    print("[Lifespan] Clean shutdown complete.")
