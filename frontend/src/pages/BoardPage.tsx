/** Kanban board page: columns, drag and drop, task drawer. */

import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { useProject, useProjectRole } from '@/entities/project/hooks';
import { projectPermissions } from '@/entities/project/model';
import type { BoardCard, TaskRead } from '@/shared/api/types';
import { useProjectLiveUpdates } from '@/features/live/hooks';
import { Badge, Button, PageHeader, Skeleton } from '@/shared/ui';
import { Board } from '@/widgets/board/Board';
import { TaskCreateModal } from '@/features/task/TaskCreateModal';
import { TaskDrawer } from '@/widgets/task/TaskDrawer';

/**
 * Render the project kanban board page.
 *
 * Cards open in a drawer above the board; drag and drop persists card order.
 *
 * @returns board page element.
 */
export function BoardPage() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const { data: project, isLoading } = useProject(id);
  const role = useProjectRole(id);
  const permissions = projectPermissions(role);
  useProjectLiveUpdates(id);

  const [createOpen, setCreateOpen] = useState(false);
  const [presetStatusId, setPresetStatusId] = useState<number | null>(null);
  const [openTaskId, setOpenTaskId] = useState<number | null>(null);

  /**
   * Open the create dialog, optionally presetting the target column.
   *
   * @param statusId board status id or null for the default column.
   */
  const handleCreate = (statusId: number | null) => {
    setPresetStatusId(statusId);
    setCreateOpen(true);
  };

  /**
   * Open the task drawer after a task was created.
   *
   * @param task created task.
   */
  const handleCreated = (task: TaskRead) => {
    setCreateOpen(false);
    setOpenTaskId(task.id);
  };

  return (
    <>
      <PageHeader
        title={isLoading ? 'Loading' : `${project?.name ?? 'Project'} board`}
        meta={
          project && (
            <>
              <Badge tone="accent">{project.key}</Badge>
              {project.is_archived && <Badge tone="warning">Archived</Badge>}
            </>
          )
        }
        description="Drag cards between columns; card order is saved on drop."
        actions={
          permissions.canEditTasks && (
            <Button variant="primary" icon={<Plus size={16} />} onClick={() => handleCreate(null)}>
              New task
            </Button>
          )
        }
      />

      {isLoading ? (
        <Skeleton height={420} radius="var(--radius-lg)" />
      ) : (
        <Board
          projectId={id}
          onOpenCard={(card: BoardCard) => setOpenTaskId(card.id)}
          onCreateCard={(statusId: number) => handleCreate(statusId)}
        />
      )}

      <TaskCreateModal
        projectId={id}
        open={createOpen}
        statusId={presetStatusId ?? undefined}
        onClose={() => setCreateOpen(false)}
        onCreated={handleCreated}
      />

      <TaskDrawer taskId={openTaskId} onClose={() => setOpenTaskId(null)} />
    </>
  );
}
