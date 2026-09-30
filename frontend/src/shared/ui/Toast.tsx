/**
 * Toast notification stack with a small imperative API.
 *
 * Toasts slide in from the top right, auto-dismiss after five seconds and the
 * stack keeps at most four items (frontend/PLAN.md, "Анимации").
 */

import { useCallback, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { CheckCircle2, Info, X, XCircle } from 'lucide-react';
import { toastVariants } from '@/shared/motion/variants';
import { ToastContext, type ToastApi, type ToastMessage, type ToastTone } from './toastContext';
import styles from './overlay.module.css';

interface ToastEntry extends ToastMessage {
  id: number;
  tone: ToastTone;
}

const MAX_TOASTS = 4;
const TOAST_TTL_MS = 5000;

const toneIcon: Record<ToastTone, React.ReactNode> = {
  success: <CheckCircle2 size={18} />,
  error: <XCircle size={18} />,
  info: <Info size={18} />,
};

/** Props of the ToastProvider. */
export interface ToastProviderProps {
  children: React.ReactNode;
}

/**
 * Provide the toast API to the app and render the toast stack.
 *
 * @param props application children.
 * @returns provider with the toast viewport in a portal.
 */
export function ToastProvider({ children }: ToastProviderProps) {
  const [toasts, setToasts] = useState<ToastEntry[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const push = useCallback(
    (message: ToastMessage) => {
      const id = nextId.current++;
      const entry: ToastEntry = { ...message, id, tone: message.tone ?? 'info' };
      setToasts((current) => [...current.slice(-(MAX_TOASTS - 1)), entry]);
      window.setTimeout(() => dismiss(id), TOAST_TTL_MS);
      return id;
    },
    [dismiss],
  );

  const api = useMemo<ToastApi>(() => ({ push, dismiss }), [push, dismiss]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      {createPortal(
        <div className={styles.toastViewport} role="status" aria-live="polite">
          <AnimatePresence initial={false}>
            {toasts.map((toast) => (
              <motion.div
                key={toast.id}
                className={`${styles.toast} ${styles[`toast${capitalize(toast.tone)}`]}`}
                variants={toastVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                layout
              >
                <span className={styles.toastIcon}>{toneIcon[toast.tone]}</span>
                <div className={styles.toastContent}>
                  <p className={styles.toastTitle}>{toast.title}</p>
                  {toast.text && <p className={styles.toastText}>{toast.text}</p>}
                </div>
                <button
                  type="button"
                  className={styles.closeButton}
                  onClick={() => dismiss(toast.id)}
                  aria-label="Dismiss"
                >
                  <X size={16} />
                </button>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>,
        document.body,
      )}
    </ToastContext.Provider>
  );
}

/**
 * Capitalize a tone name to build the CSS module class.
 *
 * @param tone toast tone.
 * @returns capitalized tone name.
 */
function capitalize(tone: ToastTone): string {
  return tone.charAt(0).toUpperCase() + tone.slice(1);
}
