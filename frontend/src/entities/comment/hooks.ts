/** TanStack Query hooks for task comments. */

import { useMutation, useQuery, useQueryClient, type UseQueryResult } from '@tanstack/react-query';
import { queryKeys } from '@/shared/api/queryKeys';
import type { CommentCreate, CommentPatch, CommentRead, Paginated } from '@/shared/api/types';
import { getSessionUser } from '@/entities/session/model';
import { createComment, deleteComment, listComments, patchComment } from './api';

/**
 * Query one page of comments of a task.
 *
 * @param taskId task id.
 * @param page page number.
 * @returns paginated comment list query result.
 */
export function useComments(
  taskId: number | undefined,
  page = 1,
): UseQueryResult<Paginated<CommentRead>> {
  return useQuery({
    queryKey: [...queryKeys.comments(taskId ?? 0), page],
    queryFn: () => listComments(taskId as number, page),
    enabled: taskId !== undefined,
  });
}

/**
 * Create a comment on a task.
 *
 * The new comment is inserted into the open page cache immediately and rolled
 * back when the request fails.
 *
 * @returns create comment mutation.
 */
export function useCreateComment() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, body }: { taskId: number; body: CommentCreate; page?: number }) =>
      createComment(taskId, body),
    onMutate: async ({ taskId, body, page = 1 }) => {
      const queryKey = [...queryKeys.comments(taskId), page];
      await client.cancelQueries({ queryKey });
      const snapshot = client.getQueryData<Paginated<CommentRead>>(queryKey);
      const user = getSessionUser();
      if (snapshot && user) {
        const optimistic: CommentRead = {
          id: -Date.now(),
          task_id: taskId,
          author: { id: user.id, username: user.username },
          body: body.body,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        client.setQueryData<Paginated<CommentRead>>(queryKey, {
          ...snapshot,
          items: [...snapshot.items, optimistic],
          total: snapshot.total + 1,
        });
      }
      return { taskId, page, snapshot };
    },
    onError: (_error, _variables, context) => {
      if (!context?.snapshot) return;
      client.setQueryData([...queryKeys.comments(context.taskId), context.page], context.snapshot);
    },
    onSuccess: (_comment, variables) => {
      void client.invalidateQueries({ queryKey: queryKeys.comments(variables.taskId) });
      void client.invalidateQueries({ queryKey: queryKeys.task(variables.taskId) });
    },
  });
}

/**
 * Edit a comment.
 *
 * @returns patch comment mutation.
 */
export function useUpdateComment() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ commentId, body }: { commentId: number; body: CommentPatch; taskId: number }) =>
      patchComment(commentId, body),
    onSuccess: (_comment, variables) =>
      client.invalidateQueries({ queryKey: queryKeys.comments(variables.taskId) }),
  });
}

/**
 * Soft-delete a comment.
 *
 * @returns delete comment mutation.
 */
export function useDeleteComment() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ commentId }: { commentId: number; taskId: number }) => deleteComment(commentId),
    onSuccess: (_data, variables) => {
      void client.invalidateQueries({ queryKey: queryKeys.comments(variables.taskId) });
      void client.invalidateQueries({ queryKey: queryKeys.task(variables.taskId) });
    },
  });
}
