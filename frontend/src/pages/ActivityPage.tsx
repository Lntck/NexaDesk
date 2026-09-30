/** Project activity feed page: paginated history of all changes. */

import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { History } from 'lucide-react';
import { useProject } from '@/entities/project/hooks';
import { useProjectActivity } from '@/entities/activity/hooks';
import { activityText } from '@/entities/activity/model';
import { useProjectLiveUpdates } from '@/features/live/hooks';
import { formatRelative } from '@/shared/lib/format';
import { Avatar, EmptyState, PageHeader, Pagination, Skeleton } from '@/shared/ui';

/**
 * Render the project activity history.
 *
 * @returns activity page element.
 */
export function ActivityPage() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const projectQueryId = Number.isFinite(id) ? id : undefined;
  const { data: project } = useProject(projectQueryId);
  const [page, setPage] = useState(1);
  const { data, isLoading } = useProjectActivity(projectQueryId, page);
  useProjectLiveUpdates(projectQueryId);

  const items = data?.items ?? [];

  return (
    <>
      <PageHeader
        title={project ? `${project.name} activity` : 'Activity'}
        description="Everything that happened in the project, newest first."
      />

      {isLoading ? (
        <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
          <Skeleton height={40} radius="var(--radius-sm)" />
          <Skeleton height={40} radius="var(--radius-sm)" />
          <Skeleton height={40} radius="var(--radius-sm)" />
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={<History size={24} />}
          title="No activity yet"
          text="Changes to tasks, members and settings will appear here."
        />
      ) : (
        <ul
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-2)',
            listStyle: 'none',
            padding: 0,
            margin: 0,
          }}
        >
          {items.map((event) => (
            <li
              key={event.id}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 'var(--space-3)',
                padding: 'var(--space-3)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-surface)',
                fontSize: 'var(--font-size-14)',
              }}
            >
              {event.actor && <Avatar username={event.actor.username} size="sm" />}
              <span style={{ color: 'var(--color-text-secondary)' }}>
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
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'var(--space-4)' }}>
          <Pagination page={page} pageSize={data.page_size} total={data.total} onChange={setPage} />
        </div>
      )}
    </>
  );
}
