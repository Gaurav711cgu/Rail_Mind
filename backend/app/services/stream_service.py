"""Redis Streams client with in-memory fallback when Redis is unavailable."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine, Dict, List, Optional

from app.config import settings


class StreamService:
    def __init__(self) -> None:
        self._redis: Any = None
        self._redis_available = False
        self._memory_streams: Dict[str, List[Dict[str, Any]]] = {}

    async def connect(self) -> None:
        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            await self._redis.ping()
            self._redis_available = True
        except Exception as exc:
            print(f"[StreamService] Redis unavailable, using in-memory fallback: {exc}")
            self._redis = None
            self._redis_available = False

    async def disconnect(self) -> None:
        if self._redis is not None:
            await self._redis.close()
        self._redis = None
        self._redis_available = False

    async def publish(self, stream: str, payload: Dict[str, Any]) -> Optional[str]:
        if self._redis_available and self._redis is not None:
            return await self._redis.xadd(stream, payload)
        self._memory_streams.setdefault(stream, []).append(payload)
        return str(len(self._memory_streams[stream]))

    # ------------------------------------------------------------------ #
    #  Consumer helpers                                                    #
    # ------------------------------------------------------------------ #

    async def read_stream(
        self,
        stream: str,
        count: int = 10,
        block: int = 5000,
        last_id: str = "$",
    ) -> List:
        """
        Read new entries from a Redis Stream.

        When Redis is available, delegates to ``XREAD``.
        When offline, drains and returns events buffered in memory.
        """
        if self._redis_available and self._redis is not None:
            result = await self._redis.xread(
                {stream: last_id}, count=count, block=block
            )
            # xread returns [[stream_name, [(id, data), ...]]]
            if result:
                return result[0][1]  # list of (id, data) tuples
            return []

        # In-memory fallback: drain the buffer and return what's there
        events = self._memory_streams.get(stream, [])
        if events:
            batch = events[:count]
            self._memory_streams[stream] = events[count:]
            return [(str(i), ev) for i, ev in enumerate(batch)]
        return []

    async def start_consumer(
        self,
        callback: Callable[[List], Coroutine],
    ) -> None:
        """
        Continuously read from the telemetry positions stream and invoke
        *callback* for each batch of events.  Runs forever until cancelled.
        """
        stream = settings.REDIS_STREAM_POSITIONS
        last_id = "0-0"  # start from the beginning for a new consumer

        while True:
            try:
                events = await self.read_stream(
                    stream, count=10, block=5000, last_id=last_id
                )
                if events:
                    await callback(events)
                    # advance cursor to last consumed id
                    last_id = events[-1][0]
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                print(f"[StreamService] consumer error: {exc}")
                await asyncio.sleep(1)


stream_service = StreamService()
