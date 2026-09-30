/** Labels and board columns page: CRUD for project labels and statuses. */

import { useState, type FormEvent } from 'react';
import { useParams } from 'react-router-dom';
import { Check, Pencil, Plus, Tag, Trash2, X } from 'lucide-react';
import { useProject, useProjectRole } from '@/entities/project/hooks';
import { projectPermissions } from '@/entities/project/model';
import {
  useCreateLabel,
  useCreateStatus,
  useDeleteLabel,
  useDeleteStatus,
  useLabels,
  useStatuses,
  useUpdateLabel,
  useUpdateStatus,
} from '@/entities/status/hooks';
import type { LabelRead, TaskStatusRead } from '@/shared/api/types';
import { errorMessage } from '@/shared/api/errors';
import { Button, ConfirmDialog, Input, PageHeader, Skeleton, useToast } from '@/shared/ui';
import styles from './LabelsPage.module.css';

/** Default color offered in the create forms. */
const DEFAULT_COLOR = '#8AB4FF';

/**
 * Render the label and board column editors of a project.
 *
 * @returns labels page element.
 */
export function LabelsPage() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const projectQueryId = Number.isFinite(id) ? id : undefined;
  const { data: project } = useProject(projectQueryId);
  const role = useProjectRole(projectQueryId);
  const permissions = projectPermissions(role);
  const { data: labels, isLoading: labelsLoading } = useLabels(projectQueryId);
  const { data: statuses, isLoading: statusesLoading } = useStatuses(projectQueryId);
  const toast = useToast();

  const [labelName, setLabelName] = useState('');
  const [labelColor, setLabelColor] = useState(DEFAULT_COLOR);
  const [statusName, setStatusName] = useState('');
  const [statusKey, setStatusKey] = useState('');
  const [statusColor, setStatusColor] = useState(DEFAULT_COLOR);
  const [deleteTarget, setDeleteTarget] = useState<{
    kind: 'label' | 'status';
    id: number;
    name: string;
  } | null>(null);

  const createLabel = useCreateLabel();
  const updateLabel = useUpdateLabel();
  const deleteLabel = useDeleteLabel();
  const createStatus = useCreateStatus();
  const updateStatus = useUpdateStatus();
  const deleteStatus = useDeleteStatus();

  /**
   * Create a project label from the form state.
   *
   * @param event submit event of the label form.
   */
  const handleCreateLabel = (event: FormEvent) => {
    event.preventDefault();
    if (!projectQueryId || !labelName.trim()) return;
    createLabel.mutate(
      { projectId: projectQueryId, body: { name: labelName.trim(), color: labelColor } },
      {
        onSuccess: () => setLabelName(''),
        onError: (error) =>
          toast.push({ title: 'Label not created', text: errorMessage(error), tone: 'error' }),
      },
    );
  };

  /**
   * Create a board status from the form state.
   *
   * @param event submit event of the status form.
   */
  const handleCreateStatus = (event: FormEvent) => {
    event.preventDefault();
    if (!projectQueryId || !statusName.trim() || !statusKey.trim()) return;
    createStatus.mutate(
      {
        projectId: projectQueryId,
        body: {
          name: statusName.trim(),
          key: statusKey.trim().toUpperCase(),
          color: statusColor,
        },
      },
      {
        onSuccess: () => {
          setStatusName('');
          setStatusKey('');
        },
        onError: (error) =>
          toast.push({ title: 'Column not created', text: errorMessage(error), tone: 'error' }),
      },
    );
  };

  /**
   * Run the confirmed delete for a label or status.
   */
  const handleDelete = () => {
    if (!projectQueryId || !deleteTarget) return;
    const onError = (error: unknown) =>
      toast.push({ title: 'Delete failed', text: errorMessage(error), tone: 'error' });
    if (deleteTarget.kind === 'label') {
      deleteLabel.mutate(
        { projectId: projectQueryId, labelId: deleteTarget.id },
        {
          onSuccess: () => setDeleteTarget(null),
          onError,
        },
      );
    } else {
      deleteStatus.mutate(
        { projectId: projectQueryId, statusId: deleteTarget.id },
        {
          onSuccess: () => setDeleteTarget(null),
          onError,
        },
      );
    }
  };

  return (
    <>
      <PageHeader
        title={project ? `${project.name} labels` : 'Labels'}
        description="Labels tag tasks; columns define the board workflow."
      />

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>
          <Tag size={17} /> Labels
        </h2>
        <p className={styles.sectionHint}>Labels are shared by all tasks of the project.</p>

        {permissions.canManage && (
          <form className={styles.form} onSubmit={handleCreateLabel}>
            <Input
              label="Name"
              placeholder="Bug"
              maxLength={50}
              value={labelName}
              onChange={(event) => setLabelName(event.target.value)}
            />
            <label
              style={{ display: 'grid', gap: 'var(--space-1)', fontSize: 'var(--font-size-13)' }}
            >
              Color
              <input
                type="color"
                className={styles.colorInput}
                value={labelColor}
                onChange={(event) => setLabelColor(event.target.value)}
              />
            </label>
            <Button
              type="submit"
              variant="primary"
              icon={<Plus size={16} />}
              loading={createLabel.isPending}
            >
              Add label
            </Button>
          </form>
        )}

        {labelsLoading ? (
          <Skeleton height={44} radius="var(--radius-sm)" />
        ) : (labels ?? []).length === 0 ? (
          <div className={styles.list}>
            <div className={styles.empty}>No labels yet.</div>
          </div>
        ) : (
          <div className={styles.list}>
            {(labels ?? []).map((label) => (
              <LabelRow
                key={label.id}
                label={label}
                canEdit={permissions.canManage}
                onSave={(name, color) =>
                  updateLabel.mutate(
                    {
                      projectId: projectQueryId as number,
                      labelId: label.id,
                      body: { name, color },
                    },
                    {
                      onError: (error) =>
                        toast.push({
                          title: 'Label not saved',
                          text: errorMessage(error),
                          tone: 'error',
                        }),
                    },
                  )
                }
                onDelete={() => setDeleteTarget({ kind: 'label', id: label.id, name: label.name })}
              />
            ))}
          </div>
        )}
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Board columns</h2>
        <p className={styles.sectionHint}>
          Tasks can only move to adjacent columns, one step at a time.
        </p>

        {permissions.canManage && (
          <form className={styles.form} onSubmit={handleCreateStatus}>
            <Input
              label="Name"
              placeholder="In progress"
              maxLength={50}
              value={statusName}
              onChange={(event) => setStatusName(event.target.value)}
            />
            <Input
              label="Key"
              placeholder="IN_PROGRESS"
              maxLength={50}
              value={statusKey}
              onChange={(event) => setStatusKey(event.target.value)}
            />
            <label
              style={{ display: 'grid', gap: 'var(--space-1)', fontSize: 'var(--font-size-13)' }}
            >
              Color
              <input
                type="color"
                className={styles.colorInput}
                value={statusColor}
                onChange={(event) => setStatusColor(event.target.value)}
              />
            </label>
            <Button
              type="submit"
              variant="primary"
              icon={<Plus size={16} />}
              loading={createStatus.isPending}
            >
              Add column
            </Button>
          </form>
        )}

        {statusesLoading ? (
          <Skeleton height={44} radius="var(--radius-sm)" />
        ) : (statuses ?? []).length === 0 ? (
          <div className={styles.list}>
            <div className={styles.empty}>No columns yet.</div>
          </div>
        ) : (
          <div className={styles.list}>
            {(statuses ?? [])
              .slice()
              .sort((a, b) => a.position - b.position)
              .map((status) => (
                <StatusRow
                  key={status.id}
                  status={status}
                  canEdit={permissions.canManage}
                  onSave={(name, color) =>
                    updateStatus.mutate(
                      {
                        projectId: projectQueryId as number,
                        statusId: status.id,
                        body: { name, color },
                      },
                      {
                        onError: (error) =>
                          toast.push({
                            title: 'Column not saved',
                            text: errorMessage(error),
                            tone: 'error',
                          }),
                      },
                    )
                  }
                  onDelete={() =>
                    setDeleteTarget({ kind: 'status', id: status.id, name: status.name })
                  }
                />
              ))}
          </div>
        )}
      </section>

      <ConfirmDialog
        open={deleteTarget !== null}
        title={deleteTarget?.kind === 'label' ? 'Delete label?' : 'Delete column?'}
        text={
          deleteTarget
            ? `${deleteTarget.name} will be removed. Columns with tasks cannot be deleted.`
            : ''
        }
        confirmLabel="Delete"
        danger
        loading={deleteLabel.isPending || deleteStatus.isPending}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </>
  );
}

/** Props of the internal label row. */
interface LabelRowProps {
  label: LabelRead;
  canEdit: boolean;
  onSave: (name: string, color: string) => void;
  onDelete: () => void;
}

/**
 * Render one label row with inline editing.
 *
 * @param props label data, permissions and handlers.
 * @returns rendered label row.
 */
function LabelRow({ label, canEdit, onSave, onDelete }: LabelRowProps) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(label.name);
  const [color, setColor] = useState(label.color);

  /**
   * Save the edited label and leave edit mode.
   */
  const handleSave = () => {
    if (!name.trim()) return;
    onSave(name.trim(), color);
    setEditing(false);
  };

  return (
    <div className={styles.row}>
      {editing ? (
        <div className={styles.rowForm}>
          <input
            type="color"
            className={styles.colorInput}
            value={color}
            onChange={(event) => setColor(event.target.value)}
          />
          <Input value={name} maxLength={50} onChange={(event) => setName(event.target.value)} />
          <Button size="sm" variant="primary" icon={<Check size={15} />} onClick={handleSave} />
          <Button
            size="sm"
            variant="ghost"
            icon={<X size={15} />}
            onClick={() => setEditing(false)}
          />
        </div>
      ) : (
        <>
          <span className={styles.dot} style={{ backgroundColor: label.color }} />
          <span className={styles.name}>{label.name}</span>
          {canEdit && (
            <>
              <Button
                size="sm"
                variant="ghost"
                icon={<Pencil size={15} />}
                onClick={() => setEditing(true)}
              />
              <Button size="sm" variant="ghost" icon={<Trash2 size={15} />} onClick={onDelete} />
            </>
          )}
        </>
      )}
    </div>
  );
}

/** Props of the internal status row. */
interface StatusRowProps {
  status: TaskStatusRead;
  canEdit: boolean;
  onSave: (name: string, color: string) => void;
  onDelete: () => void;
}

/**
 * Render one board status row with inline editing.
 *
 * @param props status data, permissions and handlers.
 * @returns rendered status row.
 */
function StatusRow({ status, canEdit, onSave, onDelete }: StatusRowProps) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(status.name);
  const [color, setColor] = useState(status.color);

  /**
   * Save the edited column and leave edit mode.
   */
  const handleSave = () => {
    if (!name.trim()) return;
    onSave(name.trim(), color);
    setEditing(false);
  };

  return (
    <div className={styles.row}>
      {editing ? (
        <div className={styles.rowForm}>
          <input
            type="color"
            className={styles.colorInput}
            value={color}
            onChange={(event) => setColor(event.target.value)}
          />
          <Input value={name} maxLength={50} onChange={(event) => setName(event.target.value)} />
          <Button size="sm" variant="primary" icon={<Check size={15} />} onClick={handleSave} />
          <Button
            size="sm"
            variant="ghost"
            icon={<X size={15} />}
            onClick={() => setEditing(false)}
          />
        </div>
      ) : (
        <>
          <span className={styles.dot} style={{ backgroundColor: status.color }} />
          <span className={styles.name}>{status.name}</span>
          <span className={styles.key}>{status.key}</span>
          {canEdit && (
            <>
              <Button
                size="sm"
                variant="ghost"
                icon={<Pencil size={15} />}
                onClick={() => setEditing(true)}
              />
              <Button size="sm" variant="ghost" icon={<Trash2 size={15} />} onClick={onDelete} />
            </>
          )}
        </>
      )}
    </div>
  );
}
