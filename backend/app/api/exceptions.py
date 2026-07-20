import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse


async def global_exception_handler(request: Request, exc: Exception):
    logging.getLogger("railmind").error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. See server logs."},
    )
