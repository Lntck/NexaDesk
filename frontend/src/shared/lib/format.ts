/**
 * Date, time and text formatting helpers shared by the UI.
 */

/**
 * Format an ISO timestamp as a localized date and time.
 *
 * @param iso ISO 8601 timestamp from the API.
 * @returns formatted string, empty for missing values.
 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '';
  return new Date(iso).toLocaleString(undefined, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format a date string as a localized date.
 *
 * @param iso ISO date or timestamp.
 * @returns formatted date, empty for missing values.
 */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString(undefined, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

/**
 * Format a timestamp relative to now ("5m ago", "2h ago").
 *
 * @param iso ISO 8601 timestamp from the API.
 * @returns short relative time label.
 */
export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return '';
  const deltaMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(deltaMs / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return formatDate(iso);
}

/**
 * Build initials for an avatar circle from a username.
 *
 * @param username account name.
 * @returns up to two uppercase characters.
 */
export function initials(username: string): string {
  const parts = username
    .trim()
    .split(/[\s_.-]+/)
    .filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

/**
 * Render an estimated hours value stored as a decimal string by the API.
 *
 * @param value decimal string, number or null.
 * @returns human readable label like "8h" or an empty string.
 */
export function formatHours(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '';
  const hours = Number(value);
  if (Number.isNaN(hours)) return String(value);
  return `${hours}h`;
}

/**
 * Format a task due date relative to today for card badges.
 *
 * @param dueDate ISO date string (YYYY-MM-DD).
 * @returns label like "due today", "overdue", "due in 3d" or empty string.
 */
export function formatDueDate(dueDate: string | null | undefined): string {
  if (!dueDate) return '';
  const due = new Date(`${dueDate}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const days = Math.round((due.getTime() - today.getTime()) / 86400000);
  if (days < 0) return 'overdue';
  if (days === 0) return 'due today';
  if (days === 1) return 'due tomorrow';
  if (days <= 14) return `due in ${days}d`;
  return formatDate(dueDate);
}
