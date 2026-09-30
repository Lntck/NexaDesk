/**
 * Color helpers for dynamic accents such as label and status colors.
 */

/**
 * Convert a #RRGGBB color to an rgba() string with the given alpha.
 *
 * @param hex hex color, with or without the leading hash.
 * @param alpha opacity between 0 and 1.
 * @returns rgba() color string; falls back to a neutral accent for bad input.
 */
export function hexToRgba(hex: string, alpha: number): string {
  const clean = hex.replace('#', '');
  if (!/^[0-9a-fA-F]{6}$/.test(clean)) return `rgba(138, 180, 255, ${alpha})`;
  const number = Number.parseInt(clean, 16);
  const r = (number >> 16) & 255;
  const g = (number >> 8) & 255;
  const b = number & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * Pick a readable text color for a solid background.
 *
 * @param hex hex background color.
 * @returns dark or light text color keeping contrast readable.
 */
export function readableText(hex: string): string {
  const clean = hex.replace('#', '');
  if (!/^[0-9a-fA-F]{6}$/.test(clean)) return '#F5F7FA';
  const number = Number.parseInt(clean, 16);
  const r = (number >> 16) & 255;
  const g = (number >> 8) & 255;
  const b = number & 255;
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.6 ? '#05070B' : '#F5F7FA';
}
