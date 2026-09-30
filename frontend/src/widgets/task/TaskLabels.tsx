/** Task labels block: attached chips and a picker for project labels. */

import { Plus, X } from 'lucide-react';
import type { LabelRead } from '@/shared/api/types';
import { hexToRgba } from '@/shared/lib/colors';
import { Button, Dropdown, DropdownItem, Tooltip } from '@/shared/ui';
import styles from './TaskPanel.module.css';

/** Props of the TaskLabels component. */
export interface TaskLabelsProps {
  /** Labels attached to the task. */
  labels: LabelRead[];
  /** All labels of the project. */
  available: LabelRead[];
  /** Whether the user can edit task labels. */
  canEdit: boolean;
  /** Called to attach a label. */
  onAttach: (labelId: number) => void;
  /** Called to detach a label. */
  onDetach: (labelId: number) => void;
}

/**
 * Render task labels with attach and detach actions.
 *
 * @param props label sets, permissions and handlers.
 * @returns rendered label block.
 */
export function TaskLabels({ labels, available, canEdit, onAttach, onDetach }: TaskLabelsProps) {
  const attachedIds = new Set(labels.map((label) => label.id));
  const rest = available.filter((label) => !attachedIds.has(label.id));

  return (
    <div>
      <div className={styles.labelRow}>
        {labels.map((label) => (
          <span
            key={label.id}
            className={styles.labelChip}
            style={{
              backgroundColor: hexToRgba(label.color, 0.18),
              borderColor: hexToRgba(label.color, 0.45),
            }}
          >
            {label.name}
            {canEdit && (
              <button
                type="button"
                className={styles.labelRemove}
                onClick={() => onDetach(label.id)}
                aria-label={`Remove label ${label.name}`}
              >
                <X size={12} />
              </button>
            )}
          </span>
        ))}
        {labels.length === 0 && (
          <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-13)' }}>
            No labels
          </span>
        )}
        {canEdit && (
          <Dropdown
            trigger={({ toggle }) => (
              <Button size="sm" variant="ghost" icon={<Plus size={14} />} onClick={toggle}>
                Label
              </Button>
            )}
          >
            {({ close }) =>
              rest.length === 0 ? (
                <Tooltip label="All project labels are already attached">
                  <span style={{ padding: 'var(--space-2)', color: 'var(--color-text-muted)' }}>
                    No labels available
                  </span>
                </Tooltip>
              ) : (
                rest.map((label) => (
                  <DropdownItem
                    key={label.id}
                    onClick={() => {
                      close();
                      onAttach(label.id);
                    }}
                  >
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: 999,
                        backgroundColor: label.color,
                      }}
                    />
                    {label.name}
                  </DropdownItem>
                ))
              )
            }
          </Dropdown>
        )}
      </div>
    </div>
  );
}
