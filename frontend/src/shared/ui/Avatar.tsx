/** Initials avatar in a glass circle. */

import { cn } from '@/shared/lib/cn';
import { initials } from '@/shared/lib/format';
import styles from './surface.module.css';

/** Size variants of the Avatar component. */
export type AvatarSize = 'sm' | 'md' | 'lg';

/** Props of the Avatar component. */
export interface AvatarProps {
  /** Username rendered as initials. */
  username: string;
  /** Circle size. */
  size?: AvatarSize;
}

const sizeClass: Record<AvatarSize, string> = {
  sm: styles.avatarSm,
  md: '',
  lg: styles.avatarLg,
};

/**
 * Render a user avatar circle with initials.
 *
 * @param props username and size.
 * @returns rendered avatar element.
 */
export function Avatar({ username, size = 'md' }: AvatarProps) {
  return (
    <span
      className={cn(styles.avatar, sizeClass[size])}
      title={username}
      aria-label={username}
      role="img"
    >
      {initials(username)}
    </span>
  );
}
