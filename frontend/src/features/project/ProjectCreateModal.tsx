/** Modal dialog for creating a project. */

import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCreateProject } from '@/entities/project/hooks';
import { errorMessage } from '@/shared/api/errors';
import { Button, Input, Modal, Textarea, useToast } from '@/shared/ui';

/** Props of the ProjectCreateModal. */
export interface ProjectCreateModalProps {
  /** Controls visibility. */
  open: boolean;
  /** Called on close requests. */
  onClose: () => void;
}

const KEY_PATTERN = '^[A-Z][A-Z0-9]{1,9}$';

/**
 * Render the project creation dialog.
 *
 * @param props visibility and close handler.
 * @returns modal with the project form.
 */
export function ProjectCreateModal({ open, onClose }: ProjectCreateModalProps) {
  const [key, setKey] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const create = useCreateProject();
  const { reset: resetCreate } = create;
  const toast = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return;
    setKey('');
    setName('');
    setDescription('');
    resetCreate();
  }, [open, resetCreate]);

  /**
   * Submit the form and open the new project board.
   *
   * @param event form submit event.
   */
  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    create.mutate(
      {
        key: key.trim().toUpperCase(),
        name: name.trim(),
        description: description.trim() || null,
      },
      {
        onSuccess: (project) => {
          toast.push({ title: 'Project created', text: project.name, tone: 'success' });
          onClose();
          navigate(`/projects/${project.id}/board`);
        },
      },
    );
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New project"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            form="project-create-form"
            type="submit"
            loading={create.isPending}
          >
            Create
          </Button>
        </>
      }
    >
      <form
        id="project-create-form"
        onSubmit={handleSubmit}
        style={{ display: 'grid', gap: 'var(--space-4)' }}
      >
        {create.isError && (
          <p style={{ color: 'var(--color-danger)', fontSize: 'var(--font-size-13)' }}>
            {errorMessage(create.error)}
          </p>
        )}
        <Input
          label="Key"
          required
          minLength={2}
          maxLength={10}
          pattern={KEY_PATTERN}
          title="Uppercase letters and digits, starting with a letter (2-10 characters)"
          placeholder="NEXA"
          hint="Uppercase letters and digits, e.g. NEXA. Used in task keys like NEXA-17."
          value={key}
          onChange={(event) => setKey(event.target.value.toUpperCase())}
        />
        <Input
          label="Name"
          required
          maxLength={100}
          placeholder="NexaDesk"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <Textarea
          label="Description"
          maxLength={2000}
          rows={3}
          placeholder="What is this project about?"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />
      </form>
    </Modal>
  );
}
