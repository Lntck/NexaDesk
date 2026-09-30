/** Page header with title, description and action slot. */

import type { ReactNode } from 'react';
import styles from './PageHeader.module.css';

/** Props of the PageHeader component. */
export interface PageHeaderProps {
  /** Page title. */
  title: string;
  /** Supporting description. */
  description?: string;
  /** Right-aligned actions. */
  actions?: ReactNode;
  /** Meta line rendered under the title (badges). */
  meta?: ReactNode;
}

/**
 * Render the standard page heading row.
 *
 * @param props title, description, meta and actions.
 * @returns rendered header element.
 */
export function PageHeader({ title, description, actions, meta }: PageHeaderProps) {
  return (
    <header className={styles.header}>
      <div>
        <h1 className={styles.title}>{title}</h1>
        {meta && <div className={styles.meta}>{meta}</div>}
        {description && <p className={styles.description}>{description}</p>}
      </div>
      {actions && <div className={styles.actions}>{actions}</div>}
    </header>
  );
}
