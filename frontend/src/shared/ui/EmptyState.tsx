/** Empty state placeholder with icon, title and optional action. */

import type { ReactNode } from 'react';
import styles from './surface.module.css';

/** Props of the EmptyState component. */
export interface EmptyStateProps {
  /** Outline icon rendered inside a glass circle. */
  icon: ReactNode;
  /** Short headline. */
  title: string;
  /** Supporting text explaining the empty state. */
  text?: string;
  /** Optional call to action button. */
  action?: ReactNode;
}

/**
 * Render a centered empty state block.
 *
 * @param props icon, title, text and action slot.
 * @returns rendered empty state element.
 */
export function EmptyState({ icon, title, text, action }: EmptyStateProps) {
  return (
    <div className={styles.emptyState}>
      <div className={styles.emptyIcon}>{icon}</div>
      <p className={styles.emptyTitle}>{title}</p>
      {text && <p className={styles.emptyText}>{text}</p>}
      {action}
    </div>
  );
}
