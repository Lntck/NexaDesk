/** Task drawer: the task panel opened above the board or task list. */

import { useNavigate } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';
import { useTask } from '@/entities/task/hooks';
import { Button, Drawer, Tooltip } from '@/shared/ui';
import { TaskPanel } from './TaskPanel';

/** Props of the TaskDrawer component. */
export interface TaskDrawerProps {
  /** Task id to open; null closes the drawer. */
  taskId: number | null;
  /** Called on close requests. */
  onClose: () => void;
}

/**
 * Render the task panel inside a right-side drawer.
 *
 * @param props task id and close handler.
 * @returns drawer element or null when closed.
 */
export function TaskDrawer({ taskId, onClose }: TaskDrawerProps) {
  const navigate = useNavigate();
  const { data: task } = useTask(taskId ?? undefined);

  return (
    <Drawer
      open={taskId !== null}
      onClose={onClose}
      wide
      title={
        <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          {task ? task.key : 'Task'}
        </span>
      }
      actions={
        task && (
          <Tooltip label="Open as a shareable page">
            <Button
              variant="ghost"
              iconOnly
              icon={<ExternalLink size={16} />}
              aria-label="Open task page"
              onClick={() => navigate(`/tasks/${task.id}`)}
            />
          </Tooltip>
        )
      }
    >
      {taskId !== null && <TaskPanel taskId={taskId} onClose={onClose} embedded />}
    </Drawer>
  );
}
