/** Notification bell with unread counter and drawer. */

import { useState } from 'react';
import { Bell } from 'lucide-react';
import { useUnreadCount } from '@/entities/notification/hooks';
import { NotificationsDrawer } from './NotificationsDrawer';
import styles from './Notifications.module.css';

/**
 * Render the topbar notification bell.
 *
 * @returns bell button with unread badge and drawer trigger.
 */
export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const { data: unread = 0 } = useUnreadCount();

  return (
    <>
      <button
        type="button"
        className={styles.bell}
        onClick={() => setOpen(true)}
        aria-label={`Notifications${unread > 0 ? `, ${unread} unread` : ''}`}
      >
        <Bell size={18} />
        {unread > 0 && <span className={styles.badge}>{unread > 99 ? '99+' : unread}</span>}
      </button>
      <NotificationsDrawer open={open} onClose={() => setOpen(false)} />
    </>
  );
}
