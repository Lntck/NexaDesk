import asyncio

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.db import DatabaseClient, RedisClient

router = APIRouter(tags=["Health"])


@router.get("/live")
async def liveness_probe():
    """Report process liveness for container probes.

    Returns:
        dict: static status payload confirming the process is running.
    """
    return {"status": "ok"}


@router.get("", summary="Aggregate health probe")
@router.get("/ready", summary="Readiness probe")
async def readiness_probe(request: Request):
    """Check backing services and report readiness.

    Serves both `/health` and `/health/ready`: external monitors probe the
    aggregate path, orchestration gates traffic on the readiness path.

    Pings PostgreSQL and Redis in parallel with a short timeout; any
    failure downgrades the result to an error state.

    Args:
        request: incoming request used to reach the application state.

    Returns:
        JSONResponse: per-service status with HTTP 200 when everything is
        healthy and HTTP 503 otherwise.
    """
    db: DatabaseClient = request.app.state.db
    redis: RedisClient = request.app.state.redis

    postgres_result, redis_result = await asyncio.gather(
        asyncio.wait_for(db.ping(), timeout=3),
        asyncio.wait_for(redis.ping(), timeout=3),
        return_exceptions=True,
    )

    postgres_status = (
        False if isinstance(postgres_result, Exception) else postgres_result
    )
    redis_status = False if isinstance(redis_result, Exception) else redis_result

    overall_ok = postgres_status and redis_status
    payload = {
        "status": "ok" if overall_ok else "error",
        "services": {
            "postgres": "ok" if postgres_status else "error",
            "redis": "ok" if redis_status else "error",
        },
    }

    return JSONResponse(
        status_code=(
            status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        ),
        content=payload,
    )
