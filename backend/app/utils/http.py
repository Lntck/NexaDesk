from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Response

if TYPE_CHECKING:
    from app.services import AuthService


def set_refresh_cookie(
    response: Response, refresh_token: str, service: AuthService
) -> None:
    """Set the refresh token cookie on a response.

    Args:
        response: response the cookie is attached to.
        refresh_token: refresh token value.
        service: auth service carrying the cookie settings.
    """
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=service.settings.cookie_secure,
        samesite=service.settings.cookie_samesite,
        path="/",
        max_age=60 * service.settings.refresh_token_expire_m,
    )
