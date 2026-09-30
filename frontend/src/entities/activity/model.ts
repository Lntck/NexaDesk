/**
 * Activity history rendering.
 *
 * Every activity event is turned into a short human readable sentence with a
 * stable structure: actor, action and target.
 */

import type { ActivityEventRead } from '@/shared/api/types';

/** Extra context for rendering events that only carry user ids. */
export interface ActivityTextOptions {
  /** User id to username lookup for member and assignment events. */
  usernames?: ReadonlyMap<number, string>;
}

/**
 * Read a string field from free-form event data.
 *
 * @param data event payload.
 * @param keys candidate field names in priority order.
 * @returns first present string value or undefined.
 */
function readString(data: Record<string, unknown>, ...keys: string[]): string | undefined {
  for (const key of keys) {
    const value = data[key];
    if (typeof value === 'string' && value !== '') return value;
  }
  return undefined;
}

/**
 * Render one activity event as readable text.
 *
 * Task events carry the task key as `key` (task service) or `task_key`
 * (comment, label and watcher services); both shapes are accepted.
 *
 * @param event activity history entry.
 * @param options optional username lookup for events with user ids.
 * @returns sentence describing the event.
 */
export function activityText(event: ActivityEventRead, options: ActivityTextOptions = {}): string {
  const data = event.data as Record<string, unknown>;
  const taskKey = readString(data, 'task_key', 'key') ?? 'a task';
  const taskTitle = readString(data, 'task_title', 'title') ?? '';
  const userId = typeof data.user_id === 'number' ? data.user_id : undefined;
  const resolvedUser = userId !== undefined ? options.usernames?.get(userId) : undefined;
  const userName =
    readString(data, 'username') ??
    resolvedUser ??
    (userId !== undefined ? `user #${userId}` : 'a user');
  const labelName = readString(data, 'label_name') ?? 'a label';
  const from = readString(data, 'from') ?? '';
  const to = readString(data, 'to') ?? '';
  const fields = Array.isArray(data.fields)
    ? (data.fields as unknown[]).filter((value): value is string => typeof value === 'string')
    : [];

  switch (event.type) {
    case 'project.created':
      return 'created the project';
    case 'project.updated':
      return fields.length > 0
        ? `updated the project (${fields.join(', ')})`
        : 'updated the project';
    case 'project.archived':
      return 'archived the project';
    case 'project.restored':
      return 'restored the project';
    case 'member.added':
      return `added ${userName} to the project`;
    case 'member.removed':
      return `removed ${userName} from the project`;
    case 'member.role_changed':
      return `changed the role of ${userName}${to ? ` to ${to}` : ''}`;
    case 'task.created':
      return `created ${taskKey}${taskTitle ? ` "${taskTitle}"` : ''}`;
    case 'task.updated':
      return fields.length > 0 ? `updated ${taskKey} (${fields.join(', ')})` : `updated ${taskKey}`;
    case 'task.deleted':
      return `deleted ${taskKey}`;
    case 'task.assigned':
      return `assigned ${taskKey} to ${readString(data, 'assignee_username') ?? userName}`;
    case 'task.unassigned':
      return `unassigned ${taskKey}`;
    case 'task.status_changed':
      return `moved ${taskKey} from ${from || '?'} to ${to || '?'}`;
    case 'task.moved':
      return `moved ${taskKey} to another project`;
    case 'comment.created':
      return `commented on ${taskKey}`;
    case 'comment.updated':
      return `edited a comment on ${taskKey}`;
    case 'comment.deleted':
      return `deleted a comment on ${taskKey}`;
    case 'comment.mentioned':
      return `mentioned someone in ${taskKey}`;
    case 'label.added':
      return `added label "${labelName}" to ${taskKey}`;
    case 'label.removed':
      return `removed label "${labelName}" from ${taskKey}`;
    case 'watcher.added':
      return `started watching ${taskKey}`;
    case 'watcher.removed':
      return `stopped watching ${taskKey}`;
    case 'relation.added':
      return `linked ${taskKey} with another task`;
    case 'relation.removed':
      return `removed a link from ${taskKey}`;
    default:
      return 'updated the project';
  }
}
