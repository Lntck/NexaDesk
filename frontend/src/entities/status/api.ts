/** REST calls for board statuses and project labels. */

import { apiRequest } from '@/shared/api/client';
import type {
  LabelCreate,
  LabelPatch,
  LabelRead,
  TaskStatusCreate,
  TaskStatusPatch,
  TaskStatusRead,
} from '@/shared/api/types';

/**
 * List board statuses of a project ordered by position.
 *
 * @param projectId project id.
 * @returns status list.
 */
export function listStatuses(projectId: number): Promise<TaskStatusRead[]> {
  return apiRequest('GET', `/api/v1/projects/${projectId}/statuses`);
}

/**
 * Create a custom board status.
 *
 * @param projectId project id.
 * @param body status name, key, color and optional position.
 * @returns the created status.
 */
export function createStatus(projectId: number, body: TaskStatusCreate): Promise<TaskStatusRead> {
  return apiRequest('POST', `/api/v1/projects/${projectId}/statuses`, { body });
}

/**
 * Update status metadata or board position.
 *
 * @param projectId project id.
 * @param statusId status id.
 * @param body fields to change.
 * @returns the updated status.
 */
export function patchStatus(
  projectId: number,
  statusId: number,
  body: TaskStatusPatch,
): Promise<TaskStatusRead> {
  return apiRequest('PATCH', `/api/v1/projects/${projectId}/statuses/${statusId}`, { body });
}

/**
 * Delete an unused board status.
 *
 * @param projectId project id.
 * @param statusId status id.
 */
export function deleteStatus(projectId: number, statusId: number): Promise<void> {
  return apiRequest('DELETE', `/api/v1/projects/${projectId}/statuses/${statusId}`);
}

/**
 * List labels of a project.
 *
 * @param projectId project id.
 * @returns label list.
 */
export function listLabels(projectId: number): Promise<LabelRead[]> {
  return apiRequest('GET', `/api/v1/projects/${projectId}/labels`);
}

/**
 * Create a project label.
 *
 * @param projectId project id.
 * @param body label name and color.
 * @returns the created label.
 */
export function createLabel(projectId: number, body: LabelCreate): Promise<LabelRead> {
  return apiRequest('POST', `/api/v1/projects/${projectId}/labels`, { body });
}

/**
 * Update a project label.
 *
 * @param projectId project id.
 * @param labelId label id.
 * @param body fields to change.
 * @returns the updated label.
 */
export function patchLabel(
  projectId: number,
  labelId: number,
  body: LabelPatch,
): Promise<LabelRead> {
  return apiRequest('PATCH', `/api/v1/projects/${projectId}/labels/${labelId}`, { body });
}

/**
 * Delete a project label and detach it from tasks.
 *
 * @param projectId project id.
 * @param labelId label id.
 */
export function deleteLabel(projectId: number, labelId: number): Promise<void> {
  return apiRequest('DELETE', `/api/v1/projects/${projectId}/labels/${labelId}`);
}
