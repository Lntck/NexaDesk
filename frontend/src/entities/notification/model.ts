/** Notification rendering: text and tone per notification type. */

import type { NotificationRead } from '@/shared/api/types';

/**
 * Render a notification as a short sentence.
 *
 * Uses the payload snapshot so the text survives task renames and deletes.
 *
 * @param notification notification record.
 * @returns human readable text.
 */
export function notificationText(notification: NotificationRead): string {
  const data = notification.data as Record<string, unknown>;
  const taskTitle =
    typeof data.task_title === 'string' ? data.task_title : (notification.task?.title ?? 'a task');
  const taskKey =
    typeof data.task_key === 'string' ? data.task_key : (notification.task?.key ?? '');
  const actor = notification.actor?.username ?? 'Someone';
  switch (notification.type) {
    case 'task.assigned':
      return `${actor} assigned "${taskTitle}" to you`;
    case 'comment.created':
      return `${actor} commented on ${taskKey}`;
    case 'comment.mentioned':
      return `${actor} mentioned you on ${taskKey}`;
    case 'task.status_changed':
      return `${actor} moved ${taskKey} to ${String(data.to ?? 'another column')}`;
    case 'task.updated':
      return `${actor} updated "${taskTitle}"`;
    case 'member.added':
      return `${actor} added you to ${typeof data.project_key === 'string' ? data.project_key : 'a project'}`;
    default:
      return 'You have a new notification';
  }
}

/**
 * Pick a destination route for a notification click.
 *
 * @param notification notification record.
 * @returns in-app route or null when the notice has no target.
 */
export function notificationTarget(notification: NotificationRead): string | null {
  const projectId = notification.project?.id ?? null;
  const taskId = notification.task?.id ?? null;
  if (taskId) return `/tasks/${taskId}`;
  if (projectId) return `/projects/${projectId}/board`;
  return null;
}
