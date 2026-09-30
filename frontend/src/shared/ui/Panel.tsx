/** Large floating glass panel with optional header. */

import type { ReactNode } from 'react';
import { cn } from '@/shared/lib/cn';
import styles from './surface.module.css';

/** Props of the Panel component. */
export interface PanelProps {
  /** Optional panel title rendered in the header row. */
  title?: ReactNode;
  /** Actions rendered on the right side of the header. */
  actions?: ReactNode;
  /** Remove body padding, e.g. for full-bleed lists. */
  flush?: boolean;
  className?: string;
  children: ReactNode;
}

/**
 * Render a large glass surface with stronger blur and depth.
 *
 * @param props title, actions, flush flag and content.
 * @returns rendered panel element.
 */
export function Panel({ title, actions, flush = false, className, children }: PanelProps) {
  return (
    <section className={cn(styles.panel, className)}>
      {(title || actions) && (
        <header className={styles.panelHeader}>
          {typeof title === 'string' ? <h3 className={styles.panelTitle}>{title}</h3> : title}
          {actions}
        </header>
      )}
      <div className={flush ? undefined : styles.panelBody}>{children}</div>
    </section>
  );
}

/** Horizontal hairline divider used inside panels and cards. */
export function Divider() {
  return <hr className={styles.divider} />;
}
