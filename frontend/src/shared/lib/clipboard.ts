/** Clipboard helpers shared by copy actions across the app. */

/**
 * Copy a text snippet to the system clipboard.
 *
 * @param text text to copy.
 * @returns true when the copy succeeded, false otherwise.
 */
export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
