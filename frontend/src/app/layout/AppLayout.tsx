/** Authenticated app shell: glass sidebar, topbar and animated page outlet. */

import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { screenVariants } from '@/shared/motion/variants';
import { Sidebar } from '@/widgets/sidebar/Sidebar';
import { Topbar } from '@/widgets/topbar/Topbar';
import styles from './AppLayout.module.css';

/**
 * Render the application shell with sidebar, topbar and routed content.
 *
 * @returns layout element with animated page transitions.
 */
export function AppLayout() {
  const location = useLocation();

  return (
    <div className={styles.shell}>
      <Sidebar />
      <div className={styles.main}>
        <Topbar />
        <main className={styles.content}>
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={location.pathname}
              className={styles.page}
              variants={screenVariants}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
