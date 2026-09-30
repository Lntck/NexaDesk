/** Labeled form controls: input, textarea and select with hint and error slots. */

import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react';
import { cn } from '@/shared/lib/cn';
import styles from './controls.module.css';

/** Shared props of all labeled controls. */
interface FieldShellProps {
  /** Visible label above the control. */
  label?: ReactNode;
  /** Helper text below the control. */
  hint?: ReactNode;
  /** Validation message below the control. */
  error?: ReactNode;
  /** Mark the label as required. */
  required?: boolean;
}

/**
 * Wrap a control with label, hint and error slots.
 *
 * @param props label, hint, error and control element.
 * @returns rendered field block.
 */
function FieldShell({
  label,
  hint,
  error,
  required,
  children,
}: FieldShellProps & { children: ReactNode }) {
  return (
    <div className={styles.field}>
      {label && (
        <label className={styles.label}>
          {label}
          {required && <span className={styles.required}> *</span>}
        </label>
      )}
      {children}
      {error ? (
        <span className={styles.error}>{error}</span>
      ) : (
        hint && <span className={styles.hint}>{hint}</span>
      )}
    </div>
  );
}

/** Props of the Input component. */
export interface InputProps extends FieldShellProps, InputHTMLAttributes<HTMLInputElement> {}

/**
 * Render a labeled single-line input.
 *
 * @param props field slots and native input attributes.
 * @returns rendered input field.
 */
export function Input({ label, hint, error, required, className, ...rest }: InputProps) {
  return (
    <FieldShell label={label} hint={hint} error={error} required={required}>
      <input className={cn(styles.input, Boolean(error) && styles.invalid, className)} {...rest} />
    </FieldShell>
  );
}

/** Props of the Textarea component. */
export interface TextareaProps
  extends FieldShellProps, TextareaHTMLAttributes<HTMLTextAreaElement> {}

/**
 * Render a labeled multi-line textarea.
 *
 * @param props field slots and native textarea attributes.
 * @returns rendered textarea field.
 */
export function Textarea({ label, hint, error, required, className, ...rest }: TextareaProps) {
  return (
    <FieldShell label={label} hint={hint} error={error} required={required}>
      <textarea
        className={cn(styles.textarea, Boolean(error) && styles.invalid, className)}
        {...rest}
      />
    </FieldShell>
  );
}

/** Props of the Select component. */
export interface SelectProps extends FieldShellProps, SelectHTMLAttributes<HTMLSelectElement> {}

/**
 * Render a labeled select control.
 *
 * @param props field slots, options as children and native select attributes.
 * @returns rendered select field.
 */
export function Select({
  label,
  hint,
  error,
  required,
  className,
  children,
  ...rest
}: SelectProps) {
  return (
    <FieldShell label={label} hint={hint} error={error} required={required}>
      <select className={cn(styles.select, Boolean(error) && styles.invalid, className)} {...rest}>
        {children}
      </select>
    </FieldShell>
  );
}
