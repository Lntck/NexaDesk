/** REST calls for project membership. */

import { apiRequest } from '@/shared/api/client';
import type { MemberAdd, MemberList, MemberRead, ProjectRole } from '@/shared/api/types';

/**
 * List members of a project.
 *
 * @param projectId project id.
 * @returns member list.
 */
export function listMembers(projectId: number): Promise<MemberList> {
  return apiRequest('GET', `/api/v1/projects/${projectId}/members`);
}

/**
 * Add an existing user to a project.
 *
 * @param projectId project id.
 * @param body user id and membership role.
 * @returns the created membership.
 */
export function addMember(projectId: number, body: MemberAdd): Promise<MemberRead> {
  return apiRequest('POST', `/api/v1/projects/${projectId}/members`, { body });
}

/**
 * Change the role of a project member.
 *
 * @param projectId project id.
 * @param userId member user id.
 * @param role new project role.
 * @returns the updated membership.
 */
export function updateMemberRole(
  projectId: number,
  userId: number,
  role: ProjectRole,
): Promise<MemberRead> {
  return apiRequest('PATCH', `/api/v1/projects/${projectId}/members/${userId}`, { body: { role } });
}

/**
 * Remove a member from a project.
 *
 * @param projectId project id.
 * @param userId member user id.
 */
export function removeMember(projectId: number, userId: number): Promise<void> {
  return apiRequest('DELETE', `/api/v1/projects/${projectId}/members/${userId}`);
}
