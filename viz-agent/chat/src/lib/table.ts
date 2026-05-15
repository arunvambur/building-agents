export interface TablePayload {
  headers: string[];
  rows: string[][];
  row_count: number;
}

export function parseTableContent(content: string): TablePayload | null {
  const stripped = stripJsonFence(stripTablePrefix(content));

  try {
    return normalizeTablePayload(JSON.parse(stripped));
  } catch {
    return null;
  }
}

function stripTablePrefix(content: string): string {
  const trimmed = content.trim();
  return trimmed.startsWith("table://") ? trimmed.slice("table://".length) : trimmed;
}

function stripJsonFence(content: string): string {
  const trimmed = content.trim();
  if (!trimmed.startsWith("```")) return trimmed;

  const lines = trimmed.split("\n");
  if (lines.length < 2) return trimmed;
  const body = lines[lines.length - 1].trim() === "```"
    ? lines.slice(1, -1)
    : lines.slice(1);
  return body.join("\n").trim();
}

function normalizeTablePayload(payload: unknown): TablePayload | null {
  if (Array.isArray(payload)) {
    if (!payload.length || !payload.every(isRecord)) return null;
    return recordsToTable(payload);
  }

  if (!isRecord(payload)) return null;

  if (Array.isArray(payload.headers) && Array.isArray(payload.rows)) {
    return rowsToTable(payload.headers, payload.rows, payload.count ?? payload.row_count);
  }

  const headers = Array.isArray(payload.columns)
    ? payload.columns
    : Array.isArray(payload.headers)
      ? payload.headers
      : null;
  const data = Array.isArray(payload.data)
    ? payload.data
    : headers && Array.isArray(payload.rows)
      ? payload.rows
    : Array.isArray(payload.records)
      ? payload.records
      : Array.isArray(payload.results)
        ? payload.results
        : null;

  if (headers && data) {
    return rowsToTable(headers, data, payload.row_count);
  }

  if (Array.isArray(payload.rows) && payload.rows.length && payload.rows.every(isRecord)) {
    const inferredHeaders = headers ?? Object.keys(payload.rows[0]);
    return rowsToTable(inferredHeaders, payload.rows, payload.row_count);
  }

  return null;
}

function recordsToTable(records: Record<string, unknown>[]): TablePayload {
  const headers = Object.keys(records[0]);
  const rows = records.map((record) => headers.map((header) => stringifyCell(record[header])));
  return { headers, rows, row_count: records.length };
}

function rowsToTable(
  headers: unknown[],
  rows: unknown[],
  rowCount: unknown,
): TablePayload | null {
  const normalizedHeaders = headers.map(stringifyCell);
  if (!normalizedHeaders.length) return null;

  const normalizedRows: string[][] = [];
  for (const row of rows) {
    if (Array.isArray(row)) {
      normalizedRows.push(row.map(stringifyCell));
      continue;
    }
    if (isRecord(row)) {
      normalizedRows.push(normalizedHeaders.map((header) => stringifyCell(row[header])));
      continue;
    }
    return null;
  }

  return {
    headers: normalizedHeaders,
    rows: normalizedRows,
    row_count: typeof rowCount === "number" ? rowCount : normalizedRows.length,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringifyCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value);
}
