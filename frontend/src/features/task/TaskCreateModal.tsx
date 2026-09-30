/** Modal dialog for creating a task inside a project. */

import { useEffect, useState, type FormEvent } from 'react';
import { useCreateTask } from '@/entities/task/hooks';
import { useMembers } from '@/entities/member/hooks';
import { useStatuses } from '@/entities/status/hooks';
import { PRIORITY_META, PRIORITY_ORDER } from '@/entities/task/model';
import type { Priority, TaskRead } from '@/shared/api/types';
import { errorMessage } from '@/shared/api/errors';
import { Button, Input, Modal, Select, Textarea, useToast } from '@/shared/ui';

/** Props of the TaskCreateModal. */
export interface TaskCreateModalProps {
  /** Project to create the task in. */
  projectId: number;
  /** Controls visibility. */
  open: boolean;
  /** Preset board column. */
  statusId?: number;
  /** Called on close requests. */
  onClose: () => void;
  /** Called after the task was created. */
  onCreated: (task: TaskRead) => void;
}

/**
 * Render the task creation dialog.
 *
 * @param props project, visibility, preset status and handlers.
 * @returns modal with the task form.
 */
export function TaskCreateModal({
  projectId,
  open,
  statusId,
  onClose,
  onCreated,
}: TaskCreateModalProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<Priority>('MEDIUM');
  const [assigneeId, setAssigneeId] = useState('');
  const [status, setStatus] = useState<string>('');
  const [dueDate, setDueDate] = useState('');
  const [estimatedHours, setEstimatedHours] = useState('');
  const create = useCreateTask();
  const { data: statuses } = useStatuses(projectId);
  const { data: members } = useMembers(projectId);
  const toast = useToast();

  useEffect(() => {
    if (!open) return;
    setTitle('');
    setDescription('');
    setPriority('MEDIUM');
    setAssigneeId('');
    setDueDate('');
    setEstimatedHours('');
    setStatus(statusId ? String(statusId) : '');
    create.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, statusId]);

  /**
   * Submit the task payload.
   *
   * @param event form submit event.
   */
  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    create.mutate(
      {
        projectId,
        body: {
          title: title.trim(),
          description: description.trim() || null,
          priority,
          assignee_id: assigneeId ? Number(assigneeId) : null,
          status_id: status ? Number(status) : null,
          due_date: dueDate || null,
          estimated_hours: estimatedHours ? Number(estimatedHours) : null,
          parent_task_id: null,
        },
      },
      {
        onSuccess: (task) => {
          toast.push({ title: 'Task created', text: task.key, tone: 'success' });
          onCreated(task);
        },
        onError: (error) =>
          toast.push({ title: 'Could not create task', text: errorMessage(error), tone: 'error' }),
      },
    );
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New task"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            type="submit"
            form="task-create-form"
            loading={create.isPending}
          >
            Create
          </Button>
        </>
      }
    >
      <form
        id="task-create-form"
        onSubmit={handleSubmit}
        style={{ display: 'grid', gap: 'var(--space-4)' }}
      >
        {create.isError && (
          <p style={{ color: 'var(--color-danger)', fontSize: 'var(--font-size-13)' }}>
            {errorMessage(create.error)}
          </p>
        )}
        <Input
          label="Title"
          required
          maxLength={200}
          placeholder="Short summary of the work"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
        <Textarea
          label="Description"
          maxLength={10000}
          rows={3}
          placeholder="Details, context and acceptance criteria"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
          <Select label="Status" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Default column</option>
            {(statuses ?? []).map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </Select>
          <Select
            label="Priority"
            value={priority}
            onChange={(event) => setPriority(event.target.value as Priority)}
          >
            {PRIORITY_ORDER.map((value) => (
              <option key={value} value={value}>
                {PRIORITY_META[value].label}
              </option>
            ))}
          </Select>
          <Select
            label="Assignee"
            value={assigneeId}
            onChange={(event) => setAssigneeId(event.target.value)}
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
            value={dueDate}
            onChange={(event) => setDueDate(event.target.value)}
          />
          <Input
            label="Estimation (hours)"
            type="number"
            min={0}
            step={0.5}
            value={estimatedHours}
            onChange={(event) => setEstimatedHours(event.target.value)}
          />
        </div>
      </form>
    </Modal>
  );
}
