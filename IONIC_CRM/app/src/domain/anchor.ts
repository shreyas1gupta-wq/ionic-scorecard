/**
 * External anchors for the audit chain.
 *
 * WHY THIS FILE IS THE POINT OF THE WHOLE AUDIT DESIGN:
 *
 * The hash chain in `hash-chain.ts` detects any edit, deletion or reordering by
 * someone who cannot recompute the whole chain — which is everyone except a
 * database superuser. Against a superuser it proves nothing on its own: they can
 * delete a row and rewrite every hash after it, and the result is internally
 * perfect. `hash-chain.test.ts` proves that limitation rather than hiding it.
 *
 * An anchor closes it. Each day the chain's head hash is written somewhere the
 * database cannot reach — here, a plain-text file committed to the private backup
 * repository. A full rewrite now has to match a number recorded outside the
 * system, and cannot.
 *
 * So the anchors file is the actual root of trust. Two consequences follow, and
 * both are design constraints rather than preferences:
 *
 *   1. It must be append-only in practice. Git gives that: history is immutable,
 *      and a force-push to hide an anchor is itself visible.
 *   2. The format must be dull, line-oriented and human-readable. Someone will
 *      one day need to read it during an incident, possibly without this codebase
 *      to hand, and a binary or JSON-blob format would be actively hostile then.
 */

import { GENESIS_HASH } from './hash-chain';
import type { IsoDate } from './calendar';

/** One day's anchor: the chain head as it stood when the anchor was taken. */
export interface AnchorRecord {
  /** The IST date the anchor covers. */
  readonly date: IsoDate;
  /** The audit_log seq the head hash belongs to. 0 means an empty chain. */
  readonly seq: number;
  /** Hex, 64 chars. The genesis value for an empty chain. */
  readonly headHashHex: string;
  /** Whether full-chain verification passed when the anchor was taken. */
  readonly chainOk: boolean;
}

const FIELD_SEP = ' ';
const HEX64 = /^[0-9a-f]{64}$/;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export const GENESIS_HASH_HEX: string = GENESIS_HASH.toString('hex');

/** Version prefix, so a future format change is detectable rather than silent. */
export const ANCHOR_FORMAT = 'anchor/1';

export const ANCHORS_FILE_HEADER: readonly string[] = [
  '# Ionic CRM — audit chain anchors',
  '#',
  '# One line per day, append-only. Each line records the audit chain head hash as',
  '# it stood at that date. These values live OUTSIDE the database on purpose: they',
  '# are what makes a full rewrite of the audit log detectable. Never edit or remove',
  '# a line. If a line is wrong, append a new one and explain it in the commit.',
  '#',
  `# Format: ${ANCHOR_FORMAT} <date> <seq> <head-hash-hex> <ok|BROKEN>`,
];

/**
 * One line, terminated by the caller.
 *
 * Space-separated and fixed-arity so `grep`, `awk` and a human eye all work on it
 * during an incident.
 */
export function formatAnchorLine(a: AnchorRecord): string {
  if (!ISO_DATE.test(a.date)) throw new Error(`anchor date must be YYYY-MM-DD, got ${a.date}`);
  if (!Number.isInteger(a.seq) || a.seq < 0) {
    throw new Error(`anchor seq must be a non-negative integer, got ${a.seq}`);
  }
  if (!HEX64.test(a.headHashHex)) {
    throw new Error(`anchor head hash must be 64 lower-case hex chars, got ${a.headHashHex}`);
  }
  return [ANCHOR_FORMAT, a.date, String(a.seq), a.headHashHex, a.chainOk ? 'ok' : 'BROKEN'].join(
    FIELD_SEP,
  );
}

/** Parse one line. Returns null for blanks and comments; throws on a malformed record. */
export function parseAnchorLine(line: string): AnchorRecord | null {
  const trimmed = line.trim();
  if (trimmed.length === 0 || trimmed.startsWith('#')) return null;

  const parts = trimmed.split(/\s+/);
  if (parts.length !== 5) {
    throw new Error(`malformed anchor line (expected 5 fields, got ${parts.length}): ${trimmed}`);
  }
  const [format, date, seq, hash, status] = parts as [string, string, string, string, string];

  if (format !== ANCHOR_FORMAT) {
    // Refused rather than guessed: silently misreading an older format would
    // produce anchors that never match and an investigation chasing a ghost.
    throw new Error(`unknown anchor format ${format}, expected ${ANCHOR_FORMAT}`);
  }
  if (!ISO_DATE.test(date)) throw new Error(`bad anchor date: ${date}`);
  if (!/^\d+$/.test(seq)) throw new Error(`bad anchor seq: ${seq}`);
  if (!HEX64.test(hash)) throw new Error(`bad anchor hash: ${hash}`);
  if (status !== 'ok' && status !== 'BROKEN') throw new Error(`bad anchor status: ${status}`);

  return { date, seq: Number(seq), headHashHex: hash, chainOk: status === 'ok' };
}

export function parseAnchorsFile(contents: string): AnchorRecord[] {
  const out: AnchorRecord[] = [];
  const lines = contents.split(/\r?\n/);
  for (const [i, line] of lines.entries()) {
    try {
      const record = parseAnchorLine(line);
      if (record !== null) out.push(record);
    } catch (err) {
      // Line number included because an anchors file is read under pressure.
      throw new Error(`anchors file line ${i + 1}: ${(err as Error).message}`);
    }
  }
  return out;
}

/**
 * Anchors in the shape `verifyChain` expects: seq (as a string) to hex hash.
 *
 * Only `ok` anchors are returned. An anchor recorded while the chain was already
 * broken is evidence about that day, not a trustworthy reference point, and
 * feeding it back in as expected truth would launder the original problem.
 */
export function anchorsToExpectedMap(anchors: readonly AnchorRecord[]): Map<string, string> {
  const map = new Map<string, string>();
  for (const a of anchors) {
    if (!a.chainOk) continue;
    // seq 0 is an empty chain: there is no row to pin, so nothing to check.
    if (a.seq === 0) continue;
    map.set(String(a.seq), a.headHashHex);
  }
  return map;
}

export type AnchorFileProblem =
  | { readonly kind: 'SEQ_WENT_BACKWARDS'; readonly at: number; readonly prev: number; readonly found: number }
  | { readonly kind: 'DATE_WENT_BACKWARDS'; readonly at: number; readonly prev: IsoDate; readonly found: IsoDate }
  | { readonly kind: 'HASH_CHANGED_FOR_SEQ'; readonly seq: number; readonly first: string; readonly then: string }
  | { readonly kind: 'CHAIN_WAS_BROKEN'; readonly date: IsoDate; readonly seq: number };

/**
 * Sanity-check the anchors file itself.
 *
 * The anchors are the root of trust, so they get checked too. The important case
 * is `HASH_CHANGED_FOR_SEQ`: two anchors claiming different head hashes for the
 * same seq means either the audit log was rewritten between two anchor runs, or
 * the anchors file was tampered with. Either way it is the strongest signal this
 * system can produce, and it must never pass silently.
 */
export function inspectAnchors(anchors: readonly AnchorRecord[]): AnchorFileProblem[] {
  const problems: AnchorFileProblem[] = [];
  const seenSeq = new Map<number, string>();
  let prevSeq: number | null = null;
  let prevDate: IsoDate | null = null;

  for (const [i, a] of anchors.entries()) {
    if (prevSeq !== null && a.seq < prevSeq) {
      problems.push({ kind: 'SEQ_WENT_BACKWARDS', at: i, prev: prevSeq, found: a.seq });
    }
    if (prevDate !== null && a.date < prevDate) {
      problems.push({ kind: 'DATE_WENT_BACKWARDS', at: i, prev: prevDate, found: a.date });
    }
    const already = seenSeq.get(a.seq);
    if (already !== undefined && already !== a.headHashHex) {
      problems.push({ kind: 'HASH_CHANGED_FOR_SEQ', seq: a.seq, first: already, then: a.headHashHex });
    } else if (already === undefined) {
      seenSeq.set(a.seq, a.headHashHex);
    }
    if (!a.chainOk) {
      problems.push({ kind: 'CHAIN_WAS_BROKEN', date: a.date, seq: a.seq });
    }
    prevSeq = a.seq;
    prevDate = a.date;
  }
  return problems;
}

/** Render a fresh anchors file, header included. Used on first run. */
export function renderAnchorsFile(anchors: readonly AnchorRecord[]): string {
  return [...ANCHORS_FILE_HEADER, ...anchors.map(formatAnchorLine), ''].join('\n');
}
