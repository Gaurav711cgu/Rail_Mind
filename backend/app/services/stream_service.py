"""
Redis Streams service — event bus for inter-agent communication.

Streams used:
  railmind:stream:positions       — live train position events (MonitorAgent → all)
  railmind:stream:disruptions     — detected disruptions (ConflictDetector → CascadePredictor)
  railmind:stream:recommendations — dispatch recommendations (DispatchAgent → NotificationAgent)
  railmind:stream:audit           — all agent events (AuditAgent consumes)

Falls back to in-memory asyncio.Queue if Redis is unavailable (local dev without Redis).
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Callable, Coroutine

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  In-memory fallback queue (used when Redis is not reachable)                #
# --------------------------------------------------------------------------- #
_fallback_queues: Dict[str, asyncio.Queue] = {}
_fallback_history: Dict[str, List[Dict]] = {}


def _get_fallback(stream: str) -> asyncio.Queue:
    if stream not in _fallback_queues:
        _fallback_queues[stream] = asyncio.Queue(maxsize=500)
        _fallback_history[stream] = []
    return _fallback_queues[stream]


# --------------------------------------------------------------------------- #
#  StreamService                                                               #
# --------------------------------------------------------------------------- #
class StreamService:
    """
    Thin async wrapper around Redis Streams (XADD / XREVRANGE / XREAD).
    All values are JSON-serialised before storage and deserialised on read.
    """

    def __init__(self):
        self._client: Optional[aioredis.Redis] = None
        self._redis_available: bool = False

    async def connect(self) -> None:
        try:
            self._client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=3,
            )
            # Ping to verify connection
            await self._client.ping()
            self._redis_available = True
            logger.info("[StreamService] Connected to Redis at %s", settings.REDIS_URL)
        except Exception as exc:
            self._redis_available = False
            logger.warning(
                "[StreamService] Redis unavailable (%s). "
                "Using in-memory fallback queues.",
                exc,
            )

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()

    # ----------------------------------------------------------------------- #
    #  Publish                                                                  #
    # ----------------------------------------------------------------------- #
    async def publish(self, stream: str, payload: Dict[str, Any]) -> str:
        """
        Publish a dict to a Redis Stream. Returns the stream entry ID.
        Silently falls back to in-memory queue on Redis failure.
        """
        serialised = {"data": json.dumps(payload)}

        if self._redis_available and self._client:
            try:
                entry_id: str = await self._client.xadd(
                    stream,
                    serialised,
                    maxlen=1000,          # cap stream length to avoid unbounded growth
                    approximate=True,
                )
                return entry_id
            except Exception as exc:
                logger.warning("[StreamService] xadd failed: %s — falling back", exc)

        # In-memory fallback
        q = _get_fallback(stream)
        entry = {"id": f"mem-{len(_fallback_history[stream])}", **payload}
        _fallback_history[stream].append(entry)
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass  # Drop oldest if queue is saturated
        return entry["id"]

    # ----------------------------------------------------------------------- #
    #  Read latest N entries (for dashboard / API polling)                     #
    # ----------------------------------------------------------------------- #
    async def read_latest(
        self,
        stream: str,
        count: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Returns the most recent `count` entries from the stream, newest first.
        """
        if self._redis_available and self._client:
            try:
                raw = await self._client.xrevrange(stream, count=count)
                results = []
                for entry_id, fields in raw:
                    try:
                        data = json.loads(fields.get("data", "{}"))
                        data["_stream_id"] = entry_id
                        results.append(data)
                    except json.JSONDecodeError:
                        continue
                return results
            except Exception as exc:
                logger.warning("[StreamService] xrevrange failed: %s", exc)

        # In-memory fallback
        history = _fallback_history.get(stream, [])
        return list(reversed(history[-count:]))

    # ----------------------------------------------------------------------- #
    #  Consume (blocking read — used by background agent loops)               #
    # ----------------------------------------------------------------------- #
    async def consume(
        self,
        stream: str,
        block_ms: int = 2000,
    ) -> Optional[Dict[str, Any]]:
        """
        Blocking read: waits up to `block_ms` for a new entry.
        Returns the payload dict or None on timeout.
        """
        if self._redis_available and self._client:
            try:
                raw = await self._client.xread(
                    {stream: "$"},      # "$" = only new messages
                    count=1,
                    block=block_ms,
                )
                if raw:
                    _, entries = raw[0]
                    _, fields = entries[0]
                    return json.loads(fields.get("data", "{}"))
                return None
            except Exception as exc:
                logger.warning("[StreamService] xread failed: %s", exc)

        # In-memory fallback
        q = _get_fallback(stream)
        try:
            payload = await asyncio.wait_for(q.get(), timeout=block_ms / 1000)
            return payload
        except asyncio.TimeoutError:
            return None

    # ----------------------------------------------------------------------- #
    #  Legacy Stream Consumer (for telemetry event orchestration)              #
    # ----------------------------------------------------------------------- #
    async def read_stream(
        self,
        stream: str,
        count: int = 10,
        block: int = 5000,
        last_id: str = "$",
    ) -> List:
        """
        Read new entries from a Redis Stream.
        When Redis is available, delegates to XREAD.
        When offline, drains and returns events buffered in memory.
        """
        if self._redis_available and self._client is not None:
            try:
                result = await self._client.xread(
                    {stream: last_id}, count=count, block=block
                )
                if result:
                    # xread returns: [[stream_name, [(entry_id, fields), ...]]]
                    parsed_entries = []
                    for entry_id, fields in result[0][1]:
                        try:
                            data = json.loads(fields.get("data", "{}"))
                            parsed_entries.append((entry_id, data))
                        except Exception:
                            parsed_entries.append((entry_id, fields))
                    return parsed_entries
                return []
            except Exception as exc:
                logger.warning("[StreamService] xread failed: %s", exc)
                return []

        # In-memory fallback: read items from history that are newer than last_id
        history = _fallback_history.get(stream, [])
        start_idx = 0
        if last_id and last_id.startswith("mem-"):
            try:
                start_idx = int(last_id.split("-")[1]) + 1
            except ValueError:
                pass
        elif last_id == "$":
            start_idx = len(history)

        events = history[start_idx:start_idx + count]
        return [(ev["id"], ev) for ev in events]

    async def start_consumer(
        self,
        callback: Callable[[List], Coroutine[Any, Any, None]],
    ) -> None:
        """
        Continuously read from the positions stream and invoke the callback.
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
                    last_id = events[-1][0]
                else:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("[StreamService] consumer error: %s", exc)
                await asyncio.sleep(1)

    # ----------------------------------------------------------------------- #
    #  Cache helpers (Redis GET/SET with TTL)                                  #
    # ----------------------------------------------------------------------- #
    async def cache_set(self, key: str, value: Any, ttl: int) -> None:
        if self._redis_available and self._client:
            try:
                await self._client.setex(key, ttl, json.dumps(value))
            except Exception as exc:
                logger.debug("[StreamService] cache_set failed: %s", exc)

    async def cache_get(self, key: str) -> Optional[Any]:
        if self._redis_available and self._client:
            try:
                raw = await self._client.get(key)
                return json.loads(raw) if raw else None
            except Exception as exc:
                logger.debug("[StreamService] cache_get failed: %s", exc)
        return None

    async def rate_limit_check(self, key: str, limit: int, window_sec: int) -> bool:
        """
        Returns True if request is within rate limit, False if exceeded.
        Uses a simple Redis counter with expiry.
        """
        if not (self._redis_available and self._client):
            return True  # Allow all when Redis unavailable
        try:
            pipe = self._client.pipeline()
            await pipe.incr(key)
            await pipe.expire(key, window_sec)
            results = await pipe.execute()
            count = results[0]
            return count <= limit
        except Exception:
            return True


# Singleton
stream_service = StreamService()
