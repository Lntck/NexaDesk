/** Confirmation dialog for destructive or irreversible actions. */

import { AlertTriangle } from 'lucide-react';
import { Button } from './Button';
import { Modal } from './Modal';

/** Props of the ConfirmDialog component. */
export interface ConfirmDialogProps {
  /** Controls visibility. */
  open: boolean;
  /** Dialog headline. */
  title: string;
  /** Explanatory text. */
  text?: string;
  /** Label of the confirming button. */
  confirmLabel?: string;
  /** Destructive styling of the confirm button. */
  danger?: boolean;
  /** Shows a spinner and blocks the confirm button. */
  loading?: boolean;
  /** Optional middle action, for example reloading stale data. */
  secondaryLabel?: string;
  /** Called on confirm. */
  onConfirm: () => void;
  /** Called on the optional middle action. */
  onSecondary?: () => void;
  /** Called on cancel or close. */
  onCancel: () => void;
}

/**
 * Render a small confirm dialog with cancel and confirm actions.
 *
 * @param props visibility, text, labels and handlers.
 * @returns rendered modal with two or three actions.
 */
export function ConfirmDialog({
  open,
  title,
  text,
  confirmLabel = 'Confirm',
  danger = false,
  loading = false,
  secondaryLabel,
  onConfirm,
  onSecondary,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Modal
      open={open}
      onClose={onCancel}
      title={title}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onCancel} disabled={loading}>
            Cancel
          </Button>
          {secondaryLabel && onSecondary && (
            <Button variant="ghost" onClick={onSecondary} disabled={loading}>
              {secondaryLabel}
            </Button>
          )}
          <Button variant={danger ? 'danger' : 'primary'} onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      {text && (
        <p style={{ display: 'flex', gap: 'var(--space-3)', color: 'var(--color-text-secondary)' }}>
          {danger && (
            <AlertTriangle size={18} style={{ color: 'var(--color-danger)', flexShrink: 0 }} />
          )}
          {text}
        </p>
      )}
    </Modal>
  );
}
