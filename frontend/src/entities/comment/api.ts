/** REST calls for task comments. */

import { apiRequest, withQuery } from '@/shared/api/client';
import type { CommentCreate, CommentPatch, CommentRead, Paginated } from '@/shared/api/types';

/**
 * List comments of a task.
 *
 * @param taskId task id.
 * @param page page number.
 * @returns paginated comment list.
 */
export function listComments(taskId: number, page = 1): Promise<Paginated<CommentRead>> {
  return apiRequest('GET', withQuery(`/api/v1/tasks/${taskId}/comments`, { page, page_size: 50 }));
}

/**
 * Create a comment; @mentions are parsed server-side.
 *
 * @param taskId task id.
 * @param body comment text.
 * @returns the created comment.
 */
export function createComment(taskId: number, body: CommentCreate): Promise<CommentRead> {
  return apiRequest('POST', `/api/v1/tasks/${taskId}/comments`, { body });
}

/**
 * Edit a comment.
 *
 * @param commentId comment id.
 * @param body new comment text.
 * @returns the updated comment.
 */
export function patchComment(commentId: number, body: CommentPatch): Promise<CommentRead> {
  return apiRequest('PATCH', `/api/v1/comments/${commentId}`, { body });
}

/**
 * Soft-delete a comment.
 *
 * @param commentId comment id.
 */
export function deleteComment(commentId: number): Promise<void> {
  return apiRequest('DELETE', `/api/v1/comments/${commentId}`);
}
