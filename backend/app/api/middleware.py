import time
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from app.core import state
from app.core.rate_limiter import rate_limiter


async def performance_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
        return response
    finally:
        latency = (time.perf_counter() - start_time) * 1000.0
        state.request_metrics["total_requests"] += 1
        n = state.request_metrics["total_requests"]
        old_avg = state.request_metrics["avg_latency_ms"]
        state.request_metrics["avg_latency_ms"] = round(old_avg + (latency - old_avg) / n, 2)

        state.request_metrics["_latencies"].append(latency)
        if len(state.request_metrics["_latencies"]) > 100:
            state.request_metrics["_latencies"].pop(0)

        sorted_l = sorted(state.request_metrics["_latencies"])
        if sorted_l:
            idx = min(int(len(sorted_l) * 0.99), len(sorted_l) - 1)
            state.request_metrics["p99_latency_ms"] = round(sorted_l[idx], 2)
        else:
            state.request_metrics["p99_latency_ms"] = 0.0


async def rate_limit_middleware(request: Request, call_next):
    try:
        await rate_limiter.check_rate_limit(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)
