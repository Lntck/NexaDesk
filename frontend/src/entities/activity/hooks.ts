/** TanStack Query hooks for the activity history. */

import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { queryKeys } from '@/shared/api/queryKeys';
import type { ActivityEventRead, Paginated } from '@/shared/api/types';
import { listProjectActivity, listTaskActivity } from './api';

/**
 * Query the project activity feed.
 *
 * @param projectId project id.
 * @param page page number.
 * @returns paginated activity query result.
 */
export function useProjectActivity(
  projectId: number | undefined,
  page = 1,
): UseQueryResult<Paginated<ActivityEventRead>> {
  return useQuery({
    queryKey: [...queryKeys.projectActivity(projectId ?? 0), page],
    queryFn: () => listProjectActivity(projectId as number, page),
    enabled: projectId !== undefined,
  });
}

/**
 * Query the activity feed of a single task.
 *
 * @param taskId task id.
 * @param page page number.
 * @returns paginated activity query result.
 */
export function useTaskActivity(
  taskId: number | undefined,
  page = 1,
): UseQueryResult<Paginated<ActivityEventRead>> {
  return useQuery({
    queryKey: [...queryKeys.taskActivity(taskId ?? 0), page],
    queryFn: () => listTaskActivity(taskId as number, page),
    enabled: taskId !== undefined,
  });
}
