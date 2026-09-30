/**
 * Toast API shared by the provider component and consumers.
 *
 * The context and the hook live outside Toast.tsx so the file with the
 * provider component exports components only (react-refresh).
 */

import { createContext, useContext } from 'react';

/** Visual tone of a toast. */
export type ToastTone = 'success' | 'error' | 'info';

/** Toast descriptor passed to the push function. */
export interface ToastMessage {
  /** Short headline. */
  title: string;
  /** Optional supporting text. */
  text?: string;
  /** Visual tone. */
  tone?: ToastTone;
}

/** Context API of the toast system. */
export interface ToastApi {
  /** Show a toast; returns its id. */
  push: (message: ToastMessage) => number;
  /** Hide a toast by id. */
  dismiss: (id: number) => void;
}

export const ToastContext = createContext<ToastApi | null>(null);

/**
 * Access the toast API from any component.
 *
 * @returns toast push and dismiss functions.
 * @throws Error when used outside a ToastProvider.
 */
export function useToast(): ToastApi {
  const api = useContext(ToastContext);
  if (!api) throw new Error('useToast must be used inside ToastProvider');
  return api;
}
