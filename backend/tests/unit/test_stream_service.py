import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import json

from app.services.stream_service import StreamService


@pytest.mark.asyncio
async def test_stream_service_redis_available():
    service = StreamService()

    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.close = AsyncMock()
    mock_redis.xadd = AsyncMock(return_value="123-456")
    mock_redis.xrevrange = AsyncMock(return_value=[("123-456", {"data": '{"test": "val"}'})])
    mock_redis.xread = AsyncMock(
        return_value=[("stream_name", [("123-456", {"data": '{"test": "val"}'})])]
    )
    mock_redis.setex = AsyncMock()
    mock_redis.get = AsyncMock(return_value=json.dumps("val"))

    # Mock pipeline
    mock_pipeline = AsyncMock()
    mock_pipeline.execute = AsyncMock(return_value=[1])
    mock_redis.pipeline = MagicMock(return_value=mock_pipeline)

    with patch("redis.asyncio.from_url", return_value=mock_redis):
        await service.connect()
        assert service._redis_available is True

        # Test publish
        entry_id = await service.publish("stream", {"test": "val"})
        assert entry_id == "123-456"
        mock_redis.xadd.assert_called_once()

        # Test read_latest
        latest = await service.read_latest("stream", count=1)
        assert len(latest) == 1
        assert latest[0]["test"] == "val"
        assert latest[0]["_stream_id"] == "123-456"

        # Test consume
        consumed = await service.consume("stream")
        assert consumed == {"test": "val"}

        # Test read_stream
        entries = await service.read_stream("stream", count=10)
        assert len(entries) == 1
        assert entries[0][0] == "123-456"
        assert entries[0][1] == {"test": "val"}

        # Test cache set/get
        await service.cache_set("key", "val", 10)
        mock_redis.setex.assert_called_once()

        cached = await service.cache_get("key")
        assert cached == "val"

        # Test rate limit
        allowed = await service.rate_limit_check("key", 10, 60)
        assert allowed is True

        # Test disconnect
        await service.disconnect()
        mock_redis.close.assert_called_once()


@pytest.mark.asyncio
async def test_stream_service_redis_failures():
    service = StreamService()

    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(side_effect=Exception("Redis connection error"))
    mock_redis.xadd = AsyncMock(side_effect=Exception("xadd failed"))
    mock_redis.xrevrange = AsyncMock(side_effect=Exception("xrevrange failed"))
    mock_redis.xread = AsyncMock(side_effect=Exception("xread failed"))
    mock_redis.setex = AsyncMock(side_effect=Exception("setex failed"))
    mock_redis.get = AsyncMock(side_effect=Exception("get failed"))
    mock_redis.pipeline = MagicMock(side_effect=Exception("pipeline failed"))

    with patch("redis.asyncio.from_url", return_value=mock_redis):
        await service.connect()
        assert service._redis_available is False

        # Test publish (falls back to memory)
        entry_id = await service.publish("stream_fail", {"test": "fallback"})
        assert entry_id.startswith("mem-")

        # Test read_latest (falls back to memory)
        latest = await service.read_latest("stream_fail", count=1)
        assert len(latest) == 1
        assert latest[0]["test"] == "fallback"

        # Test consume (falls back to memory)
        consumed = await service.consume("stream_fail", block_ms=10)
        assert consumed == {"test": "fallback"}

        # Test read_stream (falls back to memory)
        entries = await service.read_stream("stream_fail", count=10, last_id="mem-0")
        assert (
            len(entries) == 0
        )  # since last_id is mem-0, index starts from 1, and only 1 element is there

        # Test cache set/get fail paths
        await service.cache_set("key", "val", 10)  # should not raise
        cached = await service.cache_get("key")
        assert cached is None

        # Test rate limit check when Redis unavailable
        allowed = await service.rate_limit_check("key", 10, 60)
        assert allowed is True


@pytest.mark.asyncio
async def test_stream_service_consumer_loop():
    service = StreamService()
    events_to_return = [[("mem-0", {"test": "loop"})]]

    async def mock_read_stream(*args, **kwargs):
        if events_to_return:
            return events_to_return.pop()
        raise asyncio.CancelledError()

    service.read_stream = mock_read_stream

    callback_called = asyncio.Event()

    async def mock_callback(events):
        assert len(events) == 1
        assert events[0][0] == "mem-0"
        callback_called.set()

    task = asyncio.create_task(service.start_consumer(mock_callback))
    try:
        await asyncio.wait_for(callback_called.wait(), timeout=2.0)
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
