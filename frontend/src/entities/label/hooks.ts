/** TanStack Query hooks for task label attachments. */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/shared/api/queryKeys';
import { attachTaskLabel, detachTaskLabel } from './api';

/**
 * Attach a label to a task and refresh task caches.
 *
 * @returns attach mutation.
 */
export function useAttachLabel() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, labelId }: { taskId: number; labelId: number }) =>
      attachTaskLabel(taskId, labelId),
    onSuccess: (_label, variables) => {
      void client.invalidateQueries({ queryKey: queryKeys.task(variables.taskId) });
      void client.invalidateQueries({ queryKey: ['project'] });
    },
  });
}

/**
 * Remove a label from a task and refresh task caches.
 *
 * @returns detach mutation.
 */
export function useDetachLabel() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, labelId }: { taskId: number; labelId: number }) =>
      detachTaskLabel(taskId, labelId),
    onSuccess: (_data, variables) => {
      void client.invalidateQueries({ queryKey: queryKeys.task(variables.taskId) });
      void client.invalidateQueries({ queryKey: ['project'] });
    },
  });
}
