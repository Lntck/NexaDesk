/** Modal dialog for transferring project ownership to a member. */

import { useState, type FormEvent } from 'react';
import { useTransferOwnership } from '@/entities/project/hooks';
import { useMembers } from '@/entities/member/hooks';
import { errorMessage } from '@/shared/api/errors';
import { Button, Modal, Select, useToast } from '@/shared/ui';

/** Minimal project info needed by the transfer dialog. */
export interface TransferTarget {
  /** Project id. */
  id: number;
  /** Project key. */
  key: string;
  /** Project name. */
  name: string;
}

/** Props of the TransferOwnershipModal. */
export interface TransferOwnershipModalProps {
  /** Project to transfer; null hides the dialog. */
  project: TransferTarget | null;
  /** Called on close requests. */
  onClose: () => void;
}

/**
 * Render the ownership transfer dialog.
 *
 * @param props target project and close handler.
 * @returns modal with the member selector.
 */
export function TransferOwnershipModal({ project, onClose }: TransferOwnershipModalProps) {
  const [userId, setUserId] = useState('');
  const { data: members } = useMembers(project?.id);
  const transfer = useTransferOwnership();
  const toast = useToast();

  /**
   * Transfer ownership to the selected member.
   *
   * @param event form submit event.
   */
  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!project || !userId) return;
    transfer.mutate(
      { projectId: project.id, userId: Number(userId) },
      {
        onSuccess: () => {
          toast.push({ title: 'Ownership transferred', tone: 'success' });
          onClose();
        },
        onError: (error) =>
          toast.push({ title: 'Transfer failed', text: errorMessage(error), tone: 'error' }),
      },
    );
  };

  const candidates = (members?.items ?? []).filter((member) => member.role !== 'owner');

  return (
    <Modal
      open={project !== null}
      onClose={onClose}
      title="Transfer ownership"
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            type="submit"
            form="transfer-ownership-form"
            disabled={!userId}
            loading={transfer.isPending}
          >
            Transfer
          </Button>
        </>
      }
    >
      <form
        id="transfer-ownership-form"
        onSubmit={handleSubmit}
        style={{ display: 'grid', gap: 'var(--space-4)' }}
      >
        {transfer.isError && (
          <p style={{ color: 'var(--color-danger)', fontSize: 'var(--font-size-13)' }}>
            {errorMessage(transfer.error)}
          </p>
        )}
        <Select
          label="New owner"
          required
          value={userId}
          onChange={(event) => setUserId(event.target.value)}
          hint="Only existing project members can own the project."
        >
          <option value="">Select a member</option>
          {candidates.map((member) => (
            <option key={member.user.id} value={member.user.id}>
              {member.user.username}
            </option>
          ))}
        </Select>
      </form>
    </Modal>
  );
}
