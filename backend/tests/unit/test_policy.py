import pytest

from app.auth.policy import RequireProjectRole
from app.auth.schemas import CurrentUser
from app.enums import ProjectRole, Role
from app.exceptions import AccessDenied, ProjectNotFound


class FakeMembership:
    """Project membership lookup returning a preset role."""

    def __init__(self, role: ProjectRole | None):
        """Remember the role to report.

        Args:
            role: role of the stub member, None means not a member.
        """
        self.role = role

    async def get_project_role(self, session, project_id: int, user_id: int):
        """Return the configured role.

        Args:
            session: unused session placeholder.
            project_id: unused project id placeholder.
            user_id: unused user id placeholder.

        Returns:
            ProjectRole | None: configured role.
        """
        return self.role


def _fake_user() -> CurrentUser:
    """Build an authenticated user stub for policy tests.

    Returns:
        CurrentUser: stub with global user role and id 1.
    """
    return CurrentUser.model_validate({"sub": 1, "role": Role.USER})


async def test_require_project_role_non_member():
    guard = RequireProjectRole(ProjectRole.MEMBER)
    with pytest.raises(ProjectNotFound):
        await guard(
            project_id=1,
            current_user=_fake_user(),
            session=None,
            membership=FakeMembership(None),
        )


async def test_require_project_role_insufficient():
    guard = RequireProjectRole(ProjectRole.MEMBER)
    with pytest.raises(AccessDenied):
        await guard(
            project_id=1,
            current_user=_fake_user(),
            session=None,
            membership=FakeMembership(ProjectRole.VIEWER),
        )


async def test_require_project_role_granted():
    guard = RequireProjectRole(ProjectRole.MEMBER)
    user = _fake_user()
    result = await guard(
        project_id=1,
        current_user=user,
        session=None,
        membership=FakeMembership(ProjectRole.OWNER),
    )
    assert result is user


async def test_require_project_role_membership_not_configured():
    guard = RequireProjectRole(ProjectRole.MEMBER)
    with pytest.raises(RuntimeError):
        await guard(
            project_id=1,
            current_user=_fake_user(),
            session=None,
            membership=None,
        )