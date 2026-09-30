/** Centered glass card layout for login and registration screens. */

import { Navigate, Outlet } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Layers } from 'lucide-react';
import { useSession } from '@/entities/session/hooks';
import { overlayVariants } from '@/shared/motion/variants';
import styles from './AuthLayout.module.css';

/**
 * Render the centered auth card with the routed auth form.
 *
 * Already authenticated users are redirected to the project list.
 *
 * @returns layout element for the auth screens.
 */
export function AuthLayout() {
  const { status } = useSession();

  if (status === 'authenticated') return <Navigate to="/projects" replace />;
  if (status === 'loading') {
    return (
      <div className={styles.page}>
        <div className={styles.brandMark}>
          <Layers size={22} />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <motion.div
        className={styles.card}
        variants={overlayVariants}
        initial="initial"
        animate="animate"
      >
        <div className={styles.brand}>
          <div className={styles.brandMark}>
            <Layers size={22} />
          </div>
          <div>
            <p className={styles.brandName}>NexaDesk</p>
            <p className={styles.brandTagline}>Team task management</p>
          </div>
        </div>
        <Outlet />
      </motion.div>
    </div>
  );
}
