from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.logger import logger
from app.core.metrics import observe_auth_attempt

from .custom import AppException

#: Rate limited endpoints that count as authentication attempts.
AUTH_ATTEMPT_SUFFIXES = ("/register", "/login", "/refresh", "/logout")


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers for the FastAPI application.

    Every error payload follows the contract envelope: human readable
    "detail" plus stable machine readable "code".
    """

    @app.exception_handler(RateLimitExceeded)
    async def handle_rate_limit(request: Request, exc: RateLimitExceeded):
        """Answer a throttled request and count the auth attempt.

        Args:
            request: throttled request.
            exc: rate limit error.

        Returns:
            JSONResponse: 429 response with the contract envelope.
        """
        if request.url.path.endswith(AUTH_ATTEMPT_SUFFIXES):
            observe_auth_attempt("rate_limited")
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded", "code": "rate_limited"},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Request validation error",
                "code": "validation_error",
                "errors": jsonable_encoder(exc.errors()),
            },
        )

    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
        )

    @app.exception_handler(Exception)
    async def handle_any_exception(request: Request, exc: Exception):
        """Log the failure and answer with the internal error envelope.

        Args:
            request: request being processed.
            exc: unhandled exception raised by the application.

        Returns:
            JSONResponse: 500 response with the contract envelope.
        """
        logger.error("unhandled error while processing request", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "code": "internal_error"},
        )
