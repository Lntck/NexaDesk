/** Standalone shareable task page. */

import { Badge } from '@/shared/ui';
import { hexToRgba } from '@/shared/lib/colors';
import { ArrowLeft } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { useTask } from '@/entities/task/hooks';
import { useProjectLiveUpdates } from '@/features/live/hooks';
import { Button, PageHeader, Skeleton } from '@/shared/ui';
import { TaskPanel } from '@/widgets/task/TaskPanel';

/**
 * Render the standalone shareable task page.
 *
 * The same panel as the board drawer, wrapped in the page layout.
 *
 * @returns task page element.
 */
export function TaskPage() {
  const { taskId } = useParams();
  const id = Number(taskId);
  const { data: task, isLoading } = useTask(id);
  const navigate = useNavigate();
  useProjectLiveUpdates(task?.project_id);

  return (
    <>
      <PageHeader
        title={isLoading ? 'Loading' : task ? `${task.key} ${task.title}` : 'Task not found'}
        meta={
          task && (
            <Badge
              tone="neutral"
              style={{
                backgroundColor: hexToRgba('#8AB4FF', 0.16),
                color: 'var(--color-text-secondary)',
              }}
            >
              {task.status.name}
            </Badge>
          )
        }
        actions={
          <Button
            variant="ghost"
            icon={<ArrowLeft size={16} />}
            onClick={() => navigate(task ? `/projects/${task.project_id}/board` : '/projects')}
          >
            Back to board
          </Button>
        }
      />
      {isLoading ? (
        <Skeleton height={420} radius="var(--radius-lg)" />
      ) : task ? (
        <TaskPanel taskId={task.id} />
      ) : (
        <p style={{ color: 'var(--color-text-muted)' }}>
          The task does not exist or you do not have access to it.
        </p>
      )}
    </>
  );
}
