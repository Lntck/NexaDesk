/** Right-side drawer panel with glass blur and slide motion. */

import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { cn } from '@/shared/lib/cn';
import { useFocusTrap } from '@/shared/lib/focus';
import { drawerVariants } from '@/shared/motion/variants';
import styles from './overlay.module.css';

/** Props of the Drawer component. */
export interface DrawerProps {
  /** Controls visibility. */
  open: boolean;
  /** Called on close requests. */
  onClose: () => void;
  /** Drawer title. */
  title: ReactNode;
  /** Header meta line rendered under the title. */
  subtitle?: ReactNode;
  /** Use the wider task drawer width. */
  wide?: boolean;
  /** Extra actions rendered in the header. */
  actions?: ReactNode;
  children: ReactNode;
}

/**
 * Render a right-side glass drawer in a portal.
 *
 * Locks page scroll while open and closes on Escape.
 *
 * @param props visibility, close handler, header content and body.
 * @returns portal with the animated drawer, or null when closed.
 */
export function Drawer({
  open,
  onClose,
  title,
  subtitle,
  wide = false,
  actions,
  children,
}: DrawerProps) {
  const panelRef = useRef<HTMLElement | null>(null);
  useFocusTrap(open, panelRef);

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
          className={cn(styles.backdrop, styles.drawerBackdrop)}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1, transition: { duration: 0.2 } }}
          exit={{ opacity: 0, transition: { duration: 0.15 } }}
          onClick={onClose}
        >
          <motion.aside
            ref={panelRef}
            className={cn(styles.drawer, wide && styles.drawerWide)}
            role="dialog"
            aria-modal="true"
            aria-label={typeof title === 'string' ? title : undefined}
            tabIndex={-1}
            variants={drawerVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            onClick={(event) => event.stopPropagation()}
          >
            <header className={styles.drawerHeader}>
              <div>
                {typeof title === 'string' ? <h2 className={styles.modalTitle}>{title}</h2> : title}
                {subtitle && <div style={{ marginTop: 4 }}>{subtitle}</div>}
              </div>
              <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                {actions}
                <button
                  type="button"
                  className={styles.closeButton}
                  onClick={onClose}
                  aria-label="Close"
                >
                  <X size={18} />
                </button>
              </div>
            </header>
            <div className={styles.drawerBody}>{children}</div>
          </motion.aside>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
