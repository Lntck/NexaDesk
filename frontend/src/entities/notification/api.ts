/** REST calls for user notifications. */

import { apiRequest, withQuery } from '@/shared/api/client';
import type { NotificationRead, Paginated } from '@/shared/api/types';

/**
 * List notifications of the current user.
 *
 * @param read read-state filter; null returns everything.
 * @param page page number.
 * @returns paginated notification list.
 */
export function listNotifications(
  read: boolean | null,
  page = 1,
): Promise<Paginated<NotificationRead>> {
  return apiRequest('GET', withQuery('/api/v1/notifications', { read, page, page_size: 20 }));
}

/**
 * Mark one notification as read (no-op when already read).
 *
 * @param notificationId notification id.
 * @returns the updated notification.
 */
export function markNotificationRead(notificationId: number): Promise<NotificationRead> {
  return apiRequest('POST', `/api/v1/notifications/${notificationId}/read`);
}

/**
 * Mark all notifications of the current user as read.
 */
export function markAllNotificationsRead(): Promise<void> {
  return apiRequest('POST', '/api/v1/notifications/read-all');
}
