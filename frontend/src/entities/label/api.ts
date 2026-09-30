/** REST calls for task label attachments. */

import { apiRequest } from '@/shared/api/client';
import type { LabelRead } from '@/shared/api/types';

/**
 * Attach a project label to a task.
 *
 * @param taskId task id.
 * @param labelId label id of the same project.
 * @returns the attached label.
 */
export function attachTaskLabel(taskId: number, labelId: number): Promise<LabelRead> {
  return apiRequest('POST', `/api/v1/tasks/${taskId}/labels/${labelId}`);
}

/**
 * Remove a label from a task.
 *
 * @param taskId task id.
 * @param labelId label id.
 */
export function detachTaskLabel(taskId: number, labelId: number): Promise<void> {
  return apiRequest('DELETE', `/api/v1/tasks/${taskId}/labels/${labelId}`);
}
