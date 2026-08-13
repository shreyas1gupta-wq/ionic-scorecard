/**
 * Human-facing ticket references: `TKT-2026-0001`.
 *
 * The reference is per-year sequential and NEVER reused, including for cancelled or
 * deleted-by-mistake tickets. People quote these in email and in conversation, and a
 * reused reference means two different pieces of work answer to the same name.
 *
 * The authoritative counter lives in the database (a per-year sequence), not here.
 * This module only formats and parses.
 */

export const TICKET_REF_RE = /^TKT-(\d{4})-(\d{4,})$/;

export function formatTicketRef(year: number, sequence: number): string {
  if (!Number.isInteger(year) || year < 2000 || year > 9999) {
    throw new Error(`implausible year: ${year}`);
  }
  if (!Number.isInteger(sequence) || sequence < 1) {
    throw new Error(`sequence must be a positive integer, got ${sequence}`);
  }
  // Pads to 4 digits but does not truncate: the 10,000th ticket of a year becomes
  // TKT-2026-10000 rather than silently colliding with an earlier one.
  return `TKT-${year}-${String(sequence).padStart(4, '0')}`;
}

export interface ParsedTicketRef {
  readonly year: number;
  readonly sequence: number;
}

export function parseTicketRef(ref: string): ParsedTicketRef | null {
  const m = TICKET_REF_RE.exec(ref.trim().toUpperCase());
  if (!m) return null;
  return { year: Number(m[1]!), sequence: Number(m[2]!) };
}
