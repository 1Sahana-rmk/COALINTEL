import { DocumentTableItem, ExtractedMetricItem } from '@/types/document';

export interface PersistedTableMerge {
  startRow: number;
  startColumn: number;
  endRow: number;
  endColumn: number;
}

/**
 * Convert persisted table values for display without replacing structural
 * blanks with user-facing placeholder text.
 */
export function displayPersistedTableValue(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function tablesForPage(tables: DocumentTableItem[], pageNumber: number): DocumentTableItem[] {
  return tables.filter((table) => table.page_number === pageNumber);
}

export function structuredRows(table: DocumentTableItem): unknown[][] {
  if (!Array.isArray(table.rows)) return [];
  return table.rows.filter((row): row is unknown[] => Array.isArray(row));
}

export function tableColumnCount(table: DocumentTableItem): number {
  const headerCount = Array.isArray(table.headers) ? table.headers.length : 0;
  return Math.max(headerCount, ...structuredRows(table).map((row) => row.length), 0);
}

export function hasReliableStructuredTable(table: DocumentTableItem): boolean {
  const headers = Array.isArray(table.headers) ? table.headers : [];
  return tableColumnCount(table) > 0 && (headers.length > 0 || structuredRows(table).length > 0);
}

export function reliableTables(tables: DocumentTableItem[]): DocumentTableItem[] {
  return tables.filter(hasReliableStructuredTable);
}

export function tableDataRowCount(tables: DocumentTableItem[]): number {
  return tables.reduce((count, table) => count + structuredRows(table).length, 0);
}

export function tableColumnNames(tables: DocumentTableItem[]): string[] {
  const names: string[] = [];
  for (const table of tables) {
    for (const header of Array.isArray(table.headers) ? table.headers : []) {
      const name = header === null || header === undefined ? '' : String(header).trim();
      if (name && !names.includes(name)) names.push(name);
    }
  }
  return names;
}

function excelColumnNumber(value: string): number | null {
  let result = 0;
  for (const character of value.toUpperCase()) {
    const code = character.charCodeAt(0) - 64;
    if (code < 1 || code > 26) return null;
    result = result * 26 + code;
  }
  return result || null;
}

function parseCellReference(value: string): { row: number; column: number } | null {
  const match = value.trim().match(/^\$?([A-Z]+)\$?(\d+)$/i);
  if (!match) return null;
  const column = excelColumnNumber(match[1]);
  const row = Number(match[2]);
  return column && Number.isSafeInteger(row) && row >= 1 ? { row, column } : null;
}

export function persistedTableMerges(table: DocumentTableItem): PersistedTableMerge[] {
  if (!Array.isArray(table.merged_cells)) return [];
  const merges: PersistedTableMerge[] = [];
  for (const entry of table.merged_cells) {
    if (typeof entry === 'string') {
      const parts = entry.split(':');
      if (parts.length !== 2) continue;
      const start = parseCellReference(parts[0]);
      const end = parseCellReference(parts[1]);
      if (start && end && end.row >= start.row && end.column >= start.column) {
        merges.push({ startRow: start.row, startColumn: start.column, endRow: end.row, endColumn: end.column });
      }
      continue;
    }
    if (!entry || typeof entry !== 'object') continue;
    const record = entry as Record<string, unknown>;
    const startRow = Number(record.start_row ?? record.startRow ?? record.row ?? record.row_index);
    const startColumn = Number(record.start_column ?? record.startColumn ?? record.column ?? record.column_index);
    const rowSpan = Number(record.row_span ?? record.rowSpan ?? 1);
    const columnSpan = Number(record.column_span ?? record.colSpan ?? record.columnSpan ?? 1);
    if ([startRow, startColumn, rowSpan, columnSpan].every(Number.isSafeInteger) && startRow >= 1 && startColumn >= 1 && rowSpan >= 1 && columnSpan >= 1) {
      merges.push({ startRow, startColumn, endRow: startRow + rowSpan - 1, endColumn: startColumn + columnSpan - 1 });
    }
  }
  return merges;
}

export function buildPageContentSummary(tables: DocumentTableItem[]): string {
  const structured = reliableTables(tables);
  if (structured.length === 0) return '';

  const titled = structured
    .map((table) => table.title?.trim())
    .filter((title): title is string => Boolean(title));
  const titleText = titled.length > 0
    ? `${titled.map((title) => `“${title}”`).join(', ')}${structured.length === 1 ? ' table' : ' tables'}`
    : `${structured.length} persisted structured table${structured.length === 1 ? '' : 's'}`;
  const rowCount = tableDataRowCount(structured);
  const columns = tableColumnNames(structured);
  const rowText = `${rowCount} data row${rowCount === 1 ? '' : 's'}`;
  const columnText = columns.length > 0 ? ` with columns for ${columns.join(', ')}` : '';
  return `This page contains ${titleText}. It contains ${rowText}${columnText}.`;
}

export function metricForEvidence(
  metrics: ExtractedMetricItem[],
  evidenceLocator: string | null,
): ExtractedMetricItem | null {
  if (!evidenceLocator || !/^\d+$/.test(evidenceLocator)) return null;
  const metricId = Number(evidenceLocator);
  if (!Number.isSafeInteger(metricId)) return null;
  return metrics.find((metric) => metric.id === metricId) || null;
}
