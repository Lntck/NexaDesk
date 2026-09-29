class AppException(Exception):
    """Base application exception"""

    status_code: int = 500
    detail: str = "Internal server error"
    code: str = "internal_error"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.detail
        super().__init__(self.detail)


# Register Exceptions
class UserAlreadyExists(AppException):
    """Raised on unique constraint violation during registration."""

    status_code = 409
    detail = "User already exists"
    code = "already_exists"


class ValidationFailed(AppException):
    """Raised when a request value violates application-level validation rules."""

    status_code = 422
    detail = "Validation error"
    code = "validation_error"


# Authenticate Exceptions
class InvalidCredentials(AppException):
    """Raised when username or password do not match an active account."""

    status_code = 401
    detail = "Invalid username or password"
    code = "unauthenticated"


class TokenExpiredError(AppException):
    """Raised when a valid-shaped token is past its expiry."""

    status_code = 401
    detail = "Token has expired"
    code = "token_invalid"


class TokenInvalidError(AppException):
    """Raised when a token fails signature or payload validation."""

    status_code = 401
    detail = "Token is invalid"
    code = "token_invalid"


# User Exceptions
class UserNotFound(AppException):
    """Raised when a requested user does not exist."""

    status_code = 404
    detail = "User not found"
    code = "user_not_found"


class ProjectNotFound(AppException):
    """Raised when a project does not exist or the caller is not its member."""

    status_code = 404
    detail = "Project not found"
    code = "project_not_found"


class AccessDenied(AppException):
    """Raised when the caller is known but lacks the required permission."""

    status_code = 403
    detail = "Access Denied"
    code = "forbidden"