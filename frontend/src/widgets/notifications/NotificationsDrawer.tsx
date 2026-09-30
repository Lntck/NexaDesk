/** Notification drawer with read-state filter and mark-as-read actions. */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { CheckCheck, Inbox } from 'lucide-react';
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
} from '@/entities/notification/hooks';
import { notificationTarget, notificationText } from '@/entities/notification/model';
import type { NotificationRead } from '@/shared/api/types';
import { formatRelative } from '@/shared/lib/format';
import { listItemVariants } from '@/shared/motion/variants';
import { Button, Drawer, EmptyState, SkeletonLines, Tabs } from '@/shared/ui';
import styles from './Notifications.module.css';

/** Props of the NotificationsDrawer. */
export interface NotificationsDrawerProps {
  /** Controls visibility. */
  open: boolean;
  /** Called on close requests. */
  onClose: () => void;
}

/**
 * Render the notification drawer with filtering and read-state actions.
 *
 * @param props visibility and close handler.
 * @returns drawer element with the notification list.
 */
export function NotificationsDrawer({ open, onClose }: NotificationsDrawerProps) {
  const [tab, setTab] = useState<'all' | 'unread'>('all');
  const readFilter = tab === 'unread' ? false : null;
  const { data, isLoading } = useNotifications(open ? readFilter : null);
  const markRead = useMarkNotificationRead();
  const markAll = useMarkAllNotificationsRead();
  const navigate = useNavigate();

  /**
   * Open the notification target and mark the notice as read.
   *
   * @param notification clicked notification.
   */
  const handleOpen = (notification: NotificationRead) => {
    if (!notification.is_read) markRead.mutate(notification.id);
    const target = notificationTarget(notification);
    if (target) {
      navigate(target);
      onClose();
    }
  };

  const items = data?.items ?? [];

  return (
    <Drawer open={open} onClose={onClose} title="Notifications">
      <div className={styles.drawerToolbar}>
        <Tabs
          items={[
            { value: 'all', label: 'All' },
            { value: 'unread', label: 'Unread' },
          ]}
          value={tab}
          onChange={(value) => setTab(value as 'all' | 'unread')}
        />
        <Button
          size="sm"
          variant="ghost"
          icon={<CheckCheck size={16} />}
          loading={markAll.isPending}
          onClick={() => markAll.mutate()}
        >
          Mark all read
        </Button>
      </div>

      {isLoading ? (
        <SkeletonLines lines={5} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<Inbox size={24} />}
          title="Nothing here"
          text={
            tab === 'unread'
              ? 'You have no unread notifications.'
              : 'Notifications will appear here.'
          }
        />
      ) : (
        <ul className={styles.list}>
          <AnimatePresence initial={false}>
            {items.map((notification) => (
              <motion.li
                key={notification.id}
                variants={listItemVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                layout
              >
                <button
                  type="button"
                  className={`${styles.item} ${notification.is_read ? '' : styles.itemUnread}`}
                  onClick={() => handleOpen(notification)}
                >
                  <span className={styles.itemDot} data-read={notification.is_read} />
                  <span className={styles.itemBody}>
                    <span className={styles.itemText}>{notificationText(notification)}</span>
                    <span className={styles.itemTime}>
                      {formatRelative(notification.created_at)}
                    </span>
                  </span>
                </button>
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </Drawer>
  );
}
