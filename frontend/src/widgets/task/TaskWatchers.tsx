/** Task watchers block: avatars, watch toggle and admin removal. */

import { Eye, EyeOff, X } from 'lucide-react';
import type { UserRead, WatcherRead } from '@/shared/api/types';
import { Avatar, Button, Tooltip } from '@/shared/ui';
import styles from './TaskPanel.module.css';

/** Props of the TaskWatchers component. */
export interface TaskWatchersProps {
  /** Users watching the task. */
  watchers: WatcherRead[];
  /** Current user, to detect own watch state. */
  me: UserRead | null;
  /** Whether the current user can edit the task. */
  canEdit: boolean;
  /** Whether the current user manages the project. */
  canManage: boolean;
  /** Watch toggle in flight. */
  pending: boolean;
  /** Called to watch or unwatch the task. */
  onToggle: () => void;
  /** Called to remove another watcher. */
  onRemove: (userId: number) => void;
}

/**
 * Render the watcher avatars and watch controls.
 *
 * @param props watcher list, permissions and handlers.
 * @returns rendered watchers block.
 */
export function TaskWatchers({
  watchers,
  me,
  canEdit,
  canManage,
  pending,
  onToggle,
  onRemove,
}: TaskWatchersProps) {
  const watching = me !== null && watchers.some((watcher) => watcher.user.id === me.id);

  return (
    <div>
      <div className={styles.watchers}>
        {watchers.map((watcher) => (
          <span key={watcher.user.id} className={styles.watcherChip}>
            <Avatar username={watcher.user.username} size="sm" />
            {watcher.user.username}
            {canManage && me?.id !== watcher.user.id && (
              <Tooltip label="Remove watcher">
                <button
                  type="button"
                  className={styles.labelRemove}
                  onClick={() => onRemove(watcher.user.id)}
                  aria-label={`Remove watcher ${watcher.user.username}`}
                >
                  <X size={12} />
                </button>
              </Tooltip>
            )}
          </span>
        ))}
        {watchers.length === 0 && (
          <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-13)' }}>
            Nobody is watching this task
          </span>
        )}
      </div>
      {canEdit && (
        <div>
          <Button
            size="sm"
            variant={watching ? 'secondary' : 'ghost'}
            icon={watching ? <EyeOff size={15} /> : <Eye size={15} />}
            loading={pending}
            onClick={onToggle}
          >
            {watching ? 'Unwatch' : 'Watch'}
          </Button>
        </div>
      )}
    </div>
  );
}
