// ============================================================
// Haystack Helper Utilities
// Utilities for working with haystack-core types
// ============================================================

import { HDict, HVal, HStr, HNum, HBool, HRef, HDateTime, HDate, HTime, HGrid } from 'haystack-core';

/**
 * Safely get a string value from a Haystack dict
 */
export function getString(dict: HDict, key: string, defaultValue = ''): string {
  const val = dict.get(key);
  return val instanceof HStr ? val.value : defaultValue;
}

/**
 * Safely get a number value from a Haystack dict
 */
export function getNumber(dict: HDict, key: string, defaultValue = 0): number {
  const val = dict.get(key);
  return val instanceof HNum ? val.value : defaultValue;
}

/**
 * Safely get a boolean value from a Haystack dict
 */
export function getBoolean(dict: HDict, key: string, defaultValue = false): boolean {
  const val = dict.get(key);
  return val instanceof HBool ? val.value : defaultValue;
}

/**
 * Safely get a reference ID from a Haystack dict
 */
export function getRefId(dict: HDict, key: string): string {
  const val = dict.get(key);
  return val instanceof HRef ? val.value : '';
}

/**
 * Get display name from a Haystack record
 */
export function getDisplayName(dict: HDict): string {
  return getString(dict, 'dis') || getString(dict, 'id');
}

/**
 * Convert Haystack value to JavaScript primitive
 */
export function haystackToJs(val: HVal | null | undefined): unknown {
  if (val === null || val === undefined) return null;

  if (val instanceof HStr) return val.value;
  if (val instanceof HNum) return val.value;
  if (val instanceof HBool) return val.value;
  if (val instanceof HRef) return val.value;
  if (val instanceof HDateTime) return val.date;
  if (val instanceof HDate) return val.date;
  if (val instanceof HTime) {
    const date = new Date();
    date.setHours(val.hours, val.minutes, val.seconds ?? 0, 0);
    return date;
  }

  // For complex types, use zinc encoding
  return val.toZinc();
}

/**
 * Convert a Haystack Grid to an array of plain objects
 */
export function gridToArray(grid: HGrid<HDict>): Record<string, unknown>[] {
  const result: Record<string, unknown>[] = [];
  for (const row of grid) {
    const obj: Record<string, unknown> = {};

    for (const col of row) {
      obj[col.name] = haystackToJs(col.value);
    }

    result.push(obj);
  }

  return result;
}

/**
 * Parse severity from a Haystack record
 */
export function parseSeverity(dict: HDict): 'critical' | 'high' | 'medium' | 'low' | 'info' {
  const priority = getNumber(dict, 'priority', 99);

  if (priority <= 1) return 'critical';
  if (priority <= 3) return 'high';
  if (priority <= 5) return 'medium';
  if (priority <= 7) return 'low';
  return 'info';
}

/**
 * Format a Haystack value for display
 */
export function formatHaystackValue(val: HVal | null | undefined, unit?: string): string {
  if (val === null || val === undefined) return '—';

  if (val instanceof HNum) {
    const num = val.value;
    const u = unit || val.unit || '';
    return `${num.toFixed(u ? 1 : 0)}${u ? ' ' + u : ''}`;
  }

  if (val instanceof HBool) {
    return val.value ? 'Yes' : 'No';
  }

  if (val instanceof HDateTime) {
    return val.date.toLocaleString();
  }

  if (val instanceof HDate) {
    return val.date.toLocaleDateString();
  }

  return val.toZinc();
}

/**
 * Extract equipment ID from various Haystack reference formats
 */
export function normalizeEquipRef(ref: string | HRef | undefined): string {
  if (!ref) return '';
  if (ref instanceof HRef) return ref.value;
  if (ref.startsWith('@')) return ref;
  return `@${ref}`;
}

/**
 * Build a Haystack filter expression for equipment queries
 */
export function buildEquipmentFilter(options: {
  type?: string;
  siteRef?: string;
  equipRef?: string;
}): string {
  const parts: string[] = ['equip'];

  if (options.type) {
    parts.push(`and equip==${options.type}`);
  }

  if (options.siteRef) {
    parts.push(`and siteRef==${options.siteRef}`);
  }

  if (options.equipRef) {
    parts.push(`and id==${options.equipRef}`);
  }

  return parts.join(' ');
}

/**
 * Build a Haystack filter expression for point queries
 */
export function buildPointFilter(options: {
  equipRef?: string;
  kind?: string;
  unit?: string;
  hasCurVal?: boolean;
}): string {
  const parts: string[] = ['point'];

  if (options.equipRef) {
    parts.push(`and equipRef==${options.equipRef}`);
  }

  if (options.kind) {
    parts.push(`and kind==${options.kind}`);
  }

  if (options.unit) {
    parts.push(`and unit==${options.unit}`);
  }

  if (options.hasCurVal) {
    parts.push('and curVal');
  }

  return parts.join(' ');
}
