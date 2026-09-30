/** Project task list page: filters, table and the task drawer. */

import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ListFilter, Plus } from 'lucide-react';
import { useProject, useProjectRole } from '@/entities/project/hooks';
import { projectPermissions } from '@/entities/project/model';
import { useProjectTasks } from '@/entities/task/hooks';
import { PRIORITY_META, type ProjectTasksFilters } from '@/entities/task/model';
import { useMembers } from '@/entities/member/hooks';
import { useStatuses } from '@/entities/status/hooks';
import { useProjectLiveUpdates } from '@/features/live/hooks';
import { TaskFilters } from '@/features/filters/TaskFilters';
import { TaskCreateModal } from '@/features/task/TaskCreateModal';
import { TaskDrawer } from '@/widgets/task/TaskDrawer';
import { formatDateTime } from '@/shared/lib/format';
import { Avatar, Badge, Button, EmptyState, PageHeader, Pagination, Skeleton } from '@/shared/ui';
import styles from './TasksPage.module.css';

/** Initial sort of the task list. */
const DEFAULT_SORT = '-updated_at';

/**
 * Render the filtered task list of a project.
 *
 * @returns tasks page element.
 */
export function TasksPage() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const { data: project } = useProject(Number.isFinite(id) ? id : undefined);
  const role = useProjectRole(project?.id);
  const permissions = projectPermissions(role);
  const { data: members } = useMembers(project?.id);
  const { data: statuses } = useStatuses(project?.id);
  useProjectLiveUpdates(project?.id);

  const [filters, setFilters] = useState<ProjectTasksFilters>({ sort: DEFAULT_SORT });
  const [openTaskId, setOpenTaskId] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const { data, isLoading } = useProjectTasks(project?.id, filters);

  const dirty = useMemo(
    () =>
      Boolean(
        filters.search ||
        filters.status ||
        filters.priority ||
        filters.assignee_id ||
        filters.due_before,
      ),
    [filters],
  );

  /**
   * Merge a partial filter patch into the current filter state.
   *
   * @param patch changed filter fields.
   */
  const handleFilterChange = (patch: Partial<ProjectTasksFilters>) => {
    setFilters((current) => ({ ...current, ...patch }));
  };

  return (
    <>
      <PageHeader
        title={project ? `${project.name} tasks` : 'Tasks'}
        description="All tasks of the project with filters and sorting."
        actions={
          permissions.canEditTasks && (
            <Button variant="primary" icon={<Plus size={16} />} onClick={() => setCreateOpen(true)}>
              New task
            </Button>
          )
        }
      />

      <TaskFilters
        filters={filters}
        onChange={handleFilterChange}
        members={members?.items ?? []}
        statuses={statuses ?? []}
        dirty={dirty}
      />

      {isLoading ? (
        <div style={{ display: 'grid', gap: 'var(--space-2)' }}>
          <Skeleton height={44} radius="var(--radius-sm)" />
          <Skeleton height={44} radius="var(--radius-sm)" />
          <Skeleton height={44} radius="var(--radius-sm)" />
        </div>
      ) : (data?.items.length ?? 0) === 0 ? (
        <EmptyState
          icon={<ListFilter size={24} />}
          title={dirty ? 'Nothing matches the filters' : 'No tasks yet'}
          text={dirty ? 'Try removing some filters.' : 'Create the first task to fill the board.'}
        />
      ) : (
        <div className={styles.table}>
          <div className={`${styles.row} ${styles.head}`}>
            <span>Key</span>
            <span>Title</span>
            <span>Status</span>
            <span>Priority</span>
            <span>Assignee</span>
            <span>Updated</span>
          </div>
          {(data?.items ?? []).map((task) => (
            <div
              key={task.id}
              className={styles.row}
              role="button"
              tabIndex={0}
              onClick={() => setOpenTaskId(task.id)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') setOpenTaskId(task.id);
              }}
            >
              <span className={styles.key}>{task.key}</span>
              <span>{task.title}</span>
              <span>{task.status.name}</span>
              <Badge tone="neutral" style={{ color: PRIORITY_META[task.priority].color }}>
                {PRIORITY_META[task.priority].label}
              </Badge>
              <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                {task.assignee ? (
                  <>
                    <Avatar username={task.assignee.username} size="sm" />
                    {task.assignee.username}
                  </>
                ) : (
                  <span style={{ color: 'var(--color-text-muted)' }}>Unassigned</span>
                )}
              </span>
              <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-13)' }}>
                {formatDateTime(task.updated_at)}
              </span>
            </div>
          ))}
        </div>
      )}

      {data && data.total > data.page_size && (
        <div className={styles.footer}>
          <Pagination
            page={filters.page ?? 1}
            pageSize={data.page_size}
            total={data.total}
            onChange={(page) => handleFilterChange({ page })}
          />
        </div>
      )}

      <TaskDrawer taskId={openTaskId} onClose={() => setOpenTaskId(null)} />
      {project && (
        <TaskCreateModal
          open={createOpen}
          projectId={project.id}
          onClose={() => setCreateOpen(false)}
          onCreated={(task) => {
            setCreateOpen(false);
            setOpenTaskId(task.id);
          }}
        />
      )}
    </>
  );
}
