/** REST calls for task watchers. */

import { apiRequest } from '@/shared/api/client';
import type { WatcherRead } from '@/shared/api/types';

/**
 * List watchers of a task.
 *
 * @param taskId task id.
 * @returns watcher list.
 */
export function listWatchers(taskId: number): Promise<WatcherRead[]> {
  return apiRequest('GET', `/api/v1/tasks/${taskId}/watchers`);
}

/**
 * Start watching a task (idempotent).
 *
 * @param taskId task id.
 * @returns the created watch entry.
 */
export function watchTask(taskId: number): Promise<WatcherRead> {
  return apiRequest('POST', `/api/v1/tasks/${taskId}/watch`);
}

/**
 * Stop watching a task (idempotent).
 *
 * @param taskId task id.
 */
export function unwatchTask(taskId: number): Promise<void> {
  return apiRequest('POST', `/api/v1/tasks/${taskId}/unwatch`);
}

/**
 * Remove a watcher from a task.
 *
 * @param taskId task id.
 * @param userId watcher user id.
 */
export function removeWatcher(taskId: number, userId: number): Promise<void> {
  return apiRequest('DELETE', `/api/v1/tasks/${taskId}/watchers/${userId}`);
}
