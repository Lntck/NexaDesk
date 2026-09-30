/** Loading placeholders with a slow shimmer. */

import type { CSSProperties } from 'react';
import { cn } from '@/shared/lib/cn';
import styles from './surface.module.css';

/** Props of the Skeleton component. */
export interface SkeletonProps {
  /** CSS width, e.g. "100%" or 120. */
  width?: number | string;
  /** CSS height. */
  height?: number | string;
  /** Corner radius class override. */
  radius?: string;
  /** Additional class name. */
  className?: string;
  /** Inline style overrides. */
  style?: CSSProperties;
}

/**
 * Render a shimmering placeholder block.
 *
 * @param props dimensions and style overrides.
 * @returns rendered skeleton element.
 */
export function Skeleton({ width = '100%', height = 16, radius, className, style }: SkeletonProps) {
  return (
    <span
      className={cn(styles.skeleton, className)}
      style={{ width, height, borderRadius: radius, ...style }}
      aria-hidden
    />
  );
}

/**
 * Render a stack of skeleton lines for text placeholders.
 *
 * @param props number of lines to render.
 * @returns rendered skeleton lines.
 */
export function SkeletonLines({ lines = 3 }: { lines?: number }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {Array.from({ length: lines }, (_, index) => (
        <Skeleton key={index} height={14} width={index === lines - 1 ? '60%' : '100%'} />
      ))}
    </div>
  );
}
