// ============================================================
// Haystack Service
// Simple HTTP client for Haystack 3.0 API
// Uses JSON format for requests, parses JSON responses
// ============================================================

import {
  HGrid,
  HDict,
  HVal,
  HStr,
  HNum,
  HBool,
  HRef,
  HDate,
  HDateTime,
  HSymbol,
  HUri,
  HList,
  HMarker,
  Kind,
  isHVal,
  valueIsKind,
} from 'haystack-core';

const HAYSTACK_PROJECT = import.meta.env.VITE_HAYSTACK_PROJECT || 'demo';
const HAYSTACK_BASE_URL = import.meta.env.VITE_HAYSTACK_API_URL || '/api';

export type HaystackOp =
  | 'about' | 'close' | 'commit' | 'defs' | 'eval' | 'evalAll'
  | 'filetypes' | 'hisRead' | 'hisWrite' | 'invokeAction'
  | 'libs' | 'nav' | 'ops' | 'pointWrite' | 'read'
  | 'rec' | 'watchPoll' | 'watchSub' | 'watchUnsub';

// Re-export types for convenience
export type { HVal, HGrid, HDict, HList, HStr, HBool, HNum, HRef, HDate, HDateTime, HSymbol, HUri };
export { Kind, isHVal, valueIsKind };

// ============================================================
// HTTP Client
// ============================================================

class HaystackClient {
  private baseUrl: string;
  private project: string;

  constructor(baseUrl: string, project: string) {
    this.baseUrl = baseUrl;
    this.project = project;
  }

  public getUrl(op: string): string {
    return `${this.baseUrl}/${this.project}/${op}`;
  }

  public async get(op: string): Promise<HGrid> {
    const response = await fetch(this.getUrl(op), {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const json = await response.json();
    return this.parseResponse(json);
  }

  public async post(op: string, body?: Record<string, any>): Promise<HGrid> {
    const response = await fetch(this.getUrl(op), {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const json = await response.json();
    return this.parseResponse(json);
  }

  /**
   * Parse JSON response to HGrid
   * Handles both direct grid objects and dict-wrapped grids
   */
  public parseResponse(json: any): HGrid {
    // Handle empty response
    if (!json) {
      return HGrid.make([]);
    }

    // If response is already an HGrid (has rows method)
    if (typeof json === 'object' && 'rows' in json) {
      return HGrid.make(json);
    }

    // If response is a dict (has cols meta), wrap it
    if (typeof json === 'object' && 'cols' in json) {
      return HGrid.make(json);
    }

    // Fallback: treat as dict and create grid from it
    return HGrid.make(json);
  }
}

let clientInstance: HaystackClient | null = null;

export function getClient(): HaystackClient {
  if (!clientInstance) {
    const baseUrl = window.location.origin;
    const apiUrl = new URL(HAYSTACK_BASE_URL, baseUrl);
    // Remove trailing slash for cleaner URL construction
    const apiBase = apiUrl.toString().replace(/\/$/, '');
    clientInstance = new HaystackClient(apiBase, HAYSTACK_PROJECT);
  }
  return clientInstance;
}

export function closeClient(): Promise<void> {
  if (clientInstance) {
    // Just clear the reference, no close method needed
    clientInstance = null;
  }
  return Promise.resolve();
}

// ============================================================
// Haystack API Functions
// ============================================================

export async function readEntities(
  filter: string,
  limit?: number
): Promise<HGrid | null> {
  const client = getClient();
  try {
    // Build filter expression
    let url = `read?filter=${encodeURIComponent(filter)}`;
    if (limit) {
      url += `&limit=${limit}`;
    }
    const response = await fetch(client.getUrl(url), {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const json = await response.json();
    const grid = client.parseResponse(json);
    return grid;
  } catch (error) {
    console.error('Error reading entities:', error);
    return null;
  }
}

export async function evalAxon(expr: string): Promise<HVal> {
  const client = getClient();
  try {
    // Build eval request body
    const body = { expr };
    const response = await fetch(client.getUrl('eval'), {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const json = await response.json();
    const grid = client.parseResponse(json);

    const row = grid.get(0);
    if (row) {
      const val = row.get('val');
      if (val && isHVal(val)) {
        return val;
      }
    }
    return HMarker.make();
  } catch (error) {
    console.error('Error evaluating axon:', error);
    return HStr.make(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

export async function getAbout(): Promise<{
  productName: string;
  productVersion: string;
  vendorName: string;
  serverName: string;
  serverDis: string;
  timezone: string;
}> {
  const client = getClient();
  try {
    const grid = await client.get('about');
    const row = grid.get(0);
    if (!row) {
      throw new Error('About response is empty');
    }
    const getStr = (key: string): string => {
      const val = row.get(key);
      if (val && valueIsKind(val, Kind.Str)) {
        const strVal = val as HStr;
        return strVal.valueOf() as string;
      }
      return 'Unknown';
    };
    return {
      productName: getStr('productName'),
      productVersion: getStr('productVersion'),
      vendorName: getStr('vendorName'),
      serverName: getStr('serverName'),
      serverDis: getStr('serverDis'),
      timezone: getStr('timezone'),
    };
  } catch (error) {
    console.error('Error getting about:', error);
    return {
      productName: 'Demo Mode',
      productVersion: '3.0',
      vendorName: 'AI4Building',
      serverName: 'BA Agent',
      serverDis: 'BA Agent Demo Server',
      timezone: 'UTC',
    };
  }
}

export async function queryNav(navId?: string): Promise<HGrid | null> {
  const client = getClient();
  try {
    let url = 'nav';
    if (navId) {
      url += `?navId=${encodeURIComponent(navId)}`;
    }
    const response = await fetch(client.getUrl(url), {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const json = await response.json();
    return client.parseResponse(json);
  } catch (error) {
    console.error('Error querying nav:', error);
    return null;
  }
}

export async function listOps(): Promise<HGrid | null> {
  const client = getClient();
  try {
    return await client.get('ops');
  } catch (error) {
    console.error('Error listing ops:', error);
    return null;
  }
}

export function getWebSocketUrl(): string {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const apiUrl = new URL(`${HAYSTACK_BASE_URL}/${HAYSTACK_PROJECT}`, window.location.origin);
  return `${wsProtocol}//${apiUrl.host}`;
}

// ============================================================
// Formatting Functions
// ============================================================

export function formatHaystackValue(val: HVal | HGrid): string {
  // Handle HGrid by checking if it has grid-specific methods
  if (valueIsKind(val, Kind.Grid)) {
    return formatGrid(val as HGrid);
  }

  if (valueIsKind(val, Kind.Dict)) {
    return formatDict(val as HDict);
  }
  if (valueIsKind(val, Kind.List)) {
    return formatList(val as HList);
  }
  if (valueIsKind(val, Kind.Str)) {
    return `"${(val as HStr).valueOf()}"`;
  }
  if (valueIsKind(val, Kind.Number)) {
    const numVal = val as HNum;
    const unitVal = numVal.unit;
    const unitStr = unitVal ? ` ${unitVal}` : '';
    return `${numVal.valueOf()}${unitStr}`;
  }
  if (valueIsKind(val, Kind.Bool)) {
    return (val as HBool).valueOf() ? 'true' : 'false';
  }
  if (valueIsKind(val, Kind.Ref)) {
    const refVal = val as HRef;
    const refDis = refVal.dis;
    const refId = refVal.valueOf();
    return refDis ? `@${refDis} <${refId}>` : `@${refId}`;
  }
  if (valueIsKind(val, Kind.Date) || valueIsKind(val, Kind.DateTime)) {
    return (val as HDate | HDateTime).toZinc();
  }
  if (valueIsKind(val, Kind.Symbol)) {
    return `'${(val as HSymbol).valueOf()}'`;
  }
  if (valueIsKind(val, Kind.Uri)) {
    return `<${(val as HUri).valueOf()}>`;
  }
  if (valueIsKind(val, Kind.Marker)) {
    return '⊘';
  }
  if (valueIsKind(val, Kind.NA)) {
    return 'NA';
  }
  // Fallback: use Zinc encoding for unknown types
  return (val as any).toZinc ? (val as any).toZinc() : String(val);
}

function formatGrid(grid: HGrid): string {
  const rowsArray = [...grid];
  const rowCount = rowsArray.length;
  const meta = grid.meta;

  // Get columns
  const cols = getGridCols(grid);
  const colCount = cols.length;

  if (rowCount === 0) {
    return '**Empty Grid**\n\n查询未返回任何记录。';
  }

  let result = '**Grid 数据**\n\n';
  result += `- 行数: ${rowCount}\n`;
  result += `- 列数: ${colCount}\n`;

  if (meta && !meta.isEmpty()) {
    result += '\n**元数据**:\n```\n' + formatDict(meta) + '\n```\n';
  }

  result += '\n**表格预览**:\n```\n' + formatTable(grid) + '\n```\n';

  return result;
}

function getGridCols(grid: HGrid): { name: string }[] {
  const meta = grid.meta;
  if (meta.isEmpty()) return [];

  // Try to get columns from meta
  const colsVal = meta.get('cols');
  if (colsVal && valueIsKind(colsVal, Kind.List)) {
    const colsList = colsVal as HList;
    const cols: { name: string }[] = [];
    for (const item of colsList) {
      if (valueIsKind(item, Kind.Dict)) {
        const itemDict = item as HDict;
        const name = itemDict.get('name');
        if (name && valueIsKind(name, Kind.Str)) {
          const nameStr = name as HStr;
          cols.push({ name: nameStr.valueOf() as string });
        }
      }
    }
    return cols;
  }

  // Fallback: infer columns from first row
  const firstRow = grid.get(0);
  if (firstRow && !firstRow.isEmpty()) {
    const cols: { name: string }[] = [];
    // HValRow has keys property to get column names (not a method)
    const keys = firstRow.keys;
    for (const key of keys) {
      cols.push({ name: key });
    }
    return cols;
  }

  return [];
}

function formatDict(d: HDict): string {
  if (d.isEmpty()) {
    return '{}';
  }

  const maxKeys = 15;
  const entries: [string, HVal][] = [];
  // keys is a property that returns an array
  const keyArray = d.keys;
  for (const key of keyArray) {
    if (entries.length >= maxKeys) break;
    const val = d.get(key);
    if (val && isHVal(val)) {
      entries.push([key, val]);
    }
  }

  const lines: string[] = [];
  for (const [key, val] of entries) {
    lines.push(`"${key}": ${formatHaystackValue(val)}`);
  }

  if (entries.length >= maxKeys && d.keys.length > maxKeys) {
    lines.push('  ...');
  }

  if (lines.length === 0) return '{}';

  return '{' + lines.join(',\n  ') + '\n}';
}

function formatList(list: HList): string {
  if (list.isEmpty()) return '[]';

  const maxItems = 20;
  // Convert HList to array to get items and length
  const items = [...list].slice(0, maxItems);
  const totalCount = [...list].length;

  const formatted = items.map((v) => {
    if (v && isHVal(v)) {
      return formatHaystackValue(v);
    }
    return 'NA';
  }).join(',\n  ');

  if (totalCount <= maxItems) {
    return '[\n  ' + formatted + '\n]';
  }

  return '[\n  ' + formatted + ',\n  // ... ' + (totalCount - maxItems) + ' more items\n]';
}

function formatTable(grid: HGrid): string {
  const maxRows = 50;
  const maxCols = 10;
  const cols = getGridCols(grid).slice(0, maxCols);

  if (cols.length === 0) {
    return '(No columns)';
  }

  // Calculate column widths
  const colWidths = cols.map((c) => {
    let maxWidth = c.name.length;
    for (const row of grid) {
      const val = row.get(c.name);
      if (val && isHVal(val)) {
        const strVal = formatHaystackValue(val);
        maxWidth = Math.max(maxWidth, strVal.length + 2);
      }
    }
    return Math.min(maxWidth, 40);
  });

  // Build separator
  const sep = '+-' + colWidths.map((w) => '-'.repeat(Math.max(w, 3))).join('-+-') + '-+';

  // Build header
  const header = '|' + cols.map((c, i) =>
    ' ' + c.name.padEnd(colWidths[i] - 2) + ' '
  ).join('|') + '|';

  // Build rows
  const lines: string[] = [sep, header, sep];
  let rowCount = 0;
  for (const row of grid) {
    if (rowCount >= maxRows) break;
    rowCount++;

    const cells = cols.map((c, i) => {
      const val = row.get(c.name);
      const formatted = val && isHVal(val) ? formatHaystackValue(val) : '';
      return ' ' + formatted.padEnd(colWidths[i] - 2) + ' ';
    });
    lines.push('|' + cells.join('|') + '|');
  }

  const totalRows = [...grid].length;
  if (totalRows > maxRows) {
    lines.push('| ... ' + (totalRows - maxRows) + ' more rows |');
  }

  lines.push(sep);

  return '\n' + lines.join('\n') + '\n';
}

/**
 * Convert HGrid to table HTML format
 */
export function gridToHTML(grid: HGrid): string {
  const maxRows = 100;
  const cols = getGridCols(grid).slice(0, 20);

  let html = '<table class="haystack-grid">\n';

  // Header
  html += '  <thead><tr>\n';
  for (const col of cols) {
    html += `    <th>${escapeHtml(col.name)}</th>\n`;
  }
  html += '  </tr></thead>\n';

  // Body
  html += '  <tbody>\n';
  let rowCount = 0;
  for (const row of grid) {
    if (rowCount >= maxRows) break;
    rowCount++;

    html += '  <tr>\n';
    for (const col of cols) {
      const val = row.get(col.name);
      const formatted = val && isHVal(val) ? formatHaystackValue(val) : '';
      html += `    <td>${escapeHtml(formatted)}</td>\n`;
    }
    html += '  </tr>\n';
  }

  const totalRows = [...grid].length;
  if (totalRows > maxRows) {
    html += `  <tr><td colspan="${cols.length}">... ${totalRows - maxRows} more rows</td></tr>\n`;
  }

  html += '  </tbody>\n';
  html += '</table>';

  return html;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
