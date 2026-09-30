/**
 * Task panel: details of one task with inline editing.
 *
 * The panel is shared between the board drawer and the standalone task
 * route. All writes go through PATCH with If-Match; a stale version opens
 * a conflict dialog (docs/api-endpoints.md, section 32).
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Eye, Pencil, Tag, Trash2, Users } from 'lucide-react';
import {
  useAssignTask,
  useDeleteTask,
  useTransitionTask,
  useUnassignTask,
  useUpdateTask,
} from '@/entities/task/hooks';
import { PRIORITY_META, PRIORITY_ORDER } from '@/entities/task/model';
import { useMembers } from '@/entities/member/hooks';
import { useLabels, useStatuses } from '@/entities/status/hooks';
import { useAttachLabel, useDetachLabel } from '@/entities/label/hooks';
import { useRemoveWatcher, useToggleWatch, useWatchers } from '@/entities/watcher/hooks';
import { useProjectRole } from '@/entities/project/hooks';
import { projectPermissions } from '@/entities/project/model';
import { useSession } from '@/entities/session/hooks';
import { useTask } from '@/entities/task/hooks';
import type { Priority, TaskPatch, TaskRead } from '@/shared/api/types';
import { asApiError, errorMessage } from '@/shared/api/errors';
import { formatDateTime, formatHours } from '@/shared/lib/format';
import {
  Badge,
  Button,
  ConfirmDialog,
  Input,
  Select,
  Skeleton,
  Textarea,
  useToast,
} from '@/shared/ui';
import { CommentSection } from '@/features/comments/CommentSection';
import { TaskActivity } from './TaskActivity';
import { TaskLabels } from './TaskLabels';
import { TaskWatchers } from './TaskWatchers';
import styles from './TaskPanel.module.css';

/** Props of the TaskPanel component. */
export interface TaskPanelProps {
  /** Task to render. */
  taskId: number;
  /** Called when the panel requests closing (drawer mode). */
  onClose?: () => void;
  /** Renders inside the board drawer; hides the back link. */
  embedded?: boolean;
}

/**
 * Render the full task panel with fields, labels, watchers and feeds.
 *
 * @param props task id and view mode.
 * @returns rendered task panel.
 */
export function TaskPanel({ taskId, onClose, embedded = false }: TaskPanelProps) {
  const { data: task, isLoading, refetch } = useTask(taskId);
  return (
    <TaskPanelInner
      taskId={taskId}
      task={task}
      isLoading={isLoading}
      refetch={refetch}
      onClose={onClose}
      embedded={embedded}
    />
  );
}

interface TaskPanelInnerProps {
  taskId: number;
  task: TaskRead | undefined;
  isLoading: boolean;
  refetch: () => Promise<{ data?: TaskRead }>;
  onClose?: () => void;
  embedded: boolean;
}

/**
 * Render the loaded task panel and keep local edit state.
 *
 * @param props task data, permissions and view mode.
 * @returns rendered task content.
 */
function TaskPanelInner({
  taskId,
  task,
  isLoading,
  refetch,
  onClose,
  embedded,
}: TaskPanelInnerProps) {
  const { user } = useSession();
  const projectId = task?.project_id;
  const role = useProjectRole(projectId);
  const permissions = projectPermissions(role);
  const { data: members } = useMembers(projectId);
  const { data: labels } = useLabels(projectId);
  const { data: watchers } = useWatchers(taskId);
  const update = useUpdateTask();
  const remove = useDeleteTask();
  const transition = useTransitionTask();
  const assign = useAssignTask();
  const unassign = useUnassignTask();
  const attachLabel = useAttachLabel();
  const detachLabel = useDetachLabel();
  const toggleWatch = useToggleWatch();
  const removeWatcher = useRemoveWatcher();
  const toast = useToast();

  const [titleEditing, setTitleEditing] = useState(false);
  const [titleDraft, setTitleDraft] = useState('');
  const [descriptionDraft, setDescriptionDraft] = useState<string | null>(null);
  const [conflict, setConflict] = useState<TaskPatch | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);

  useEffect(() => {
    if (task) {
      setTitleDraft(task.title);
      setDescriptionDraft(task.description ?? '');
    }
  }, [task]);

  if (isLoading || !task) {
    return (
      <div style={{ display: 'grid', gap: 'var(--space-4)' }}>
        <Skeleton height={28} width="40%" />
        <Skeleton height={72} />
        <Skeleton height={120} />
      </div>
    );
  }

  /**
   * Apply a task patch with conflict detection.
   *
   * @param body fields to change.
   */
  const patch = (body: TaskPatch) => {
    update.mutate(
      { taskId: task.id, body, version: task.version },
      {
        onError: (error) => {
          const apiError = asApiError(error);
          if (apiError.code === 'stale_version' || apiError.status === 428) {
            setConflict(body);
          } else {
            toast.push({ title: 'Update failed', text: apiError.message, tone: 'error' });
          }
        },
      },
    );
  };

  /**
   * Overwrite the conflicting change with the latest server version.
   */
  const handleOverwrite = () => {
    if (!conflict) return;
    const body = conflict;
    void refetch().then((result) => {
      const fresh = result.data;
      if (!fresh) return;
      update.mutate(
        { taskId: task.id, body, version: fresh.version },
        {
          onSuccess: () => setConflict(null),
          onError: (error) =>
            toast.push({ title: 'Update failed', text: errorMessage(error), tone: 'error' }),
        },
      );
    });
  };

  /**
   * Drop the local edits and load the latest server version.
   */
  const handleReload = () => {
    void refetch().then(() => setConflict(null));
  };

  /**
   * Delete the task after confirmation.
   */
  const handleDelete = () => {
    remove.mutate(
      { taskId: task.id, version: task.version },
      {
        onSuccess: () => {
          toast.push({ title: 'Task deleted', text: task.key, tone: 'success' });
          setDeleteOpen(false);
          onClose?.();
        },
        onError: (error) => {
          const apiError = asApiError(error);
          if (apiError.code === 'stale_version' || apiError.status === 428) {
            setDeleteOpen(false);
            setConflict({ title: task.title });
          } else {
            toast.push({ title: 'Delete failed', text: apiError.message, tone: 'error' });
          }
        },
      },
    );
  };

  return (
    <div>
      <header className={styles.header}>
        <div>
          <div className={styles.titleRow}>
            <span className={styles.key}>{task.key}</span>
            {titleEditing ? (
              <input
                className={styles.titleInput}
                value={titleDraft}
                autoFocus
                maxLength={200}
                onChange={(event) => setTitleDraft(event.target.value)}
                onBlur={() => {
                  setTitleEditing(false);
                  const value = titleDraft.trim();
                  if (value && value !== task.title) patch({ title: value });
                }}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') event.currentTarget.blur();
                  if (event.key === 'Escape') {
                    setTitleDraft(task.title);
                    setTitleEditing(false);
                  }
                }}
              />
            ) : (
              <h2
                className={styles.title}
                onClick={() => permissions.canEditTasks && setTitleEditing(true)}
                title={permissions.canEditTasks ? 'Click to edit' : undefined}
              >
                {task.title}
              </h2>
            )}
            {permissions.canEditTasks && !titleEditing && (
              <Button
                size="sm"
                variant="ghost"
                iconOnly
                icon={<Pencil size={14} />}
                aria-label="Edit title"
                onClick={() => setTitleEditing(true)}
              />
            )}
          </div>
          <div className={styles.metaRow}>
            <span>Created {formatDateTime(task.created_at)}</span>
            <span>Updated {formatDateTime(task.updated_at)}</span>
            <span>by {task.creator.username}</span>
            {task.version > 0 && <span>revision {task.version}</span>}
          </div>
        </div>
        {permissions.canDeleteOwnTasks && (
          <Button
            variant="ghost"
            iconOnly
            icon={<Trash2 size={16} />}
            aria-label="Delete task"
            onClick={() => setDeleteOpen(true)}
          />
        )}
      </header>

      <div className={styles.grid}>
        <div className={styles.column}>
          <div className={styles.descriptionBox}>
            <TaskStatusField
              task={task}
              disabled={!permissions.canEditTasks}
              onSelect={(statusId) =>
                transition.mutate(
                  { taskId: task.id, statusId },
                  {
                    onError: (error) =>
                      toast.push({
                        title: 'Move failed',
                        text:
                          asApiError(error).code === 'invalid_transition'
                            ? 'Only adjacent columns are allowed.'
                            : errorMessage(error),
                        tone: 'error',
                      }),
                  },
                )
              }
            />
            <TaskDescriptionField
              value={descriptionDraft ?? task.description ?? ''}
              editing={descriptionDraft !== null}
              disabled={!permissions.canEditTasks}
              onChange={setDescriptionDraft}
              onSave={(value) => {
                setDescriptionDraft(null);
                if (value !== (task.description ?? '')) patch({ description: value || null });
              }}
              onCancel={() => setDescriptionDraft(null)}
            />
          </div>

          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <Tag size={16} /> Labels
              </span>
            </h3>
            <TaskLabels
              labels={task.labels ?? []}
              available={labels ?? []}
              canEdit={permissions.canEditTasks}
              onAttach={(labelId) =>
                attachLabel.mutate(
                  { taskId: task.id, labelId },
                  {
                    onError: (error) =>
                      toast.push({
                        title: 'Label not added',
                        text: errorMessage(error),
                        tone: 'error',
                      }),
                  },
                )
              }
              onDetach={(labelId) =>
                detachLabel.mutate(
                  { taskId: task.id, labelId },
                  {
                    onError: (error) =>
                      toast.push({
                        title: 'Label not removed',
                        text: errorMessage(error),
                        tone: 'error',
                      }),
                  },
                )
              }
            />
          </section>

          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <Users size={16} /> Watchers
              </span>
            </h3>
            <TaskWatchers
              watchers={watchers ?? []}
              me={user}
              canEdit={permissions.canEditTasks}
              canManage={permissions.canManage}
              pending={toggleWatch.isPending || removeWatcher.isPending}
              onToggle={() =>
                toggleWatch.mutate(
                  {
                    taskId: task.id,
                    watch: !(user && (watchers ?? []).some((w) => w.user.id === user.id)),
                  },
                  {
                    onError: (error) =>
                      toast.push({
                        title: 'Watch failed',
                        text: errorMessage(error),
                        tone: 'error',
                      }),
                  },
                )
              }
              onRemove={(userId) =>
                removeWatcher.mutate(
                  { taskId: task.id, userId },
                  {
                    onError: (error) =>
                      toast.push({
                        title: 'Remove failed',
                        text: errorMessage(error),
                        tone: 'error',
                      }),
                  },
                )
              }
            />
          </section>

          <CommentSection
            taskId={task.id}
            projectId={task.project_id}
            canComment={permissions.canEditTasks}
            canManage={permissions.canManage}
          />
          <TaskActivity taskId={task.id} />
        </div>

        <div className={styles.column}>
          <Select
            label="Priority"
            value={task.priority}
            disabled={!permissions.canEditTasks}
            onChange={(event) => patch({ priority: event.target.value as Priority })}
          >
            {PRIORITY_ORDER.map((value) => (
              <option key={value} value={value}>
                {PRIORITY_META[value].label}
              </option>
            ))}
          </Select>

          <Select
            label="Assignee"
            value={task.assignee?.id ?? ''}
            disabled={!permissions.canEditTasks}
            onChange={(event) => {
              const value = event.target.value;
              if (value === '') {
                unassign.mutate({ taskId: task.id });
              } else {
                assign.mutate(
                  { taskId: task.id, userId: Number(value) },
                  {
                    onError: (error) =>
                      toast.push({
                        title: 'Assign failed',
                        text: errorMessage(error),
                        tone: 'error',
                      }),
                  },
                );
              }
            }}
          >
            <option value="">Unassigned</option>
            {(members?.items ?? []).map((member) => (
              <option key={member.user.id} value={member.user.id}>
                {member.user.username}
              </option>
            ))}
          </Select>

          <Input
            label="Due date"
            type="date"
            disabled={!permissions.canEditTasks}
            value={task.due_date ?? ''}
            onChange={(event) => {
              const value = event.target.value;
              if (value !== (task.due_date ?? '')) {
                patch({ due_date: value || null });
              }
            }}
          />

          <Input
            label="Estimation (hours)"
            type="number"
            min={0}
            step={0.5}
            disabled={!permissions.canEditTasks}
            defaultValue={task.estimated_hours ? Number(task.estimated_hours) : ''}
            onBlur={(event) => {
              const raw = event.target.value;
              const next = raw === '' ? null : Number(raw);
              const current = task.estimated_hours ? Number(task.estimated_hours) : null;
              if (next !== current) patch({ estimated_hours: next });
            }}
          />

          <div className={styles.metaRow}>
            <Badge tone="neutral">{formatHours(task.estimated_hours) || 'no estimate'}</Badge>
            <Badge tone="info">{task.comments_count} comments</Badge>
            <Badge tone="muted">{task.watchers_count} watchers</Badge>
            {embedded && !task.parent_task_id && (
              <Badge tone="muted">
                <Eye size={12} /> live
              </Badge>
            )}
          </div>

          {!embedded && (
            <Link
              to={`/projects/${task.project_id}/board`}
              style={{ fontSize: 'var(--font-size-13)' }}
            >
              Back to board
            </Link>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={deleteOpen}
        title="Delete task?"
        text={`Task ${task.key} will be hidden from lists. Activity history is kept.`}
        confirmLabel="Delete"
        danger
        loading={remove.isPending}
        onConfirm={handleDelete}
        onCancel={() => setDeleteOpen(false)}
      />

      <ConfirmDialog
        open={conflict !== null}
        title="Task was changed"
        text="Someone updated this task while you were editing. Reload to see the latest version or overwrite it with your change."
        confirmLabel="Overwrite"
        secondaryLabel="Reload"
        loading={update.isPending}
        onConfirm={handleOverwrite}
        onSecondary={handleReload}
        onCancel={() => setConflict(null)}
      />
    </div>
  );
}

/** Props of the internal status selector. */
interface TaskStatusFieldProps {
  task: TaskRead;
  disabled: boolean;
  onSelect: (statusId: number) => void;
}

/**
 * Render the status selector limited to adjacent columns.
 *
 * The workflow allows one-step moves only, so the select lists the current
 * column and its immediate neighbours.
 *
 * @param props task data, permissions and change handler.
 * @returns rendered status selector.
 */
function TaskStatusField({ task, disabled, onSelect }: TaskStatusFieldProps) {
  const { data: statuses } = useStatuses(task.project_id);
  const ordered = (statuses ?? []).slice().sort((a, b) => a.position - b.position);
  const currentIndex = ordered.findIndex((status) => status.id === task.status.id);
  const allowed = ordered.filter(
    (_status, index) => currentIndex < 0 || Math.abs(index - currentIndex) <= 1,
  );

  return (
    <Select
      label="Status"
      value={String(task.status.id)}
      disabled={disabled}
      onChange={(event) => onSelect(Number(event.target.value))}
      hint="Only adjacent columns are available"
    >
      {allowed.map((status) => (
        <option key={status.id} value={status.id}>
          {status.name}
        </option>
      ))}
    </Select>
  );
}

/** Props of the description editor. */
interface TaskDescriptionFieldProps {
  value: string;
  editing: boolean;
  disabled: boolean;
  onChange: (value: string | null) => void;
  onSave: (value: string) => void;
  onCancel: () => void;
}

/**
 * Render the task description with click-to-edit behavior.
 *
 * @param props draft value, edit state and handlers.
 * @returns rendered description block.
 */
function TaskDescriptionField({
  value,
  editing,
  disabled,
  onChange,
  onSave,
  onCancel,
}: TaskDescriptionFieldProps) {
  const [draft, setDraft] = useState(value);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  if (!editing) {
    return (
      <div style={{ display: 'grid', gap: 'var(--space-2)' }}>
        <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-13)' }}>
          Description
        </span>
        <div
          className={styles.descriptionText}
          onClick={() => !disabled && onChange(draft)}
          title={disabled ? undefined : 'Click to edit'}
        >
          {value || <span className={styles.descriptionEmpty}>No description</span>}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gap: 'var(--space-2)' }}>
      <Textarea
        label="Description"
        rows={6}
        maxLength={10000}
        autoFocus
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
      />
      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
        <Button size="sm" variant="primary" onClick={() => onSave(draft)}>
          Save
        </Button>
        <Button size="sm" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
