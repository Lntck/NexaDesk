/** Task activity feed: history of one task. */

import { History } from 'lucide-react';
import { useTaskActivity } from '@/entities/activity/hooks';
import { activityText } from '@/entities/activity/model';
import { formatRelative } from '@/shared/lib/format';
import { Avatar, CenteredSpinner, EmptyState, Pagination } from '@/shared/ui';
import { useState } from 'react';
import styles from './TaskPanel.module.css';

/** Props of the TaskActivity component. */
export interface TaskActivityProps {
  /** Task to show history for. */
  taskId: number;
}

/**
 * Render the paginated activity history of a task.
 *
 * @param props task id.
 * @returns rendered activity feed.
 */
export function TaskActivity({ taskId }: TaskActivityProps) {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useTaskActivity(taskId, page);
  const items = data?.items ?? [];

  return (
    <section className={styles.section}>
      <h3 className={styles.sectionTitle}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <History size={16} /> History
        </span>
      </h3>

      {isLoading ? (
        <CenteredSpinner size={22} />
      ) : items.length === 0 ? (
        <EmptyState icon={<History size={22} />} title="No history yet" />
      ) : (
        <ul style={{ display: 'grid', gap: 'var(--space-2)' }}>
          {items.map((event) => (
            <li
              key={event.id}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 'var(--space-2)',
                fontSize: 'var(--font-size-13)',
                color: 'var(--color-text-secondary)',
              }}
            >
              {event.actor && <Avatar username={event.actor.username} size="sm" />}
              <span>
                {event.actor && (
                  <strong style={{ color: 'var(--color-text)' }}>{event.actor.username}</strong>
                )}{' '}
                {activityText(event)}
                <span style={{ color: 'var(--color-text-muted)' }}>
                  {' '}
                  &middot;&nbsp;{formatRelative(event.created_at)}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}

      {data && data.total > data.page_size && (
        <Pagination page={page} pageSize={data.page_size} total={data.total} onChange={setPage} />
      )}
    </section>
  );
}
