/**
 * Tamper-evident audit chain.
 *
 * Each row's hash covers the previous row's hash, so altering or removing any historical
 * row breaks every hash after it. This gives us the one property git-as-a-database would
 * have given us, without git's fatal flaw (undeletable personal data — see DESIGN §1).
 *
 * WHAT THIS DETECTS ON ITS OWN: any edit, deletion or reordering by someone who cannot
 * recompute the whole chain — which is everyone except a database superuser.
 *
 * WHAT IT DOES NOT DETECT ON ITS OWN: a privileged insider who deletes a row and rewrites
 * every subsequent hash. That is what `expectedAnchors` is for. Publishing each day's
 * final hash somewhere outside the database (we commit it to the private backup repo)
 * means a full rewrite still has to match a number recorded elsewhere, and cannot.
 *
 * Chain verification without anchors proves internal consistency. Only anchors prove
 * the history is the one that actually happened.
 */

import { createHash } from 'node:crypto';

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | readonly JsonValue[]
  | { readonly [k: string]: JsonValue };

/** Field separator. 0x1F (ASCII unit separator) cannot occur in any hashed field. */
const SEP = Buffer.from([0x1f]);

/** The chain's origin. 32 zero bytes — the `prev_hash` of the very first row. */
export const GENESIS_HASH: Buffer = Buffer.alloc(32, 0);

export interface AuditRowInput {
  /**
   * A plain number, not a bigint.
   *
   * Postgres `bigserial` can exceed `Number.MAX_SAFE_INTEGER` in principle, and an
   * earlier version used `bigint` for that reason. It was changed for two
   * reasons, the second one forced:
   *
   *   1. Nine quadrillion audit entries is not a scenario for a fifty-person
   *      ticket tool. The precision was theoretical.
   *   2. Next's file tracer (`@vercel/nft`, used by the webpack build and by the
   *      Cloudflare adapter) statically evaluates expressions and **crashes** on
   *      mixed bigint arithmetic: `TypeError: Cannot mix BigInt and other types`.
   *      That made the app impossible to package for deployment at all.
   *
   * The hash is unaffected: it serialises `String(seq)`, which is identical for a
   * number and a bigint holding the same integer, so chains written before this
   * change still verify.
   */
  readonly seq: number;
  /**
   * Canonical ISO-8601 UTC with exactly 6 fractional digits: `2026-08-03T09:15:00.123456Z`.
   *
   * Deliberately a string, not a Date: Postgres `timestamptz` has microsecond precision
   * and a JS `Date` has only milliseconds, so round-tripping through `Date` would silently
   * discard bits that are inside the hash. Use `canonicalTimestamp()` at the boundary.
   */
  readonly occurredAt: string;
  readonly actorId: string | null;
  readonly action: string;
  readonly entity: string;
  readonly entityId: string | null;
  readonly payload: JsonValue;
}

export interface AuditRow extends AuditRowInput {
  readonly prevHash: Buffer;
  readonly rowHash: Buffer;
}

const CANONICAL_TS_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$/;

/**
 * Normalise a timestamp into the exact form the hash requires.
 *
 * This exists because a mismatch here is the most likely way to break verification
 * without breaking anything visible: Postgres may hand back `2026-08-03 09:15:00+00`
 * while application code produces `...T09:15:00.000Z`, and those hash differently
 * while looking identical to a human.
 */
export function canonicalTimestamp(input: string | Date): string {
  if (input instanceof Date) {
    if (Number.isNaN(input.getTime())) throw new Error('invalid Date');
    // Milliseconds padded to microseconds. A Date genuinely has no more precision;
    // this is lossless for values that came from a Date in the first place.
    return input.toISOString().replace(/\.(\d{3})Z$/, '.$1000Z');
  }
  if (CANONICAL_TS_RE.test(input)) return input;

  // Accept the common Postgres and ISO renderings, then re-emit canonically.
  const m = /^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?(?:Z|\+00(?::?00)?)?$/.exec(
    input.trim(),
  );
  if (!m) throw new Error(`unparseable timestamp: ${JSON.stringify(input)}`);
  const date = m[1]!;
  const time = m[2]!;
  const frac = m[3] ?? '';
  return `${date}T${time}.${frac.padEnd(6, '0')}Z`;
}

/**
 * Deterministic JSON: keys sorted at every depth, no insignificant whitespace.
 *
 * `JSON.stringify` alone is not safe here — it preserves insertion order, so the same
 * logical payload built two different ways would hash differently.
 */
export function canonicalJson(v: JsonValue): string {
  if (v === null) return 'null';
  const t = typeof v;
  if (t === 'string') return JSON.stringify(v);
  if (t === 'boolean') return v ? 'true' : 'false';
  if (t === 'number') {
    if (!Number.isFinite(v as number)) {
      throw new Error(`non-finite number in audit payload: ${String(v)}`);
    }
    return JSON.stringify(v);
  }
  if (Array.isArray(v)) {
    return `[${v.map(canonicalJson).join(',')}]`;
  }
  const obj = v as { readonly [k: string]: JsonValue };
  const keys = Object.keys(obj).sort();
  const parts: string[] = [];
  for (const k of keys) {
    const val = obj[k];
    if (val === undefined) {
      // `undefined` would be dropped by JSON.stringify, making two different payloads
      // hash the same. Refuse it rather than hash something ambiguous.
      throw new Error(`undefined value at audit payload key ${JSON.stringify(k)}`);
    }
    parts.push(`${JSON.stringify(k)}:${canonicalJson(val)}`);
  }
  return `{${parts.join(',')}}`;
}

/** The hash of one row, given its predecessor's hash. Exactly DESIGN §6. */
export function computeRowHash(prevHash: Buffer, row: AuditRowInput): Buffer {
  if (prevHash.length !== 32) {
    throw new Error(`prevHash must be 32 bytes, got ${prevHash.length}`);
  }
  if (!CANONICAL_TS_RE.test(row.occurredAt)) {
    throw new Error(
      `occurredAt is not canonical (use canonicalTimestamp): ${JSON.stringify(row.occurredAt)}`,
    );
  }
  const h = createHash('sha256');
  h.update(prevHash);
  for (const field of [
    String(row.seq),
    row.occurredAt,
    row.actorId ?? '',
    row.action,
    row.entity,
    row.entityId ?? '',
    canonicalJson(row.payload),
  ]) {
    h.update(SEP);
    h.update(field, 'utf8');
  }
  return h.digest();
}

/** Append a row to a chain, returning the row with its linkage filled in. */
export function linkRow(prevHash: Buffer, input: AuditRowInput): AuditRow {
  return { ...input, prevHash, rowHash: computeRowHash(prevHash, input) };
}

export type ChainFailure =
  | { readonly kind: 'SEQ_GAP'; readonly at: number; readonly expected: string; readonly found: string }
  | { readonly kind: 'SEQ_NOT_ASCENDING'; readonly at: number; readonly found: string }
  | { readonly kind: 'BROKEN_LINK'; readonly at: number; readonly seq: string }
  | { readonly kind: 'HASH_MISMATCH'; readonly at: number; readonly seq: string }
  | { readonly kind: 'ANCHOR_MISMATCH'; readonly seq: string; readonly expected: string; readonly found: string }
  | { readonly kind: 'ANCHOR_MISSING'; readonly seq: string };

export interface VerifyOptions {
  /**
   * Independently-recorded root hashes, keyed by the `seq` they were taken at
   * (hex-encoded). These are what make a full-chain rewrite detectable.
   */
  readonly expectedAnchors?: ReadonlyMap<string, string>;
  /** Require `seq` to be strictly consecutive. Default true. */
  readonly requireConsecutive?: boolean;
}

export interface VerifyResult {
  readonly ok: boolean;
  readonly checked: number;
  readonly failures: readonly ChainFailure[];
  /** Final row hash, hex. This is the value to publish as the day's anchor. */
  readonly headHash: string | null;
}

/**
 * Walk a chain in `seq` order and recompute every hash.
 *
 * Note why a deletion cannot be hidden by renumbering: `seq` is itself inside the
 * hash. Removing row 5 and shifting 6→5 changes what row 5's hash must be, so the
 * recomputation diverges — you would have to rewrite every row after it, which is
 * what `expectedAnchors` then catches.
 */
export function verifyChain(rows: readonly AuditRow[], opts: VerifyOptions = {}): VerifyResult {
  const requireConsecutive = opts.requireConsecutive ?? true;
  const failures: ChainFailure[] = [];
  let prev = GENESIS_HASH;
  let prevSeq: number | null = null;
  let head: string | null = null;

  for (let i = 0; i < rows.length; i++) {
    const row = rows[i]!;
    const seq = Number(row.seq);

    if (prevSeq !== null) {
      if (seq <= prevSeq) {
        failures.push({ kind: 'SEQ_NOT_ASCENDING', at: i, found: String(seq) });
      } else if (requireConsecutive && seq !== prevSeq + 1) {
        failures.push({
          kind: 'SEQ_GAP',
          at: i,
          expected: String(prevSeq + 1),
          found: String(seq),
        });
      }
    }

    if (!row.prevHash.equals(prev)) {
      failures.push({ kind: 'BROKEN_LINK', at: i, seq: seq.toString() });
    }

    // Recompute from the row's OWN stored prevHash, so a broken link and a bad payload
    // are reported as the two distinct problems they are.
    const expected = computeRowHash(row.prevHash, row);
    if (!expected.equals(row.rowHash)) {
      failures.push({ kind: 'HASH_MISMATCH', at: i, seq: seq.toString() });
    }

    const anchor = opts.expectedAnchors?.get(seq.toString());
    if (anchor !== undefined && anchor !== row.rowHash.toString('hex')) {
      failures.push({
        kind: 'ANCHOR_MISMATCH',
        seq: seq.toString(),
        expected: anchor,
        found: row.rowHash.toString('hex'),
      });
    }

    prev = row.rowHash;
    prevSeq = seq;
    head = row.rowHash.toString('hex');
  }

  // An anchor whose row is absent means rows were truncated from the end — which a
  // forward walk alone would report as a perfectly valid, merely shorter, chain.
  if (opts.expectedAnchors) {
    const present = new Set(rows.map((r) => String(Number(r.seq))));
    for (const seq of opts.expectedAnchors.keys()) {
      if (!present.has(seq)) failures.push({ kind: 'ANCHOR_MISSING', seq });
    }
  }

  return { ok: failures.length === 0, checked: rows.length, failures, headHash: head };
}
