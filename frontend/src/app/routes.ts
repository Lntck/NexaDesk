/**
 * Route table for the whole app.
 *
 * Paths are referenced by navigation and redirects, so they live in one
 * place instead of being scattered across pages.
 */

/**
 * Build the board route of a project.
 *
 * @param projectId project id.
 * @returns in-app route path.
 */
export function projectBoardRoute(projectId: number): string {
  return `/projects/${projectId}/board`;
}

/**
 * Build the task list route of a project.
 *
 * @param projectId project id.
 * @returns in-app route path.
 */
export function projectTasksRoute(projectId: number): string {
  return `/projects/${projectId}/tasks`;
}

/**
 * Build the standalone task route.
 *
 * @param taskId task id.
 * @returns in-app route path that can be shared.
 */
export function taskRoute(taskId: number): string {
  return `/tasks/${taskId}`;
}
