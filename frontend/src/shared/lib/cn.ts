/**
 * Small class name helper for conditional CSS modules.
 *
 * @param values class names; falsy values are dropped.
 * @returns space separated class name string.
 */
export function cn(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(' ');
}
