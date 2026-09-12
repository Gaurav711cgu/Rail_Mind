"""
Token Bucket Rate Limiter for RailMind.
Enforces multi-tenant fairness and prevents LLM API exhaustion.
"""
import time
import asyncio
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class RateLimitExceeded(Exception):
    pass

class AsyncTokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()

    async def consume(self, tokens: int = 1) -> bool:
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

class TenantRateLimiter:
    def __init__(self, default_tpm: int = 40000):
        self.buckets: Dict[str, AsyncTokenBucket] = {}
        self.default_tpm = default_tpm
        self.refill_rate = default_tpm / 60.0 # tokens per second

    async def check_limit(self, tenant_id: str, requested_tokens: int) -> bool:
        if tenant_id not in self.buckets:
            self.buckets[tenant_id] = AsyncTokenBucket(
                capacity=self.default_tpm, 
                refill_rate=self.refill_rate
            )
            
        allowed = await self.buckets[tenant_id].consume(requested_tokens)
        if not allowed:
            logger.warning(f"Tenant {tenant_id} exceeded rate limit of {self.default_tpm} TPM.")
            raise RateLimitExceeded("LLM Token Rate Limit Exceeded. Please back off.")
        return True
