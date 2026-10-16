from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from app.auth.schemas import CurrentUser
from app.core import API_V1_PREFIX
from app.dependencies import get_auth_service
from app.services import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{API_V1_PREFIX}/login")


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    service: AuthService = Depends(get_auth_service),
) -> CurrentUser:
    """Resolve the authenticated user and expose it to the access log.

    Args:
        request: request being processed, used to store the user id.
        token: bearer access token from the Authorization header.
        service: authentication service dependency.

    Returns:
        CurrentUser: identity and role taken from the token.
    """
    current_user = service.get_user_from_access_token(token)
    request.state.user_id = current_user.id
    return current_user
