/** TanStack Query hooks for task watchers. */

import { useMutation, useQuery, useQueryClient, type UseQueryResult } from '@tanstack/react-query';
import { queryKeys } from '@/shared/api/queryKeys';
import type { WatcherRead } from '@/shared/api/types';
import { listWatchers, removeWatcher, unwatchTask, watchTask } from './api';

/**
 * Query watchers of a task.
 *
 * @param taskId task id.
 * @returns watcher list query result.
 */
export function useWatchers(taskId: number | undefined): UseQueryResult<WatcherRead[]> {
  return useQuery({
    queryKey: queryKeys.watchers(taskId ?? 0),
    queryFn: () => listWatchers(taskId as number),
    enabled: taskId !== undefined,
  });
}

/**
 * Watch or unwatch a task and refresh its caches.
 *
 * @returns mutation with a watch flag.
 */
export function useToggleWatch() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({ taskId, watch }: { taskId: number; watch: boolean }) => {
      if (watch) {
        await watchTask(taskId);
      } else {
        await unwatchTask(taskId);
      }
    },
    onSuccess: (_data, variables) => {
      void client.invalidateQueries({ queryKey: queryKeys.watchers(variables.taskId) });
      void client.invalidateQueries({ queryKey: queryKeys.task(variables.taskId) });
    },
  });
}

/**
 * Remove a watcher from a task (admin or self).
 *
 * @returns remove watcher mutation.
 */
export function useRemoveWatcher() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, userId }: { taskId: number; userId: number }) =>
      removeWatcher(taskId, userId),
    onSuccess: (_data, variables) => {
      void client.invalidateQueries({ queryKey: queryKeys.watchers(variables.taskId) });
      void client.invalidateQueries({ queryKey: queryKeys.task(variables.taskId) });
    },
  });
}
