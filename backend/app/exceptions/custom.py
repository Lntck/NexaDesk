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


class AlreadyExists(AppException):
    """Raised when a new row would violate a uniqueness invariant."""

    status_code = 409
    detail = "Resource already exists"
    code = "already_exists"


# Domain Exceptions
class TaskNotFound(AppException):
    """Raised when a task does not exist or the caller is not its project member."""

    status_code = 404
    detail = "Task not found"
    code = "task_not_found"


class TaskStatusNotFound(AppException):
    """Raised when a board status does not exist in the given project."""

    status_code = 404
    detail = "Task status not found"
    code = "status_not_found"


class InvalidTransition(AppException):
    """Raised when a task status change violates the transition matrix."""

    status_code = 409
    detail = "Task cannot transition to the requested status"
    code = "invalid_transition"


class StaleVersion(AppException):
    """Raised when an If-Match version does not match the current task version."""

    status_code = 409
    detail = "Task has been modified concurrently"
    code = "stale_version"


class PreconditionRequired(AppException):
    """Raised when a mutation is missing its If-Match precondition."""

    status_code = 428
    detail = "If-Match header with the task version is required"
    code = "precondition_required"


class StatusInUse(AppException):
    """Raised when a status holding tasks is being deleted."""

    status_code = 409
    detail = "Status still has tasks"
    code = "status_in_use"


class ArchivedCollection(AppException):
    """Raised when a write operation targets an archived project."""

    status_code = 409
    detail = "Project is archived"
    code = "archived_collection"


class CommentNotFound(AppException):
    """Raised when a comment does not exist or was soft-deleted."""

    status_code = 404
    detail = "Comment not found"
    code = "comment_not_found"


class NotificationNotFound(AppException):
    """Raised when a notification does not exist or belongs to another user."""

    status_code = 404
    detail = "Notification not found"
    code = "notification_not_found"


class LabelNotFound(AppException):
    """Raised when a label does not exist in the given project."""

    status_code = 404
    detail = "Label not found"
    code = "label_not_found"


class PayloadError(AppException):
    """Raised when ids or relations in a payload are semantically invalid."""

    status_code = 422
    detail = "Payload validation error"
    code = "payload_error"
