/** Small status pill with subtle semantic color accents. */

import type { CSSProperties, ReactNode } from 'react';
import { cn } from '@/shared/lib/cn';
import styles from './surface.module.css';

/** Visual tone of a badge. */
export type BadgeTone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info' | 'muted';

const toneClass: Record<BadgeTone, string> = {
  neutral: '',
  accent: styles.badgeAccent,
  success: styles.badgeSuccess,
  warning: styles.badgeWarning,
  danger: styles.badgeDanger,
  info: styles.badgeInfo,
  muted: styles.badgeMuted,
};

/** Props of the Badge component. */
export interface BadgeProps {
  /** Visual tone of the pill. */
  tone?: BadgeTone;
  /** Render a small dot before the label. */
  dot?: boolean;
  /** Optional custom style for colored badges (labels, statuses). */
  style?: CSSProperties;
  children: ReactNode;
}

/**
 * Rounded pill badge used for statuses, priorities and counts.
 *
 * @param props badge tone, dot flag and content.
 * @returns rendered badge element.
 */
export function Badge({ tone = 'neutral', dot = false, style, children }: BadgeProps) {
  return (
    <span className={cn(styles.badge, toneClass[tone])} style={style}>
      {dot && <span className={styles.badgeDot} />}
      {children}
    </span>
  );
}
