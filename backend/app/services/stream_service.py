"""Redis Streams client with in-memory fallback when Redis is unavailable."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.config import settings


class StreamService:
    def __init__(self) -> None:
        self._redis = None
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


stream_service = StreamService()
