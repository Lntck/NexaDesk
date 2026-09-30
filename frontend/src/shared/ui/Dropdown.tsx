/** Dropdown menu anchored to a trigger button. */

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { KeyboardEvent as ReactKeyboardEvent, ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { overlayVariants } from '@/shared/motion/variants';
import styles from './overlay.module.css';

/** Props of the Dropdown component. */
export interface DropdownProps {
  /** Element that opens the menu. */
  trigger: (props: { open: boolean; toggle: () => void }) => ReactNode;
  /** Menu content rendered inside the floating panel. */
  children: (props: { close: () => void }) => ReactNode;
  /** Preferred alignment relative to the trigger. */
  align?: 'start' | 'end';
  /** Minimum menu width in pixels. */
  minWidth?: number;
}

/**
 * Render a floating glass menu below a trigger element.
 *
 * Closes on outside click, Escape and scroll. Positions itself with fixed
 * coordinates measured from the trigger. Arrow keys move between menu items,
 * Escape returns focus to the trigger.
 *
 * @param props trigger render prop, menu content and alignment.
 * @returns rendered trigger and portal-based menu.
 */
export function Dropdown({ trigger, children, align = 'start', minWidth = 200 }: DropdownProps) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);
  const triggerRef = useRef<HTMLSpanElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const pendingFocus = useRef<'first' | 'last' | null>(null);

  const close = useCallback(() => setOpen(false), []);
  const toggle = useCallback(() => setOpen((value) => !value), []);

  /** Menu entries in DOM order. */
  const menuItems = useCallback((): HTMLElement[] => {
    const menu = menuRef.current;
    if (!menu) return [];
    return Array.from(menu.querySelectorAll<HTMLElement>('[role="menuitem"]'));
  }, []);

  /** Move focus back to the trigger button. */
  const focusTrigger = useCallback(() => {
    triggerRef.current?.querySelector<HTMLElement>('button')?.focus();
  }, []);

  /**
   * Open the menu from the keyboard and focus an edge item.
   *
   * @param target first or last menu entry to focus.
   */
  const openWithFocus = (target: 'first' | 'last') => {
    pendingFocus.current = target;
    setOpen(true);
  };

  useLayoutEffect(() => {
    if (!open) return;
    const rect = triggerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const left = align === 'end' ? rect.right - minWidth : rect.left;
    setPosition({ top: rect.bottom + 8, left: Math.max(8, left) });
  }, [open, align, minWidth]);

  useEffect(() => {
    if (!open) return;
    const target = pendingFocus.current;
    pendingFocus.current = null;
    if (!target) return;
    const items = menuItems();
    (target === 'first' ? items[0] : items[items.length - 1])?.focus();
  }, [open, menuItems]);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (triggerRef.current?.contains(target)) return;
      const menu = document.getElementById('dropdown-portal');
      if (menu?.contains(target)) return;
      close();
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        close();
        focusTrigger();
      }
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    window.addEventListener('resize', close);
    window.addEventListener('scroll', close, true);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('resize', close);
      window.removeEventListener('scroll', close, true);
    };
  }, [open, close, focusTrigger]);

  /**
   * Handle arrow keys while the menu is closed (on the trigger).
   *
   * @param event keyboard event from the trigger.
   */
  const onTriggerKeyDown = (event: ReactKeyboardEvent) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      event.stopPropagation();
      openWithFocus('first');
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      event.stopPropagation();
      openWithFocus('last');
    }
  };

  /**
   * Handle arrow keys, Home/End and Escape inside the open menu.
   *
   * @param event keyboard event from the menu panel.
   */
  const onMenuKeyDown = (event: ReactKeyboardEvent) => {
    const items = menuItems();
    const index = items.indexOf(document.activeElement as HTMLElement);
    const current = index === -1 ? 0 : index;
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        items[(current + 1) % items.length]?.focus();
        break;
      case 'ArrowUp':
        event.preventDefault();
        items[(current - 1 + items.length) % items.length]?.focus();
        break;
      case 'Home':
        event.preventDefault();
        items[0]?.focus();
        break;
      case 'End':
        event.preventDefault();
        items[items.length - 1]?.focus();
        break;
      case 'Escape':
        event.preventDefault();
        event.stopPropagation();
        close();
        focusTrigger();
        break;
      case 'Tab':
        close();
        break;
      default:
        break;
    }
  };

  return (
    <>
      <span ref={triggerRef} style={{ display: 'inline-flex' }} onKeyDown={onTriggerKeyDown}>
        {trigger({ open, toggle })}
      </span>
      {createPortal(
        <AnimatePresence>
          {open && position && (
            <motion.div
              id="dropdown-portal"
              ref={menuRef}
              className={styles.dropdown}
              style={{ top: position.top, left: position.left, minWidth }}
              role="menu"
              onKeyDown={onMenuKeyDown}
              variants={overlayVariants}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              {children({ close })}
            </motion.div>
          )}
        </AnimatePresence>,
        document.body,
      )}
    </>
  );
}

/** Props of one dropdown item. */
export interface DropdownItemProps {
  /** Leading icon element. */
  icon?: ReactNode;
  /** Destructive styling. */
  danger?: boolean;
  /** Highlighted (selected) item. */
  active?: boolean;
  /** Click handler; receives the menu close function. */
  onClick: () => void;
  children: ReactNode;
}

/**
 * Render one clickable entry of a dropdown menu.
 *
 * @param props icon, danger flag, click handler and label.
 * @returns rendered menu item button.
 */
export function DropdownItem({
  icon,
  danger = false,
  active = false,
  onClick,
  children,
}: DropdownItemProps) {
  return (
    <button
      type="button"
      role="menuitem"
      className={`${styles.dropdownItem} ${danger ? styles.dropdownItemDanger : ''} ${active ? styles.dropdownItemActive : ''}`}
      onClick={onClick}
    >
      {icon}
      {children}
    </button>
  );
}

/**
 * Render a small uppercase section label inside a dropdown.
 *
 * @param props label text and content.
 * @returns rendered label element.
 */
export function DropdownLabel({ children }: { children: ReactNode }) {
  return (
    <div className={styles.dropdownLabel} role="presentation">
      {children}
    </div>
  );
}

/**
 * Render a hairline divider inside a dropdown.
 *
 * @returns rendered divider element.
 */
export function DropdownDivider() {
  return <div className={styles.dropdownDivider} role="presentation" />;
}
