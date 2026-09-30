/** TanStack Query hooks for notifications and the unread counter. */

import { useMutation, useQuery, useQueryClient, type UseQueryResult } from '@tanstack/react-query';
import { queryKeys } from '@/shared/api/queryKeys';
import type { NotificationRead, Paginated } from '@/shared/api/types';
import { listNotifications, markAllNotificationsRead, markNotificationRead } from './api';

/**
 * Query a notification page with an optional read-state filter.
 *
 * @param read read-state filter; null returns everything.
 * @param page page number.
 * @returns paginated notification list query result.
 */
export function useNotifications(
  read: boolean | null,
  page = 1,
): UseQueryResult<Paginated<NotificationRead>> {
  return useQuery({
    queryKey: [...queryKeys.notifications(read), page],
    queryFn: () => listNotifications(read, page),
  });
}

/**
 * Query the unread notification counter.
 *
 * Backed by the unread-only notification page so the bell badge and the
 * drawer share one source of truth.
 *
 * @returns unread count query result.
 */
export function useUnreadCount(): UseQueryResult<number> {
  return useQuery({
    queryKey: [...queryKeys.notifications(false), 'count'],
    queryFn: async () => (await listNotifications(false, 1)).total,
    refetchOnWindowFocus: true,
    select: (total) => total,
  });
}

/**
 * Mark one notification as read.
 *
 * @returns mark-read mutation.
 */
export function useMarkNotificationRead() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: number) => markNotificationRead(notificationId),
    onSuccess: () => invalidateNotifications(client.invalidateQueries.bind(client)),
  });
}

/**
 * Mark every notification as read.
 *
 * @returns mark-all mutation.
 */
export function useMarkAllNotificationsRead() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => markAllNotificationsRead(),
    onSuccess: () => invalidateNotifications(client.invalidateQueries.bind(client)),
  });
}

/**
 * Invalidate every notification cache after a read-state change.
 *
 * @param invalidate query client invalidation function.
 */
function invalidateNotifications(
  invalidate: (filters: { queryKey: readonly unknown[] }) => Promise<void>,
): void {
  void invalidate({ queryKey: ['notifications'] });
}
