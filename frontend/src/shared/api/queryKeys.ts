/**
 * Central TanStack Query key factory.
 *
 * All caches share this factory so realtime event handlers can invalidate or
 * rewrite exactly the queries a screen is using.
 */

import type { ProjectTasksFilters } from '@/entities/task/model';

/** Query key factory for every server cache in the app. */
export const queryKeys = {
  /** Current user profile. */
  me: () => ['me'] as const,
  /** Project list with client filters applied. */
  projects: (filters: { search?: string; archived?: boolean }) => ['projects', filters] as const,
  /** Single project details. */
  project: (projectId: number) => ['project', projectId] as const,
  /** Project members. */
  members: (projectId: number) => ['project', projectId, 'members'] as const,
  /** Board statuses of a project. */
  statuses: (projectId: number) => ['project', projectId, 'statuses'] as const,
  /** Project labels. */
  labels: (projectId: number) => ['project', projectId, 'labels'] as const,
  /** Kanban board. */
  board: (projectId: number) => ['project', projectId, 'board'] as const,
  /** Filtered task list of a project. */
  tasks: (projectId: number, filters: ProjectTasksFilters) =>
    ['project', projectId, 'tasks', filters] as const,
  /** Single task details. */
  task: (taskId: number) => ['task', taskId] as const,
  /** Comments of a task. */
  comments: (taskId: number) => ['task', taskId, 'comments'] as const,
  /** Watchers of a task. */
  watchers: (taskId: number) => ['task', taskId, 'watchers'] as const,
  /** Activity of a task. */
  taskActivity: (taskId: number) => ['task', taskId, 'activity'] as const,
  /** Activity of a project. */
  projectActivity: (projectId: number) => ['project', projectId, 'activity'] as const,
  /** Notification list; filter is the read-state query value. */
  notifications: (read: boolean | null) => ['notifications', { read }] as const,
  /** Every notification cache: lists, pages and the unread counter. */
  notificationsRoot: () => ['notifications'] as const,
  /** Project members cached for mention autocomplete. */
  mentionable: (projectId: number) => ['project', projectId, 'members'] as const,
};
