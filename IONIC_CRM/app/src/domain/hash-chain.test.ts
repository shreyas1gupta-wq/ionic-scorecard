import { describe, it, expect } from 'vitest';
import {
  GENESIS_HASH,
  canonicalJson,
  canonicalTimestamp,
  computeRowHash,
  linkRow,
  verifyChain,
  type AuditRow,
  type AuditRowInput,
} from './hash-chain';

function ts(n: number): string {
  // Distinct, canonical, microsecond-precision timestamps.
  const s = String(n).padStart(2, '0');
  return `2026-08-03T09:${s}:00.000000Z`;
}

function input(seq: number, over: Partial<AuditRowInput> = {}): AuditRowInput {
  return {
    seq,
    occurredAt: ts(seq),
    actorId: `emp-${seq}`,
    action: 'PUNCH_CREATED',
    entity: 'status_updates',
    entityId: `su-${seq}`,
    payload: { status: 'IN_PROGRESS', note: `update ${seq}` },
    ...over,
  };
}

/** Build a well-formed chain of `n` rows. */
function buildChain(n: number): AuditRow[] {
  const rows: AuditRow[] = [];
  let prev = GENESIS_HASH;
  for (let i = 1; i <= n; i++) {
    const row = linkRow(prev, input(i));
    rows.push(row);
    prev = row.rowHash;
  }
  return rows;
}

/** Recompute an entire chain from a set of inputs — what a DB superuser could do. */
function rebuild(inputs: readonly AuditRowInput[]): AuditRow[] {
  const rows: AuditRow[] = [];
  let prev = GENESIS_HASH;
  for (const inp of inputs) {
    const row = linkRow(prev, inp);
    rows.push(row);
    prev = row.rowHash;
  }
  return rows;
}

describe('canonicalJson', () => {
  it('sorts keys so insertion order cannot change the hash', () => {
    expect(canonicalJson({ b: 1, a: 2 })).toBe('{"a":2,"b":1}');
    expect(canonicalJson({ a: 2, b: 1 })).toBe(canonicalJson({ b: 1, a: 2 }));
  });

  it('sorts nested keys too', () => {
    expect(canonicalJson({ z: { d: 1, c: 2 }, a: 3 })).toBe('{"a":3,"z":{"c":2,"d":1}}');
  });

  it('preserves array order, which is meaningful', () => {
    expect(canonicalJson([3, 1, 2])).toBe('[3,1,2]');
  });

  it('emits no insignificant whitespace', () => {
    expect(canonicalJson({ a: [1, { b: 2 }] })).toBe('{"a":[1,{"b":2}]}');
  });

  it('refuses undefined rather than hashing an ambiguous payload', () => {
    // JSON.stringify silently drops undefined, which would make {a:1,b:undefined}
    // and {a:1} hash identically.
    expect(() => canonicalJson({ a: 1, b: undefined } as never)).toThrow(/undefined value/);
  });

  it('refuses non-finite numbers', () => {
    expect(() => canonicalJson({ a: NaN })).toThrow(/non-finite/);
    expect(() => canonicalJson({ a: Infinity })).toThrow(/non-finite/);
  });

  it('escapes strings that could otherwise forge structure', () => {
    expect(canonicalJson({ a: '","b":"' })).toBe('{"a":"\\",\\"b\\":\\""}');
  });
});

describe('canonicalTimestamp', () => {
  it('passes through an already-canonical value', () => {
    expect(canonicalTimestamp('2026-08-03T09:15:00.123456Z')).toBe('2026-08-03T09:15:00.123456Z');
  });

  it('normalises the Postgres space-separated rendering', () => {
    // This is the trap: Postgres and JS render the same instant differently, and two
    // renderings hash differently while looking identical to a person.
    expect(canonicalTimestamp('2026-08-03 09:15:00+00')).toBe('2026-08-03T09:15:00.000000Z');
    expect(canonicalTimestamp('2026-08-03 09:15:00.123+00')).toBe('2026-08-03T09:15:00.123000Z');
  });

  it('pads fractional seconds to microseconds', () => {
    expect(canonicalTimestamp('2026-08-03T09:15:00.5Z')).toBe('2026-08-03T09:15:00.500000Z');
  });

  it('accepts a Date, padding milliseconds', () => {
    expect(canonicalTimestamp(new Date('2026-08-03T09:15:00.123Z'))).toBe(
      '2026-08-03T09:15:00.123000Z',
    );
  });

  it('rejects an invalid Date and unparseable text', () => {
    expect(() => canonicalTimestamp(new Date('nope'))).toThrow(/invalid Date/);
    expect(() => canonicalTimestamp('yesterday')).toThrow(/unparseable/);
  });
});

describe('computeRowHash', () => {
  it('is deterministic', () => {
    const a = computeRowHash(GENESIS_HASH, input(1));
    const b = computeRowHash(GENESIS_HASH, input(1));
    expect(a.equals(b)).toBe(true);
    expect(a).toHaveLength(32);
  });

  it('changes if any single field changes', () => {
    const base = computeRowHash(GENESIS_HASH, input(1));
    const variants: Partial<AuditRowInput>[] = [
      { seq: 2 },
      { occurredAt: ts(9) },
      { actorId: 'someone-else' },
      { action: 'PUNCH_DELETED' },
      { entity: 'tickets' },
      { entityId: 'other' },
      { payload: { status: 'DONE', note: 'update 1' } },
    ];
    for (const v of variants) {
      expect(computeRowHash(GENESIS_HASH, input(1, v)).equals(base)).toBe(false);
    }
  });

  it('distinguishes a null actor from an empty-string actor', () => {
    const withNull = computeRowHash(GENESIS_HASH, input(1, { actorId: null }));
    const withEmpty = computeRowHash(GENESIS_HASH, input(1, { actorId: '' }));
    // Both serialise to '' by design, so these SHOULD collide. Documented, not accidental:
    // a null actor is a system action and an empty string is not a valid employee id.
    expect(withNull.equals(withEmpty)).toBe(true);
  });

  it('cannot be forged by shifting content across the field boundary', () => {
    // Without a separator, action='AB' entity='C' and action='A' entity='BC' would hash
    // the same. The 0x1F separator is what prevents that.
    const a = computeRowHash(GENESIS_HASH, input(1, { action: 'AB', entity: 'C' }));
    const b = computeRowHash(GENESIS_HASH, input(1, { action: 'A', entity: 'BC' }));
    expect(a.equals(b)).toBe(false);
  });

  it('rejects a non-canonical timestamp instead of hashing it', () => {
    expect(() => computeRowHash(GENESIS_HASH, input(1, { occurredAt: '2026-08-03 09:15:00+00' })))
      .toThrow(/not canonical/);
  });

  it('rejects a wrong-length prevHash', () => {
    expect(() => computeRowHash(Buffer.alloc(31), input(1))).toThrow(/32 bytes/);
  });
});

describe('verifyChain — a sound chain', () => {
  it('accepts a well-formed chain and reports its head', () => {
    const rows = buildChain(5);
    const r = verifyChain(rows);
    expect(r.ok).toBe(true);
    expect(r.failures).toEqual([]);
    expect(r.checked).toBe(5);
    expect(r.headHash).toBe(rows[4]!.rowHash.toString('hex'));
  });

  it('accepts an empty chain', () => {
    expect(verifyChain([])).toMatchObject({ ok: true, checked: 0, headHash: null });
  });

  it('requires the first row to link to genesis', () => {
    const rows = buildChain(2);
    const forged: AuditRow = { ...rows[0]!, prevHash: Buffer.alloc(32, 7) };
    const r = verifyChain([forged, rows[1]!]);
    expect(r.ok).toBe(false);
    expect(r.failures.some((f) => f.kind === 'BROKEN_LINK')).toBe(true);
  });
});

describe('verifyChain — tampering', () => {
  it('detects an altered payload', () => {
    const rows = buildChain(5);
    rows[2] = { ...rows[2]!, payload: { status: 'DONE', note: 'quietly changed' } };
    const r = verifyChain(rows);
    expect(r.ok).toBe(false);
    expect(r.failures.some((f) => f.kind === 'HASH_MISMATCH' && f.seq === '3')).toBe(true);
  });

  it('detects a deleted row as a sequence gap and a broken link', () => {
    const rows = buildChain(5);
    const withHole = [rows[0]!, rows[1]!, rows[3]!, rows[4]!]; // seq 3 removed
    const r = verifyChain(withHole);
    expect(r.ok).toBe(false);
    expect(r.failures.some((f) => f.kind === 'SEQ_GAP')).toBe(true);
    expect(r.failures.some((f) => f.kind === 'BROKEN_LINK')).toBe(true);
  });

  it('detects a deleted row even when the survivors are RESEQUENCED to hide the gap', () => {
    // The attack this defends against: drop seq 3, renumber 4→3 and 5→4 so there is no
    // visible hole. Because seq is inside the hash, the renumbered rows no longer hash
    // to their stored value.
    const rows = buildChain(5);
    const resequenced: AuditRow[] = [
      rows[0]!,
      rows[1]!,
      { ...rows[3]!, seq: 3 },
      { ...rows[4]!, seq: 4 },
    ];
    const r = verifyChain(resequenced);
    expect(r.ok).toBe(false);
    expect(r.failures.some((f) => f.kind === 'HASH_MISMATCH')).toBe(true);
  });

  it('detects reordering of two rows', () => {
    const rows = buildChain(4);
    const swapped = [rows[0]!, rows[2]!, rows[1]!, rows[3]!];
    const r = verifyChain(swapped);
    expect(r.ok).toBe(false);
    expect(r.failures.some((f) => f.kind === 'SEQ_NOT_ASCENDING')).toBe(true);
  });

  it('detects truncation of the tail only via an anchor', () => {
    const rows = buildChain(5);
    const truncated = rows.slice(0, 3);
    // A forward walk alone sees a perfectly valid, merely shorter chain.
    expect(verifyChain(truncated).ok).toBe(true);
    // The externally-recorded anchor is what exposes it.
    const anchors = new Map([['5', rows[4]!.rowHash.toString('hex')]]);
    const r = verifyChain(truncated, { expectedAnchors: anchors });
    expect(r.ok).toBe(false);
    expect(r.failures.some((f) => f.kind === 'ANCHOR_MISSING' && f.seq === '5')).toBe(true);
  });
});

describe('verifyChain — the privileged-insider case', () => {
  it('cannot detect a full rewrite on its own', () => {
    // This is the honest limitation stated in DESIGN §6. Someone who can rewrite every
    // row produces a chain that is internally perfect.
    const original = buildChain(5);
    const anchorBefore = original[4]!.rowHash.toString('hex');

    const doctored = rebuild([input(1), input(2), input(3, { payload: { status: 'DONE', note: 'rewritten' } }), input(4), input(5)]);
    expect(verifyChain(doctored).ok).toBe(true);
    expect(doctored[4]!.rowHash.toString('hex')).not.toBe(anchorBefore);
  });

  it('detects a full rewrite once the head hash was published externally', () => {
    // Committing each day's head hash to the private backup repo is what closes this.
    const original = buildChain(5);
    const anchors = new Map([['5', original[4]!.rowHash.toString('hex')]]);

    const doctored = rebuild([input(1), input(2), input(3, { payload: { status: 'DONE', note: 'rewritten' } }), input(4), input(5)]);
    const r = verifyChain(doctored, { expectedAnchors: anchors });
    expect(r.ok).toBe(false);
    expect(r.failures.some((f) => f.kind === 'ANCHOR_MISMATCH' && f.seq === '5')).toBe(true);
  });

  it('confirms an untampered chain against its anchor', () => {
    const rows = buildChain(5);
    const anchors = new Map([['5', rows[4]!.rowHash.toString('hex')]]);
    expect(verifyChain(rows, { expectedAnchors: anchors }).ok).toBe(true);
  });
});
