from enum import StrEnum, nonmember


class ProjectRole(StrEnum):
    """Project membership role with hierarchy used by permission checks."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

    _LEVELS = nonmember(
        {
            OWNER: 40,
            ADMIN: 30,
            MEMBER: 20,
            VIEWER: 10,
        }
    )

    @property
    def level(self) -> int:
        """Return numeric level of the role for comparisons.

        Returns:
            int: level value, higher means more permissions.
        """
        return self._LEVELS[self]