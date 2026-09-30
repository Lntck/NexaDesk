/** Segmented tab control with glass active state. */

import { useRef } from 'react';
import styles from './surface.module.css';
import { cn } from '@/shared/lib/cn';

/** One tab entry. */
export interface TabItem {
  /** Stable value of the tab. */
  value: string;
  /** Visible label. */
  label: string;
}

/** Props of the Tabs component. */
export interface TabsProps {
  /** All tab entries. */
  items: TabItem[];
  /** Currently selected tab value. */
  value: string;
  /** Called when a tab is selected. */
  onChange: (value: string) => void;
  /** Accessible name of the tab list. */
  ariaLabel?: string;
}

/**
 * Render a pill-style tab list.
 *
 * Supports roving tabindex: the selected tab is in the tab order and arrow
 * keys move focus and selection between tabs.
 *
 * @param props items, selection and change handler.
 * @returns rendered tab list element.
 */
export function Tabs({ items, value, onChange, ariaLabel }: TabsProps) {
  const listRef = useRef<HTMLDivElement | null>(null);
  const selectedIndex = Math.max(
    0,
    items.findIndex((item) => item.value === value),
  );

  /**
   * Move focus and selection by a step in the tab list.
   *
   * @param step index delta, wrapping around the list.
   */
  const move = (step: number) => {
    const nextIndex = (selectedIndex + step + items.length) % items.length;
    const next = items[nextIndex];
    if (!next) return;
    onChange(next.value);
    const buttons = listRef.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]');
    buttons?.[nextIndex]?.focus();
  };

  return (
    <div className={styles.tabs} role="tablist" aria-label={ariaLabel} ref={listRef}>
      {items.map((item, index) => (
        <button
          key={item.value}
          type="button"
          role="tab"
          aria-selected={item.value === value}
          tabIndex={index === selectedIndex ? 0 : -1}
          className={cn(styles.tab, item.value === value && styles.tabActive)}
          onClick={() => onChange(item.value)}
          onKeyDown={(event) => {
            if (event.key === 'ArrowRight') {
              event.preventDefault();
              move(1);
            } else if (event.key === 'ArrowLeft') {
              event.preventDefault();
              move(-1);
            } else if (event.key === 'Home') {
              event.preventDefault();
              move(-selectedIndex);
            } else if (event.key === 'End') {
              event.preventDefault();
              move(items.length - 1 - selectedIndex);
            }
          }}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
