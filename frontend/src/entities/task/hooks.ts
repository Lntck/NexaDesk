/** TanStack Query hooks for tasks and the kanban board. */

import { useMutation, useQuery, useQueryClient, type UseQueryResult } from '@tanstack/react-query';
import { queryKeys } from '@/shared/api/queryKeys';
import type {
  BoardRead,
  Paginated,
  TaskCreate,
  TaskListItem,
  TaskPatch,
  TaskRead,
  TaskReorder,
} from '@/shared/api/types';
import {
  assignTask,
  createTask,
  deleteTask,
  getBoard,
  getTask,
  listProjectTasks,
  patchTask,
  reorderTask,
  transitionTask,
  unassignTask,
} from './api';
import type { ProjectTasksFilters } from './model';

/**
 * Query the kanban board of a project.
 *
 * @param projectId project id.
 * @returns board query result.
 */
export function useBoard(projectId: number | undefined): UseQueryResult<BoardRead> {
  return useQuery({
    queryKey: queryKeys.board(projectId ?? 0),
    queryFn: () => getBoard(projectId as number),
    enabled: projectId !== undefined,
  });
}

/**
 * Query a filtered, paginated task list of a project.
 *
 * @param projectId project id.
 * @param filters active filters.
 * @returns paginated task list query result.
 */
export function useProjectTasks(
  projectId: number | undefined,
  filters: ProjectTasksFilters,
): UseQueryResult<Paginated<TaskListItem>> {
  return useQuery({
    queryKey: queryKeys.tasks(projectId ?? 0, filters),
    queryFn: () => listProjectTasks(projectId as number, filters),
    enabled: projectId !== undefined,
    placeholderData: (previous) => previous,
  });
}

/**
 * Query a single task.
 *
 * @param taskId task id.
 * @returns task details query result.
 */
export function useTask(taskId: number | undefined): UseQueryResult<TaskRead> {
  return useQuery({
    queryKey: queryKeys.task(taskId ?? 0),
    queryFn: () => getTask(taskId as number),
    enabled: taskId !== undefined,
  });
}

/**
 * Create a task and refresh board and list caches.
 *
 * @returns create mutation.
 */
export function useCreateTask() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, body }: { projectId: number; body: TaskCreate }) =>
      createTask(projectId, body),
    onSuccess: (task) => {
      void client.invalidateQueries({ queryKey: ['project', task.project_id] });
      void client.invalidateQueries({ queryKey: queryKeys.board(task.project_id) });
    },
  });
}

/**
 * Patch a task and refresh its caches.
 *
 * @returns patch mutation carrying the task version for If-Match.
 */
export function useUpdateTask() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, body, version }: { taskId: number; body: TaskPatch; version: number }) =>
      patchTask(taskId, body, version),
    onSuccess: (task) => {
      void client.invalidateQueries({ queryKey: queryKeys.task(task.id) });
      void client.invalidateQueries({ queryKey: ['project', task.project_id] });
    },
  });
}

/**
 * Soft-delete a task and refresh project caches.
 *
 * @returns delete mutation carrying the task version for If-Match.
 */
export function useDeleteTask() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, version }: { taskId: number; version: number }) =>
      deleteTask(taskId, version),
    onSuccess: (_data, variables) => {
      void client.invalidateQueries({ queryKey: queryKeys.task(variables.taskId) });
      void client.invalidateQueries({ queryKey: ['project'] });
    },
  });
}

/**
 * Move a task to an adjacent column and refresh the board.
 *
 * @returns transition mutation.
 */
export function useTransitionTask() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, statusId }: { taskId: number; statusId: number }) =>
      transitionTask(taskId, statusId),
    onSuccess: (result, variables) => {
      void client.invalidateQueries({ queryKey: queryKeys.task(variables.taskId) });
      void client.invalidateQueries({ queryKey: ['project'] });
      void result;
    },
  });
}

/**
 * Assign a task to a project member.
 *
 * @returns assign mutation.
 */
export function useAssignTask() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, userId }: { taskId: number; userId: number }) =>
      assignTask(taskId, userId),
    onSuccess: (_result, variables) => {
      void client.invalidateQueries({ queryKey: queryKeys.task(variables.taskId) });
      void client.invalidateQueries({ queryKey: ['project'] });
    },
  });
}

/**
 * Remove the assignee of a task.
 *
 * @returns unassign mutation.
 */
export function useUnassignTask() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId }: { taskId: number }) => unassignTask(taskId),
    onSuccess: (_result, variables) => {
      void client.invalidateQueries({ queryKey: queryKeys.task(variables.taskId) });
      void client.invalidateQueries({ queryKey: ['project'] });
    },
  });
}

/**
 * Reorder a card on the board.
 *
 * The board cache is refreshed after the server recalculates ranks.
 *
 * @returns reorder mutation.
 */
export function useReorderTask() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, body }: { taskId: number; body: TaskReorder }) =>
      reorderTask(taskId, body),
    onSuccess: (result) => {
      void client.invalidateQueries({ queryKey: queryKeys.board(0) });
      void client.invalidateQueries({ queryKey: ['project'] });
      void result;
    },
  });
}
