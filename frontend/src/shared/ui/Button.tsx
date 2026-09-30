/** Glass button with variants, sizes and loading state. */

import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { cn } from '@/shared/lib/cn';
import { Spinner } from './Spinner';
import styles from './controls.module.css';

/** Visual variant of the button. */
export type ButtonVariant = 'primary' | 'secondary' | 'accent' | 'ghost' | 'danger';

/** Size of the button. */
export type ButtonSize = 'sm' | 'md' | 'lg';

/** Props of the Button component. */
export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual variant. */
  variant?: ButtonVariant;
  /** Size of the button. */
  size?: ButtonSize;
  /** Leading icon element. */
  icon?: ReactNode;
  /** Show a spinner and block clicks. */
  loading?: boolean;
  /** Stretch the button to the container width. */
  block?: boolean;
  /** Icon-only square button. */
  iconOnly?: boolean;
}

const variantClass: Record<ButtonVariant, string> = {
  primary: styles.buttonPrimary,
  secondary: '',
  accent: styles.buttonAccent,
  ghost: styles.buttonGhost,
  danger: styles.buttonDanger,
};

const sizeClass: Record<ButtonSize, string> = {
  sm: styles.buttonSm,
  md: '',
  lg: styles.buttonLg,
};

/**
 * Render a glass button with optional icon and loading state.
 *
 * @param props variant, size, icon, loading and native button attributes.
 * @returns rendered button element.
 */
export function Button({
  variant = 'secondary',
  size = 'md',
  icon,
  loading = false,
  block = false,
  iconOnly = false,
  className,
  children,
  disabled,
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        styles.button,
        variantClass[variant],
        sizeClass[size],
        block && styles.buttonBlock,
        iconOnly && styles.buttonIcon,
        className,
      )}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? (
        <span className={styles.spinnerSlot}>
          <Spinner size={size === 'sm' ? 12 : 14} />
        </span>
      ) : (
        icon
      )}
      {children}
    </button>
  );
}
