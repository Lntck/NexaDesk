/**
 * Typed aliases for every schema of the backend OpenAPI contract.
 *
 * The aliases are generated on top of `schema.d.ts` (npm run gen:api), so the
 * client always speaks the contract from frontend/openapi.json.
 */

import type { components } from './schema';

export type Role = components['schemas']['Role'];
export type ProjectRole = components['schemas']['ProjectRole'];
export type Priority = components['schemas']['Priority'];
export type ActivityEventType = components['schemas']['ActivityEventType'];
export type NotificationType = components['schemas']['NotificationType'];

export type UserRead = components['schemas']['UserRead'];
export type UserBrief = components['schemas']['UserBrief'];
export type UserRegister = components['schemas']['UserRegister'];
export type Token = components['schemas']['Token'];

export type ProjectListItem = components['schemas']['ProjectListItem'];
export type ProjectRead = components['schemas']['ProjectRead'];
export type ProjectCreated = components['schemas']['ProjectCreated'];
export type ProjectCreate = components['schemas']['ProjectCreate'];
export type ProjectPatch = components['schemas']['ProjectPatch'];

export type MemberRead = components['schemas']['MemberRead'];
export type MemberList = components['schemas']['MemberList'];
export type MemberAdd = components['schemas']['MemberAdd'];

export type TaskStatusRead = components['schemas']['TaskStatusRead'];
export type TaskStatusBrief = components['schemas']['TaskStatusBrief'];
export type TaskStatusCreate = components['schemas']['TaskStatusCreate'];
export type TaskStatusPatch = components['schemas']['TaskStatusPatch'];

export type TaskListItem = components['schemas']['TaskListItem'];
export type TaskRead = components['schemas']['TaskRead'];
export type TaskCreate = components['schemas']['TaskCreate'];
export type TaskPatch = components['schemas']['TaskPatch'];
export type TaskReorder = components['schemas']['TaskReorder'];
export type TaskPositionRead = components['schemas']['TaskPositionRead'];
export type TaskTransitionRead = components['schemas']['TaskTransitionRead'];
export type TaskAssignRead = components['schemas']['TaskAssignRead'];

export type BoardCard = components['schemas']['BoardCard'];
export type BoardColumn = components['schemas']['BoardColumn'];
export type BoardRead = components['schemas']['BoardRead'];

export type CommentRead = components['schemas']['CommentRead'];
export type CommentCreate = components['schemas']['CommentCreate'];
export type CommentPatch = components['schemas']['CommentPatch'];

export type LabelRead = components['schemas']['LabelRead'];
export type LabelCreate = components['schemas']['LabelCreate'];
export type LabelPatch = components['schemas']['LabelPatch'];

export type WatcherRead = components['schemas']['WatcherRead'];

export type NotificationRead = components['schemas']['NotificationRead'];

export type ActivityEventRead = components['schemas']['ActivityEventRead'];

/** Standard collection envelope used by all paginated endpoints. */
export interface Paginated<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

/** Realtime event envelope delivered over the project SSE stream. */
export interface RealtimeEvent {
  id: string;
  type: string;
  project_id: number | null;
  task_id: number | null;
  actor: { id: number; username: string } | null;
  recipient_id: number | null;
  timestamp: string;
  data: Record<string, unknown>;
}
