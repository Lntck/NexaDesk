/** Modal dialog with heavy backdrop blur and scale/fade motion. */

import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { cn } from '@/shared/lib/cn';
import { useFocusTrap } from '@/shared/lib/focus';
import { overlayVariants } from '@/shared/motion/variants';
import styles from './overlay.module.css';

/** Width variant of the modal. */
export type ModalSize = 'sm' | 'md' | 'lg';

/** Props of the Modal component. */
export interface ModalProps {
  /** Controls visibility. */
  open: boolean;
  /** Called on close requests (backdrop click, Escape, close button). */
  onClose: () => void;
  /** Dialog title. */
  title: string;
  /** Width variant. */
  size?: ModalSize;
  /** Footer actions, usually buttons. */
  footer?: ReactNode;
  children: ReactNode;
}

const sizeClass: Record<ModalSize, string> = {
  sm: styles.modalSm,
  md: '',
  lg: styles.modalLg,
};

/**
 * Render a centered glass dialog in a portal.
 *
 * Locks page scroll while open, traps keyboard focus and closes on Escape
 * or backdrop click.
 *
 * @param props visibility, close handler, title, size and slots.
 * @returns portal with the animated dialog, or null when closed.
 */
export function Modal({ open, onClose, title, size = 'md', footer, children }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement | null>(null);
  useFocusTrap(open, dialogRef);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [open, onClose]);

  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          className={styles.backdrop}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1, transition: { duration: 0.2 } }}
          exit={{ opacity: 0, transition: { duration: 0.15 } }}
          onClick={onClose}
        >
          <motion.div
            ref={dialogRef}
            className={cn(styles.modal, sizeClass[size])}
            role="dialog"
            aria-modal="true"
            aria-label={title}
            tabIndex={-1}
            variants={overlayVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            onClick={(event) => event.stopPropagation()}
          >
            <header className={styles.modalHeader}>
              <h2 className={styles.modalTitle}>{title}</h2>
              <button
                type="button"
                className={styles.closeButton}
                onClick={onClose}
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </header>
            <div className={styles.modalBody}>{children}</div>
            {footer && <footer className={styles.modalFooter}>{footer}</footer>}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
