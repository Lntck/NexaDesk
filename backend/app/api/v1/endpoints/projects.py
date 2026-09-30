from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import RequireRole
from app.auth.policy import RequireProjectRole
from app.auth.schemas import CurrentUser
from app.dependencies import (
    get_db_session,
    get_project_service,
)
from app.enums import ProjectRole, Role
from app.schemas import (
    OwnershipTransfer,
    PageParams,
    Paginated,
    ProjectCreate,
    ProjectCreated,
    ProjectListItem,
    ProjectPatch,
    ProjectRead,
)
from app.services import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=Paginated[ProjectListItem])
async def list_projects(
    current_user: CurrentUser = Depends(RequireRole(Role.USER)),
    session: AsyncSession = Depends(get_db_session),
    service: ProjectService = Depends(get_project_service),
    page: PageParams = Depends(),
    search: str | None = None,
    archived: bool | None = None,
    sort: str | None = None,
):
    """Get projects available to the current user.

    Args:
        current_user: authenticated caller.
        session: active database session.
        service: project domain service.
        page: pagination parameters.
        search: optional substring filter on key and name.
        archived: archive filter, archived projects are excluded by default.
        sort: sort key from the collection whitelist.

    Returns:
        Paginated[ProjectListItem]: one page of projects with caller roles.
    """
    return await service.list_projects(
        session, current_user.id, page, search, archived, sort
    )


@router.post("", response_model=ProjectCreated, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    current_user: CurrentUser = Depends(RequireRole(Role.USER)),
    session: AsyncSession = Depends(get_db_session),
    service: ProjectService = Depends(get_project_service),
):
    """Create a project owned by the current user.

    Args:
        data: validated project creation payload.
        current_user: authenticated caller.
        session: active database session.
        service: project domain service.

    Returns:
        ProjectCreated: the created project.
    """
    return await service.create_project(session, current_user.id, data)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.VIEWER)),
    session: AsyncSession = Depends(get_db_session),
    service: ProjectService = Depends(get_project_service),
    project_id: int = Path(...),
):
    """Get project details.

    Args:
        current_user: authenticated project member.
        session: active database session.
        service: project domain service.
        project_id: project to read.

    Returns:
        ProjectRead: project details with counters.
    """
    return await service.get_project(session, current_user.id, project_id)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    data: ProjectPatch,
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    service: ProjectService = Depends(get_project_service),
    project_id: int = Path(...),
):
    """Update project metadata.

    Args:
        data: merge patch payload with editable fields.
        current_user: authenticated project owner or admin.
        session: active database session.
        service: project domain service.
        project_id: project to update.

    Returns:
        ProjectRead: the updated project details.
    """
    return await service.update_project(session, current_user.id, project_id, data)


@router.post("/{project_id}/archive", response_model=ProjectRead)
async def archive_project(
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    service: ProjectService = Depends(get_project_service),
    project_id: int = Path(...),
):
    """Archive a project and freeze all domain writes.

    Args:
        current_user: authenticated project owner or admin.
        session: active database session.
        service: project domain service.
        project_id: project to archive.

    Returns:
        ProjectRead: the archived project details.
    """
    return await service.archive_project(session, current_user.id, project_id)


@router.post("/{project_id}/restore", response_model=ProjectRead)
async def restore_project(
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    service: ProjectService = Depends(get_project_service),
    project_id: int = Path(...),
):
    """Restore an archived project.

    Args:
        current_user: authenticated project owner or admin.
        session: active database session.
        service: project domain service.
        project_id: project to restore.

    Returns:
        ProjectRead: the restored project details.
    """
    return await service.restore_project(session, current_user.id, project_id)


@router.post("/{project_id}/transfer-ownership", response_model=ProjectRead)
async def transfer_ownership(
    data: OwnershipTransfer,
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.OWNER)),
    session: AsyncSession = Depends(get_db_session),
    service: ProjectService = Depends(get_project_service),
    project_id: int = Path(...),
):
    """Transfer project ownership to another member.

    Args:
        data: command payload naming the new owner.
        current_user: authenticated project owner.
        session: active database session.
        service: project domain service.
        project_id: project whose ownership is transferred.

    Returns:
        ProjectRead: the project details with the new owner.
    """
    return await service.transfer_ownership(session, current_user.id, project_id, data)
