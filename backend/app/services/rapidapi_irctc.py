import time
from collections import deque
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, status

from app.config import settings


class OutgoingAPICallCapper:
    """
    Prevents exceeding RapidAPI pricing tier limits by capping outgoing calls.
    """

    def __init__(self, max_calls: int = 30, window_seconds: int = 60) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.call_history: deque[float] = deque()

    def record_and_check(self) -> None:
        now = time.time()
        while self.call_history and now - self.call_history[0] > self.window_seconds:
            self.call_history.popleft()

        if len(self.call_history) >= self.max_calls:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Outgoing RapidAPI rate limit hit: max {self.max_calls} requests per {self.window_seconds}s.",
            )
        self.call_history.append(now)


class RapidAPIIrctcClient:
    """Small backend-only client for the unofficial RapidAPI IRCTC provider."""

    def __init__(self) -> None:
        self.base_url = settings.RAPIDAPI_IRCTC_BASE_URL.rstrip("/")
        self.host = settings.RAPIDAPI_IRCTC_HOST
        self.api_key = settings.RAPIDAPI_IRCTC_KEY
        self.timeout = settings.RAPIDAPI_IRCTC_TIMEOUT_SECONDS
        self.capper = OutgoingAPICallCapper(max_calls=30, window_seconds=60)

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RapidAPI IRCTC key is not configured. Set RAPIDAPI_IRCTC_KEY in backend/.env.",
            )

        return {
            "Content-Type": "application/json",
            "X-RapidAPI-Host": self.host,
            "X-RapidAPI-Key": self.api_key,
        }

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.capper.record_and_check()
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self._headers(), params=params or {})
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail: Any
            try:
                detail = exc.response.json()
            except ValueError:
                detail = exc.response.text
            raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Unable to reach RapidAPI IRCTC provider: {exc.__class__.__name__}",
            ) from exc

        try:
            data: Any = response.json()
        except ValueError:
            data = response.text

        return {
            "provider": "rapidapi-irctc",
            "host": self.host,
            "path": path,
            "params": params or {},
            "data": data,
        }


rapidapi_irctc = RapidAPIIrctcClient()
