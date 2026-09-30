/**
 * Task list filter bar.
 *
 * Renders the controls for every filter supported by the project task list
 * endpoint (docs/api-endpoints.md, section on GET /projects/{id}/tasks) and
 * reports changes back as a partial filter patch.
 */

import { RotateCcw } from 'lucide-react';
import type { MemberRead, Priority, TaskStatusRead } from '@/shared/api/types';
import { PRIORITY_META, PRIORITY_ORDER, type ProjectTasksFilters } from '@/entities/task/model';
import { Button, Input, Select } from '@/shared/ui';
import styles from './TaskFilters.module.css';

/** Sort keys offered in the filter bar. */
const SORT_OPTIONS: Array<{ value: string; label: string }> = [
  { value: '-updated_at', label: 'Recently updated' },
  { value: '-created_at', label: 'Recently created' },
  { value: 'title', label: 'Title A-Z' },
  { value: '-priority', label: 'Priority' },
  { value: '-due_date', label: 'Due date' },
];

/** Props of the TaskFilters component. */
export interface TaskFiltersProps {
  /** Currently applied filters. */
  filters: ProjectTasksFilters;
  /** Called with the changed filter fields. */
  onChange: (patch: Partial<ProjectTasksFilters>) => void;
  /** Project members for the assignee filter. */
  members: MemberRead[];
  /** Board statuses for the status filter. */
  statuses: TaskStatusRead[];
  /** Whether at least one filter is set. */
  dirty: boolean;
}

/**
 * Render the task filter bar.
 *
 * @param props filter state, change handler and option lists.
 * @returns rendered filter controls.
 */
export function TaskFilters({ filters, onChange, members, statuses, dirty }: TaskFiltersProps) {
  return (
    <div className={styles.filters}>
      <div className={styles.search}>
        <Input
          placeholder="Search by title"
          value={filters.search ?? ''}
          onChange={(event) => onChange({ search: event.target.value || undefined, page: 1 })}
        />
      </div>

      <div className={styles.control}>
        <Select
          aria-label="Status filter"
          value={filters.status ?? ''}
          onChange={(event) => onChange({ status: event.target.value || undefined, page: 1 })}
        >
          <option value="">Any status</option>
          {statuses.map((status) => (
            <option key={status.id} value={status.key}>
              {status.name}
            </option>
          ))}
        </Select>
      </div>

      <div className={styles.control}>
        <Select
          aria-label="Priority filter"
          value={filters.priority ?? ''}
          onChange={(event) =>
            onChange({
              priority: (event.target.value || undefined) as Priority | undefined,
              page: 1,
            })
          }
        >
          <option value="">Any priority</option>
          {PRIORITY_ORDER.map((value) => (
            <option key={value} value={value}>
              {PRIORITY_META[value].label}
            </option>
          ))}
        </Select>
      </div>

      <div className={styles.control}>
        <Select
          aria-label="Assignee filter"
          value={filters.assignee_id ?? ''}
          onChange={(event) =>
            onChange({
              assignee_id: event.target.value ? Number(event.target.value) : undefined,
              page: 1,
            })
          }
        >
          <option value="">Anyone</option>
          {members.map((member) => (
            <option key={member.user.id} value={member.user.id}>
              {member.user.username}
            </option>
          ))}
        </Select>
      </div>

      <div className={styles.control}>
        <Input
          aria-label="Due before"
          type="date"
          value={filters.due_before ?? ''}
          onChange={(event) => onChange({ due_before: event.target.value || undefined, page: 1 })}
        />
      </div>

      <div className={styles.control}>
        <Select
          aria-label="Sort order"
          value={filters.sort ?? '-updated_at'}
          onChange={(event) => onChange({ sort: event.target.value, page: 1 })}
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
      </div>

      {dirty && (
        <div className={styles.reset}>
          <Button
            variant="ghost"
            icon={<RotateCcw size={15} />}
            onClick={() =>
              onChange({
                search: undefined,
                status: undefined,
                priority: undefined,
                assignee_id: undefined,
                due_before: undefined,
                sort: '-updated_at',
                page: 1,
              })
            }
          >
            Reset
          </Button>
        </div>
      )}
    </div>
  );
}
