/** REST calls for the activity history. */

import { apiRequest, withQuery } from '@/shared/api/client';
import type { ActivityEventRead, Paginated } from '@/shared/api/types';

/**
 * List activity events of a project.
 *
 * @param projectId project id.
 * @param page page number.
 * @returns paginated activity feed.
 */
export function listProjectActivity(
  projectId: number,
  page = 1,
): Promise<Paginated<ActivityEventRead>> {
  return apiRequest(
    'GET',
    withQuery(`/api/v1/projects/${projectId}/activity`, { page, page_size: 30 }),
  );
}

/**
 * List activity events of a single task.
 *
 * @param taskId task id.
 * @param page page number.
 * @returns paginated activity feed.
 */
export function listTaskActivity(taskId: number, page = 1): Promise<Paginated<ActivityEventRead>> {
  return apiRequest('GET', withQuery(`/api/v1/tasks/${taskId}/activity`, { page, page_size: 30 }));
}
