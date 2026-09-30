/** TanStack Query hooks for board statuses and project labels. */

import { useMutation, useQuery, useQueryClient, type UseQueryResult } from '@tanstack/react-query';
import { queryKeys } from '@/shared/api/queryKeys';
import type {
  LabelCreate,
  LabelPatch,
  LabelRead,
  TaskStatusCreate,
  TaskStatusPatch,
  TaskStatusRead,
} from '@/shared/api/types';
import {
  createLabel,
  createStatus,
  deleteLabel,
  deleteStatus,
  listLabels,
  listStatuses,
  patchLabel,
  patchStatus,
} from './api';

/**
 * Query board statuses of a project.
 *
 * @param projectId project id.
 * @returns status list query result.
 */
export function useStatuses(projectId: number | undefined): UseQueryResult<TaskStatusRead[]> {
  return useQuery({
    queryKey: queryKeys.statuses(projectId ?? 0),
    queryFn: () => listStatuses(projectId as number),
    enabled: projectId !== undefined,
  });
}

/**
 * Create a board status.
 *
 * @returns create status mutation.
 */
export function useCreateStatus() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, body }: { projectId: number; body: TaskStatusCreate }) =>
      createStatus(projectId, body),
    onSuccess: (_status, variables) => {
      void client.invalidateQueries({ queryKey: queryKeys.statuses(variables.projectId) });
      void client.invalidateQueries({ queryKey: queryKeys.board(variables.projectId) });
    },
  });
}

/**
 * Update a board status.
 *
 * @returns patch status mutation.
 */
export function useUpdateStatus() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      statusId,
      body,
    }: {
      projectId: number;
      statusId: number;
      body: TaskStatusPatch;
    }) => patchStatus(projectId, statusId, body),
    onSuccess: (_status, variables) => {
      void client.invalidateQueries({ queryKey: queryKeys.statuses(variables.projectId) });
      void client.invalidateQueries({ queryKey: queryKeys.board(variables.projectId) });
    },
  });
}

/**
 * Delete a board status.
 *
 * @returns delete status mutation.
 */
export function useDeleteStatus() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, statusId }: { projectId: number; statusId: number }) =>
      deleteStatus(projectId, statusId),
    onSuccess: (_data, variables) => {
      void client.invalidateQueries({ queryKey: queryKeys.statuses(variables.projectId) });
      void client.invalidateQueries({ queryKey: queryKeys.board(variables.projectId) });
    },
  });
}

/**
 * Query project labels.
 *
 * @param projectId project id.
 * @returns label list query result.
 */
export function useLabels(projectId: number | undefined): UseQueryResult<LabelRead[]> {
  return useQuery({
    queryKey: queryKeys.labels(projectId ?? 0),
    queryFn: () => listLabels(projectId as number),
    enabled: projectId !== undefined,
  });
}

/**
 * Create a project label.
 *
 * @returns create label mutation.
 */
export function useCreateLabel() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, body }: { projectId: number; body: LabelCreate }) =>
      createLabel(projectId, body),
    onSuccess: (_label, variables) =>
      client.invalidateQueries({ queryKey: queryKeys.labels(variables.projectId) }),
  });
}

/**
 * Update a project label.
 *
 * @returns patch label mutation.
 */
export function useUpdateLabel() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      labelId,
      body,
    }: {
      projectId: number;
      labelId: number;
      body: LabelPatch;
    }) => patchLabel(projectId, labelId, body),
    onSuccess: (_label, variables) =>
      client.invalidateQueries({ queryKey: queryKeys.labels(variables.projectId) }),
  });
}

/**
 * Delete a project label.
 *
 * @returns delete label mutation.
 */
export function useDeleteLabel() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, labelId }: { projectId: number; labelId: number }) =>
      deleteLabel(projectId, labelId),
    onSuccess: (_data, variables) =>
      client.invalidateQueries({ queryKey: queryKeys.labels(variables.projectId) }),
  });
}
