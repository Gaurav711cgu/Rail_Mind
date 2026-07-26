import time
from fastapi import Request, HTTPException, status
from collections import defaultdict


class InMemoryRateLimiter:
    def __init__(self, requests_limit: int = 100, window_seconds: int = 60):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.history: defaultdict[str, list[float]] = defaultdict(list)

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

        # Clean history
        self.history[client_ip] = [t for t in self.history[client_ip] if now - t < self.window_seconds]

        # Check limit
        limit = self.requests_limit
        # Auth endpoints are more restricted: 10 per minute
        if "/auth" in request.url.path:
            limit = 10

        if len(self.history[client_ip]) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {limit} requests per minute allowed.",
            )

        self.history[client_ip].append(now)


rate_limiter = InMemoryRateLimiter()
