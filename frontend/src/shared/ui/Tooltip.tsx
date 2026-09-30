/** Hover tooltip anchored to a child element. */

import { useCallback, useLayoutEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import styles from './overlay.module.css';

/** Props of the Tooltip component. */
export interface TooltipProps {
  /** Tooltip text. */
  label: string;
  /** Anchor element. */
  children: ReactNode;
}

/**
 * Render a floating tooltip above the anchor on hover and focus.
 *
 * @param props label and anchor element.
 * @returns anchor wrapped with a portal-based tooltip.
 */
export function Tooltip({ label, children }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);
  const anchorRef = useRef<HTMLSpanElement | null>(null);

  const show = useCallback(() => {
    const rect = anchorRef.current?.getBoundingClientRect();
    if (!rect) return;
    setPosition({ top: rect.top - 8, left: rect.left + rect.width / 2 });
    setVisible(true);
  }, []);

  const hide = useCallback(() => setVisible(false), []);

  useLayoutEffect(() => {
    if (!visible) return;
    const onScroll = () => hide();
    window.addEventListener('scroll', onScroll, true);
    return () => window.removeEventListener('scroll', onScroll, true);
  }, [visible, hide]);

  return (
    <>
      <span
        ref={anchorRef}
        style={{ display: 'inline-flex' }}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
      >
        {children}
      </span>
      {createPortal(
        <AnimatePresence>
          {visible && position && (
            <motion.div
              className={styles.tooltip}
              style={{
                top: position.top,
                left: position.left,
                transform: 'translate(-50%, -100%)',
              }}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0, transition: { duration: 0.12 } }}
              exit={{ opacity: 0, transition: { duration: 0.1 } }}
              role="tooltip"
            >
              {label}
            </motion.div>
          )}
        </AnimatePresence>,
        document.body,
      )}
    </>
  );
}
