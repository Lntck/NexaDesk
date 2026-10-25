from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health_router, v1_router
from app.core import API_V1_PREFIX, get_settings, limiter
from app.core.logger import configure_logging
from app.core.middleware import MetricsMiddleware, RequestLoggingMiddleware
from app.exceptions import register_exception_handlers
from app.lifespan import lifespan

settings = get_settings()

configure_logging(settings.log_level)

app = FastAPI(
    title="NexaDesk API",
    version=settings.service_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(MetricsMiddleware)
app.state.limiter = limiter
register_exception_handlers(app)
app.include_router(health_router, prefix="/health")
app.include_router(v1_router, prefix=API_V1_PREFIX)
