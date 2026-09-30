/** Shared motion presets for screens, overlays and list items. */

import type { Variants } from 'framer-motion';

/** Standard easing curves from the design tokens. */
export const EASE_STANDARD: [number, number, number, number] = [0.2, 0.8, 0.2, 1];
export const EASE_EXIT: [number, number, number, number] = [0.4, 0, 1, 1];

/** Screen transition: fade with a small slide (200 ms). */
export const screenVariants: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.2, ease: EASE_STANDARD } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.15, ease: EASE_EXIT } },
};

/** Overlay transition: scale 0.98 to 1 with fade (200 ms). */
export const overlayVariants: Variants = {
  initial: { opacity: 0, scale: 0.98 },
  animate: { opacity: 1, scale: 1, transition: { duration: 0.2, ease: EASE_STANDARD } },
  exit: { opacity: 0, scale: 0.98, transition: { duration: 0.15, ease: EASE_EXIT } },
};

/** Drawer transition: slide in from the right edge. */
export const drawerVariants: Variants = {
  initial: { opacity: 0, x: 24 },
  animate: { opacity: 1, x: 0, transition: { duration: 0.2, ease: EASE_STANDARD } },
  exit: { opacity: 0, x: 24, transition: { duration: 0.15, ease: EASE_EXIT } },
};

/** List item transition: fade with a 12px slide. */
export const listItemVariants: Variants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.2, ease: EASE_STANDARD } },
  exit: { opacity: 0, transition: { duration: 0.15, ease: EASE_EXIT } },
};

/** Toast transition: slide in from the top right corner. */
export const toastVariants: Variants = {
  initial: { opacity: 0, x: 32, y: -8 },
  animate: { opacity: 1, x: 0, y: 0, transition: { duration: 0.2, ease: EASE_STANDARD } },
  exit: { opacity: 0, x: 32, transition: { duration: 0.15, ease: EASE_EXIT } },
};
