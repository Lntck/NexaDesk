/**
 * Live project updates: one SSE stream per open project.
 *
 * Incoming frames are translated into TanStack Query cache updates and
 * notification toasts (frontend/PLAN.md, "Реалтайм и данные").
 */

import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ProjectEventStream } from '@/shared/api/sse';
import { queryKeys } from '@/shared/api/queryKeys';
import type { RealtimeEvent } from '@/shared/api/types';
import { getSessionUser } from '@/entities/session/model';
import { notificationText } from '@/entities/notification/model';
import type { NotificationRead } from '@/shared/api/types';
import { useToast } from '@/shared/ui/toastContext';

/**
 * Subscribe to the project event stream and sync query caches.
 *
 * Notification read-state is not broadcast over SSE, so after every reconnect
 * all notification caches are resynchronized from the API.
 *
 * @param projectId project id to subscribe to; undefined disables the stream.
 */
export function useProjectLiveUpdates(projectId: number | undefined): void {
  const client = useQueryClient();
  const toast = useToast();
  const projectIdRef = useRef(projectId);
  projectIdRef.current = projectId;

  useEffect(() => {
    if (projectId === undefined) return;
    let dropped = false;
    const stream = new ProjectEventStream({
      projectId,
      onEvent: (event) => handleEvent(event, projectId, client, toast.push),
      onStatusChange: (status) => {
        if (status === 'connected') {
          if (dropped) void client.invalidateQueries({ queryKey: queryKeys.notificationsRoot() });
          dropped = false;
        } else {
          dropped = true;
        }
      },
    });
    stream.start();
    return () => stream.stop();
  }, [projectId, client, toast]);
}

/**
 * Translate one realtime event into cache updates and toasts.
 *
 * @param event realtime event envelope.
 * @param projectId project the stream belongs to.
 * @param client query client used for invalidation.
 * @param pushToast toast push function for notification frames.
 */
function handleEvent(
  event: RealtimeEvent,
  projectId: number,
  client: ReturnType<typeof useQueryClient>,
  pushToast: (message: {
    title: string;
    text?: string;
    tone?: 'success' | 'error' | 'info';
  }) => number,
): void {
  const invalidate = (...keys: Array<readonly unknown[]>) => {
    for (const key of keys) void client.invalidateQueries({ queryKey: key });
  };

  switch (event.type) {
    case 'task.created':
    case 'task.updated':
    case 'task.deleted':
    case 'task.assigned':
    case 'task.unassigned':
    case 'task.status_changed':
    case 'task.moved':
      invalidate(
        queryKeys.board(projectId),
        ['project', projectId, 'tasks'],
        event.task_id ? queryKeys.task(event.task_id) : [],
      );
      void client.invalidateQueries({ queryKey: ['project', projectId] });
      break;
    case 'comment.created':
    case 'comment.updated':
    case 'comment.deleted':
      if (event.task_id) {
        invalidate(queryKeys.comments(event.task_id), queryKeys.task(event.task_id));
      }
      break;
    case 'member.added':
    case 'member.removed':
    case 'member.role_changed':
      invalidate(queryKeys.members(projectId), ['projects']);
      break;
    case 'label.added':
    case 'label.removed':
      invalidate(queryKeys.labels(projectId));
      if (event.task_id) invalidate(queryKeys.task(event.task_id));
      break;
    case 'watcher.added':
    case 'watcher.removed':
      if (event.task_id) {
        invalidate(queryKeys.watchers(event.task_id), queryKeys.task(event.task_id));
      }
      break;
    case 'project.updated':
    case 'project.archived':
    case 'project.restored':
      invalidate(queryKeys.project(projectId), ['projects']);
      break;
    case 'notification.created': {
      const user = getSessionUser();
      if (user && event.recipient_id === user.id) {
        invalidate(['notifications']);
        const notification = event.data as unknown as NotificationRead;
        pushToast({
          title: 'New notification',
          text: notificationText(notification),
          tone: 'info',
        });
      }
      break;
    }
    default:
      invalidate(queryKeys.projectActivity(projectId), queryKeys.board(projectId));
      break;
  }

  invalidate(queryKeys.projectActivity(projectId));
}
