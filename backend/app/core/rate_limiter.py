import time
from fastapi import Request, HTTPException, status
from collections import defaultdict


class InMemoryRateLimiter:
    def __init__(
        self,
        requests_limit: int = 100,
        window_seconds: int = 60,
        ttl_seconds: int = 120,
        cleanup_interval_seconds: int = 60,
    ):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.ttl_seconds = max(ttl_seconds, window_seconds * 2)
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self.history: dict[str, list[float]] = {}
        self.last_seen: dict[str, float] = {}
        self.last_cleanup: float = time.time()

    def evict_expired(self, now: float | None = None) -> int:
        """
        Evicts all inactive IP keys whose activity is older than TTL or window.
        Returns the number of keys evicted to prevent memory leaks.
        """
        if now is None:
            now = time.time()
        evicted = 0
        stale_ips = []

        for ip, timestamps in list(self.history.items()):
            active_ts = [t for t in timestamps if now - t < self.window_seconds]
            if not active_ts or (now - self.last_seen.get(ip, 0) > self.ttl_seconds):
                stale_ips.append(ip)
            else:
                self.history[ip] = active_ts

        for ip in stale_ips:
            self.history.pop(ip, None)
            self.last_seen.pop(ip, None)
            evicted += 1

        # Also purge any orphan last_seen keys
        for ip in list(self.last_seen.keys()):
            if ip not in self.history:
                self.last_seen.pop(ip, None)

        self.last_cleanup = now
        return evicted

    async def check_rate_limit(self, request: Request):
        # Allow open access to docs
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return

        # Bypass for integration tests or scenario mode
        from app.config import settings

        if settings.SCENARIO_MODE or "testserver" in str(request.base_url):
            return

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Periodic cleanup of inactive IP keys to prevent memory leak
        if now - self.last_cleanup >= self.cleanup_interval_seconds:
            self.evict_expired(now)

        # Clean history for this specific client IP
        current_history = self.history.get(client_ip, [])
        valid_timestamps = [t for t in current_history if now - t < self.window_seconds]

        # Check limit
        limit = self.requests_limit
        # Auth endpoints are more restricted: 10 per minute
        if "/auth" in request.url.path:
            limit = 10

        if len(valid_timestamps) >= limit:
            self.history[client_ip] = valid_timestamps
            self.last_seen[client_ip] = now
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {limit} requests per minute allowed.",
            )

        valid_timestamps.append(now)
        self.history[client_ip] = valid_timestamps
        self.last_seen[client_ip] = now


rate_limiter = InMemoryRateLimiter()

