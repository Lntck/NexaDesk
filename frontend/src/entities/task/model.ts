/** Task domain types shared across the app. */

import type { Priority } from '@/shared/api/types';

/** Filter set supported by the project task list endpoint. */
export interface ProjectTasksFilters {
  /** Text search inside the task title. */
  search?: string;
  /** Status key filter. */
  status?: string;
  /** Priority filter. */
  priority?: Priority | '';
  /** Assignee user id filter. */
  assignee_id?: number | '';
  /** Creator user id filter. */
  creator_id?: number | '';
  /** Due date upper bound (ISO date). */
  due_before?: string;
  /** Due date lower bound (ISO date). */
  due_after?: string;
  /** Sort expression accepted by the API. */
  sort?: string;
  /** Page number. */
  page?: number;
  /** Page size. */
  page_size?: number;
}

/** Priority metadata for badges and selects. */
export const PRIORITY_META: Record<Priority, { label: string; color: string; soft: string }> = {
  LOW: {
    label: 'Low',
    color: 'var(--color-priority-low)',
    soft: 'var(--color-priority-low-soft)',
  },
  MEDIUM: {
    label: 'Medium',
    color: 'var(--color-priority-medium)',
    soft: 'var(--color-priority-medium-soft)',
  },
  HIGH: {
    label: 'High',
    color: 'var(--color-priority-high)',
    soft: 'var(--color-priority-high-soft)',
  },
  CRITICAL: {
    label: 'Critical',
    color: 'var(--color-priority-critical)',
    soft: 'var(--color-priority-critical-soft)',
  },
};

/** All priorities in ascending severity order. */
export const PRIORITY_ORDER: Priority[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
