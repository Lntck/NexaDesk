/** Compact loading spinner. */

import { cn } from '@/shared/lib/cn';
import styles from './surface.module.css';

/** Props of the Spinner component. */
export interface SpinnerProps {
  /** Diameter in pixels. */
  size?: number;
  /** Additional class name. */
  className?: string;
}

/**
 * Render a rotating glass spinner.
 *
 * @param props size and class name.
 * @returns rendered spinner element.
 */
export function Spinner({ size = 20, className }: SpinnerProps) {
  return (
    <span
      className={cn(styles.spinner, className)}
      style={{ width: size, height: size }}
      role="status"
      aria-label="Loading"
    />
  );
}

/**
 * Render a spinner centered in the available space.
 *
 * @param props optional diameter.
 * @returns centered spinner element.
 */
export function CenteredSpinner({ size = 28 }: { size?: number }) {
  return (
    <div className={styles.centered} style={{ padding: 'var(--space-6)' }}>
      <Spinner size={size} />
    </div>
  );
}
