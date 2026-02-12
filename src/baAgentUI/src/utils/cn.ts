// ============================================================
// Utility: className merge function
// Lightweight alternative to classnames library
// ============================================================

export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}
