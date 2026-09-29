from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import hash_password
from app.exceptions import UserAlreadyExists, UserNotFound
from app.models import User
from app.protocols import UserCRUDProtocol
from app.schemas import UserRegister


def is_unique_violation(exc: IntegrityError) -> bool:
    """Check whether the error is a unique constraint violation.

    Args:
        exc: integrity error raised by the database driver.

    Returns:
        bool: True for unique violations, False for other integrity errors.
    """
    orig = exc.orig
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    if sqlstate is not None:
        return str(sqlstate) == "23505"
    return "unique" in str(orig).lower()


class UserService:
    """User account management service."""

    def __init__(self, user_crud: UserCRUDProtocol):
        """Attach a user storage implementation.

        Args:
            user_crud: storage used for user persistence.
        """
        self.user_crud = user_crud

    async def create_user(self, session: AsyncSession, reg_data: UserRegister) -> User:
        """Register a new user account.

        Args:
            session: active database session.
            reg_data: validated registration payload.

        Returns:
            User: the persisted user.

        Raises:
            UserAlreadyExists: when username or email is already taken.
            IntegrityError: on other database integrity failures.
        """
        hashed_psw = hash_password(reg_data.password.get_secret_value())

        user = User(
            username=reg_data.username,
            email=reg_data.email,
            password_hash=hashed_psw,
        )

        try:
            return await self.user_crud.create_user(session, user)
        except IntegrityError as exc:
            if is_unique_violation(exc):
                raise UserAlreadyExists() from exc
            raise

    async def get_by_id(self, session: AsyncSession, user_id: int) -> User:
        """Load a user by primary key.

        Args:
            session: active database session.
            user_id: id of the user.

        Returns:
            User: the found user.

        Raises:
            UserNotFound: when no user has the given id.
        """
        user = await self.user_crud.get_by_id(session, user_id)
        if not user:
            raise UserNotFound()
        return user

    async def get_by_username(self, session: AsyncSession, username: str) -> User:
        """Load a user by username.

        Args:
            session: active database session.
            username: normalized username.

        Returns:
            User: the found user.

        Raises:
            UserNotFound: when no user has the given username.
        """
        user = await self.user_crud.get_by_username(session, username)
        if not user:
            raise UserNotFound()
        return user

    async def get_all_users(self, session: AsyncSession) -> list[User]:
        """Load every registered user.

        Args:
            session: active database session.

        Returns:
            list[User]: all users ordered by id.
        """
        users = await self.user_crud.get_all_users(session)
        return list(users)
