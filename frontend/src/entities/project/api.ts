/** REST calls for projects. */

import { apiRequest, withQuery } from '@/shared/api/client';
import type {
  Paginated,
  ProjectCreate,
  ProjectCreated,
  ProjectListItem,
  ProjectPatch,
  ProjectRead,
} from '@/shared/api/types';

/**
 * List projects of the current user.
 *
 * @param filters search text and archived flag.
 * @returns paginated project list.
 */
export function listProjects(filters: {
  search?: string;
  archived?: boolean;
  page?: number;
  page_size?: number;
}): Promise<Paginated<ProjectListItem>> {
  return apiRequest('GET', withQuery('/api/v1/projects', filters));
}

/**
 * Fetch one project with counters.
 *
 * @param projectId project id.
 * @returns project details.
 */
export function getProject(projectId: number): Promise<ProjectRead> {
  return apiRequest('GET', `/api/v1/projects/${projectId}`);
}

/**
 * Create a project; the caller becomes the owner.
 *
 * @param body key, name and optional description.
 * @returns the created project.
 */
export function createProject(body: ProjectCreate): Promise<ProjectCreated> {
  return apiRequest('POST', '/api/v1/projects', { body });
}

/**
 * Update project metadata.
 *
 * @param projectId project id.
 * @param body name and description fields to change.
 * @returns the updated project.
 */
export function patchProject(projectId: number, body: ProjectPatch): Promise<ProjectRead> {
  return apiRequest('PATCH', `/api/v1/projects/${projectId}`, { body });
}

/**
 * Archive a project.
 *
 * @param projectId project id.
 * @returns the archived project.
 */
export function archiveProject(projectId: number): Promise<ProjectRead> {
  return apiRequest('POST', `/api/v1/projects/${projectId}/archive`);
}

/**
 * Restore an archived project.
 *
 * @param projectId project id.
 * @returns the restored project.
 */
export function restoreProject(projectId: number): Promise<ProjectRead> {
  return apiRequest('POST', `/api/v1/projects/${projectId}/restore`);
}

/**
 * Transfer project ownership to another member.
 *
 * @param projectId project id.
 * @param userId new owner user id.
 * @returns the updated project.
 */
export function transferOwnership(projectId: number, userId: number): Promise<ProjectRead> {
  return apiRequest('POST', `/api/v1/projects/${projectId}/transfer-ownership`, {
    body: { user_id: userId },
  });
}
