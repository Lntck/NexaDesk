/** REST calls for tasks and the kanban board. */

import { apiRequest, withQuery } from '@/shared/api/client';
import type {
  BoardRead,
  Paginated,
  TaskAssignRead,
  TaskCreate,
  TaskListItem,
  TaskPatch,
  TaskPositionRead,
  TaskRead,
  TaskReorder,
  TaskTransitionRead,
} from '@/shared/api/types';
import type { ProjectTasksFilters } from './model';

/**
 * List tasks of a project with filters and pagination.
 *
 * @param projectId project id.
 * @param filters filter and paging parameters.
 * @returns paginated task list.
 */
export function listProjectTasks(
  projectId: number,
  filters: ProjectTasksFilters,
): Promise<Paginated<TaskListItem>> {
  return apiRequest(
    'GET',
    withQuery(`/api/v1/projects/${projectId}/tasks`, {
      search: filters.search,
      status: filters.status,
      priority: filters.priority,
      assignee_id: filters.assignee_id,
      creator_id: filters.creator_id,
      due_before: filters.due_before,
      due_after: filters.due_after,
      sort: filters.sort,
      page: filters.page,
      page_size: filters.page_size,
    }),
  );
}

/**
 * Fetch the kanban board grouped by status.
 *
 * @param projectId project id.
 * @param limitPerColumn maximum cards per column.
 * @returns board columns with cards.
 */
export function getBoard(projectId: number, limitPerColumn = 50): Promise<BoardRead> {
  return apiRequest(
    'GET',
    withQuery(`/api/v1/projects/${projectId}/board`, { limit_per_column: limitPerColumn }),
  );
}

/**
 * Fetch a single task with labels and counters.
 *
 * @param taskId task id.
 * @returns full task details.
 */
export function getTask(taskId: number): Promise<TaskRead> {
  return apiRequest('GET', `/api/v1/tasks/${taskId}`);
}

/**
 * Create a task inside a project.
 *
 * @param projectId project id.
 * @param body task payload.
 * @returns the created task.
 */
export function createTask(projectId: number, body: TaskCreate): Promise<TaskRead> {
  return apiRequest('POST', `/api/v1/projects/${projectId}/tasks`, { body });
}

/**
 * Patch editable task fields with optimistic concurrency.
 *
 * @param taskId task id.
 * @param body fields to change.
 * @param version current task version for the If-Match header.
 * @returns the updated task.
 */
export function patchTask(taskId: number, body: TaskPatch, version: number): Promise<TaskRead> {
  return apiRequest('PATCH', `/api/v1/tasks/${taskId}`, { body, ifMatch: version });
}

/**
 * Soft-delete a task with optimistic concurrency.
 *
 * @param taskId task id.
 * @param version current task version for the If-Match header.
 */
export function deleteTask(taskId: number, version: number): Promise<void> {
  return apiRequest('DELETE', `/api/v1/tasks/${taskId}`, { ifMatch: version });
}

/**
 * Move a task to an adjacent board column.
 *
 * @param taskId task id.
 * @param statusId target status id.
 * @returns the new task position.
 */
export function transitionTask(taskId: number, statusId: number): Promise<TaskTransitionRead> {
  return apiRequest('POST', `/api/v1/tasks/${taskId}/transition`, {
    body: { status_id: statusId },
  });
}

/**
 * Assign a task to a project member.
 *
 * @param taskId task id.
 * @param userId assignee user id.
 * @returns updated assignment.
 */
export function assignTask(taskId: number, userId: number): Promise<TaskAssignRead> {
  return apiRequest('POST', `/api/v1/tasks/${taskId}/assign`, { body: { user_id: userId } });
}

/**
 * Remove the assignee of a task.
 *
 * @param taskId task id.
 * @returns updated assignment.
 */
export function unassignTask(taskId: number): Promise<TaskAssignRead> {
  return apiRequest('POST', `/api/v1/tasks/${taskId}/unassign`);
}

/**
 * Place a card inside the board and recalculate ranks.
 *
 * @param taskId task id.
 * @param body target column and neighbor ids.
 * @returns the final position of the card.
 */
export function reorderTask(taskId: number, body: TaskReorder): Promise<TaskPositionRead> {
  return apiRequest('POST', `/api/v1/tasks/${taskId}/reorder`, { body });
}
