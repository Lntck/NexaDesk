/** Translucent glass card surface. */

import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '@/shared/lib/cn';
import styles from './surface.module.css';

/** Props of the Card component. */
export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Clickable card gets hover and active states. */
  interactive?: boolean;
  /** Inner padding; "none" leaves spacing to the caller. */
  padding?: 'none' | 'sm' | 'md';
  children: ReactNode;
}

const paddingStyle: Record<NonNullable<CardProps['padding']>, string | undefined> = {
  none: undefined,
  sm: 'var(--space-3)',
  md: 'var(--space-4)',
};

/**
 * Render a dark translucent card with a thin border and soft depth.
 *
 * @param props interaction flag, padding and standard div attributes.
 * @returns rendered card element.
 */
export function Card({
  interactive = false,
  padding = 'md',
  className,
  children,
  ...rest
}: CardProps) {
  return (
    <div
      className={cn(styles.card, interactive && styles.cardInteractive, className)}
      style={{ padding: paddingStyle[padding], ...rest.style }}
      {...rest}
    >
      {children}
    </div>
  );
}
