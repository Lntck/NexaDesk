from sqlalchemy.exc import IntegrityError

from app.core import hash_password
from app.models import User


class FakeUserCRUD:
    """In-memory stand-in for UserCRUD used in unit tests."""

    def __init__(self):
        """Create the store with one known user and an id sequence."""
        self.users = {
            1: User(
                id=1,
                username="duplicate",
                email="duplicate@example.com",
                password_hash=hash_password("password"),
                is_active=True,
            )
        }
        self._id_seq = 2

    async def create_user(self, session, user):
        """Store a user or raise IntegrityError on a duplicate.

        Args:
            session: unused session placeholder.
            user: user to store.

        Returns:
            User: the stored user with assigned id.

        Raises:
            IntegrityError: when email or username already exists.
        """
        for user_db in self.users.values():
            if user_db.email.lower() == user.email.lower():
                raise IntegrityError(
                    "INSERT INTO users ...",
                    {"email": user.email},
                    Exception("UNIQUE constraint failed: users.email"),
                )
            if user_db.username == user.username:
                raise IntegrityError(
                    "INSERT INTO users ...",
                    {"username": user.username},
                    Exception("UNIQUE constraint failed: users.username"),
                )

        user.id = self._id_seq
        self._id_seq += 1

        self.users[user.id] = user
        return user

    async def get_by_id(self, session, user_id):
        """Return the user with the given id.

        Args:
            session: unused session placeholder.
            user_id: id of the requested user.

        Returns:
            User | None: the stored user or None.
        """
        return self.users.get(user_id)

    async def get_by_username(self, session, username):
        """Return the user with the given username.

        Args:
            session: unused session placeholder.
            username: username to search for.

        Returns:
            User | None: the stored user or None.
        """
        for user in self.users.values():
            if user.username == username:
                return user
        return None

    async def get_all_users(self, session):
        """Return every stored user.

        Args:
            session: unused session placeholder.

        Returns:
            list[User]: all stored users.
        """
        return list(self.users.values())


class InactiveUserCRUD(FakeUserCRUD):
    """FakeUserCRUD variant where every account is deactivated."""

    def __init__(self):
        """Build the store and deactivate all stored accounts."""
        super().__init__()
        for user in self.users.values():
            user.is_active = False


class StaticUserCRUD:
    """User storage fake with preset accounts and no password hashing."""

    def __init__(self, users):
        """Index the preset accounts by id.

        Args:
            users: user accounts available to the tests.
        """
        self.users = {user.id: user for user in users}

    async def get_by_id(self, session, user_id):
        """Return the user with the given id.

        Args:
            session: unused session placeholder.
            user_id: id of the requested user.

        Returns:
            User | None: the preset user or None.
        """
        return self.users.get(user_id)

    async def get_by_username(self, session, username):
        """Return the user with the given username.

        Args:
            session: unused session placeholder.
            username: username to search for.

        Returns:
            User | None: the preset user or None.
        """
        for user in self.users.values():
            if user.username == username:
                return user
        return None
