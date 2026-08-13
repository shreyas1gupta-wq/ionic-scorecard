import { describe, it, expect } from 'vitest';
import {
  ANCHOR_FORMAT,
  GENESIS_HASH_HEX,
  anchorsToExpectedMap,
  formatAnchorLine,
  inspectAnchors,
  parseAnchorLine,
  parseAnchorsFile,
  renderAnchorsFile,
  type AnchorRecord,
} from './anchor';
import { GENESIS_HASH, linkRow, verifyChain, type AuditRow } from './hash-chain';

/** A distinct 64-char lower-case hex hash for fixture n. */
const H = (n: number): string => n.toString(16).padStart(2, '0').repeat(32);
/** Contains letters, so case-sensitivity can actually be tested. */
const HASH_WITH_LETTERS = 'ab'.repeat(32);

function anchor(over: Partial<AnchorRecord> = {}): AnchorRecord {
  return { date: '2026-08-03', seq: 10, headHashHex: H(1), chainOk: true, ...over };
}

describe('formatAnchorLine', () => {
  it('produces a dull, greppable, fixed-arity line', () => {
    expect(formatAnchorLine(anchor())).toBe(`${ANCHOR_FORMAT} 2026-08-03 10 ${H(1)} ok`);
  });

  it('marks a broken chain unmistakably', () => {
    expect(formatAnchorLine(anchor({ chainOk: false }))).toMatch(/ BROKEN$/);
  });

  it('accepts seq 0 for an empty chain', () => {
    expect(formatAnchorLine(anchor({ seq: 0, headHashHex: GENESIS_HASH_HEX }))).toContain(' 0 ');
  });

  it.each([
    ['a bad date', { date: '03-08-2026' }, /YYYY-MM-DD/],
    ['a negative seq', { seq: -1 }, /non-negative/],
    ['a fractional seq', { seq: 1.5 }, /non-negative integer/],
    ['a short hash', { headHashHex: 'abc' }, /64 lower-case hex/],
    ['an upper-case hash', { headHashHex: HASH_WITH_LETTERS.toUpperCase() }, /64 lower-case hex/],
  ])('refuses %s rather than writing it', (_label, over, pattern) => {
    expect(() => formatAnchorLine(anchor(over))).toThrow(pattern);
  });
});

describe('parseAnchorLine', () => {
  it('round-trips', () => {
    const a = anchor({ seq: 4321, headHashHex: H(7) });
    expect(parseAnchorLine(formatAnchorLine(a))).toEqual(a);
  });

  it('ignores blanks and comments', () => {
    expect(parseAnchorLine('')).toBeNull();
    expect(parseAnchorLine('   ')).toBeNull();
    expect(parseAnchorLine('# a note')).toBeNull();
  });

  it('tolerates extra surrounding whitespace', () => {
    expect(parseAnchorLine(`  ${formatAnchorLine(anchor())}  `)).toEqual(anchor());
  });

  it('refuses an unknown format version rather than guessing', () => {
    // Silently misreading an older format would produce anchors that never match
    // and send someone chasing a rewrite that never happened.
    expect(() => parseAnchorLine(`anchor/2 2026-08-03 10 ${H(1)} ok`)).toThrow(/unknown anchor format/);
  });

  it.each([
    [`${ANCHOR_FORMAT} 2026-08-03 10 ${H(1)}`, /expected 5 fields/],
    [`${ANCHOR_FORMAT} 2026-08-03 10 ${H(1)} ok extra`, /expected 5 fields/],
    [`${ANCHOR_FORMAT} 03-08-2026 10 ${H(1)} ok`, /bad anchor date/],
    [`${ANCHOR_FORMAT} 2026-08-03 ten ${H(1)} ok`, /bad anchor seq/],
    [`${ANCHOR_FORMAT} 2026-08-03 10 nothex ok`, /bad anchor hash/],
    [`${ANCHOR_FORMAT} 2026-08-03 10 ${H(1)} maybe`, /bad anchor status/],
  ])('refuses malformed line %j', (line, pattern) => {
    expect(() => parseAnchorLine(line)).toThrow(pattern);
  });
});

describe('parseAnchorsFile', () => {
  it('reads a rendered file back', () => {
    const anchors = [
      anchor({ date: '2026-08-01', seq: 5, headHashHex: H(1) }),
      anchor({ date: '2026-08-02', seq: 9, headHashHex: H(2) }),
    ];
    expect(parseAnchorsFile(renderAnchorsFile(anchors))).toEqual(anchors);
  });

  it('handles CRLF line endings', () => {
    const text = `# note\r\n${formatAnchorLine(anchor())}\r\n`;
    expect(parseAnchorsFile(text)).toEqual([anchor()]);
  });

  it('reports the line number, because this file gets read under pressure', () => {
    const text = ['# header', formatAnchorLine(anchor()), 'garbage here'].join('\n');
    expect(() => parseAnchorsFile(text)).toThrow(/line 3/);
  });

  it('returns nothing for a header-only file', () => {
    expect(parseAnchorsFile(renderAnchorsFile([]))).toEqual([]);
  });
});

describe('anchorsToExpectedMap', () => {
  it('maps seq to hash for verifyChain', () => {
    const map = anchorsToExpectedMap([anchor({ seq: 7, headHashHex: H(3) })]);
    expect(map.get('7')).toBe(H(3));
  });

  it('excludes anchors taken while the chain was already broken', () => {
    // Feeding a known-bad state back in as expected truth would launder the
    // original problem into "everything matches".
    const map = anchorsToExpectedMap([anchor({ seq: 7, chainOk: false })]);
    expect(map.size).toBe(0);
  });

  it('excludes seq 0, since an empty chain has no row to pin', () => {
    expect(anchorsToExpectedMap([anchor({ seq: 0, headHashHex: GENESIS_HASH_HEX })]).size).toBe(0);
  });
});

describe('inspectAnchors — the anchors file is checked too', () => {
  it('accepts a well-formed sequence', () => {
    expect(
      inspectAnchors([
        anchor({ date: '2026-08-01', seq: 3, headHashHex: H(1) }),
        anchor({ date: '2026-08-02', seq: 8, headHashHex: H(2) }),
      ]),
    ).toEqual([]);
  });

  it('accepts a repeated seq when the hash agrees — a quiet day', () => {
    // Nothing happened, so the head did not move. Not a problem.
    expect(
      inspectAnchors([
        anchor({ date: '2026-08-01', seq: 8, headHashHex: H(2) }),
        anchor({ date: '2026-08-02', seq: 8, headHashHex: H(2) }),
      ]),
    ).toEqual([]);
  });

  it('flags two different hashes for the same seq — the strongest signal available', () => {
    // Either the audit log was rewritten between runs, or the anchors file was
    // tampered with. This must never pass silently.
    const problems = inspectAnchors([
      anchor({ date: '2026-08-01', seq: 8, headHashHex: H(2) }),
      anchor({ date: '2026-08-02', seq: 8, headHashHex: H(9) }),
    ]);
    expect(problems).toHaveLength(1);
    expect(problems[0]).toMatchObject({ kind: 'HASH_CHANGED_FOR_SEQ', seq: 8 });
  });

  it('flags a seq that went backwards', () => {
    const problems = inspectAnchors([
      anchor({ date: '2026-08-01', seq: 9, headHashHex: H(2) }),
      anchor({ date: '2026-08-02', seq: 4, headHashHex: H(3) }),
    ]);
    expect(problems.some((p) => p.kind === 'SEQ_WENT_BACKWARDS')).toBe(true);
  });

  it('flags a date that went backwards', () => {
    const problems = inspectAnchors([
      anchor({ date: '2026-08-05', seq: 4, headHashHex: H(2) }),
      anchor({ date: '2026-08-02', seq: 9, headHashHex: H(3) }),
    ]);
    expect(problems.some((p) => p.kind === 'DATE_WENT_BACKWARDS')).toBe(true);
  });

  it('surfaces a day the chain was recorded broken', () => {
    const problems = inspectAnchors([anchor({ chainOk: false })]);
    expect(problems.some((p) => p.kind === 'CHAIN_WAS_BROKEN')).toBe(true);
  });
});

/**
 * The property the whole audit design rests on, end to end.
 *
 * hash-chain.test.ts proves the chain alone cannot detect a full rewrite. These
 * tests prove the anchors file closes that gap — which is the only reason the
 * anchors file exists.
 */
describe('anchors close the privileged-insider gap', () => {
  function chainOf(notes: readonly string[]): AuditRow[] {
    const rows: AuditRow[] = [];
    let prev = GENESIS_HASH;
    notes.forEach((note, i) => {
      const row = linkRow(prev, {
        seq: i + 1,
        occurredAt: `2026-08-03T09:0${i}:00.000000Z`,
        actorId: 'emp-1',
        action: 'PUNCH_CREATED',
        entity: 'status_updates',
        entityId: `su-${i + 1}`,
        payload: { note },
      });
      rows.push(row);
      prev = row.rowHash;
    });
    return rows;
  }

  it('confirms an untampered chain against its recorded anchor', () => {
    const rows = chainOf(['one', 'two', 'three']);
    const anchors = [
      anchor({ date: '2026-08-03', seq: 3, headHashHex: rows[2]!.rowHash.toString('hex') }),
    ];
    const result = verifyChain(rows, { expectedAnchors: anchorsToExpectedMap(anchors) });
    expect(result.failures).toEqual([]);
    expect(result.ok).toBe(true);
  });

  it('catches a full rewrite that the chain alone accepts', () => {
    const original = chainOf(['one', 'two', 'three']);
    const anchors = [
      anchor({ date: '2026-08-03', seq: 3, headHashHex: original[2]!.rowHash.toString('hex') }),
    ];

    // A superuser rewrites history: row 2 altered, every later hash recomputed.
    const doctored = chainOf(['one', 'rewritten', 'three']);
    // Internally flawless...
    expect(verifyChain(doctored).ok).toBe(true);
    // ...and caught the moment it is measured against the external record.
    const checked = verifyChain(doctored, { expectedAnchors: anchorsToExpectedMap(anchors) });
    expect(checked.ok).toBe(false);
    expect(checked.failures.some((f) => f.kind === 'ANCHOR_MISMATCH')).toBe(true);
  });

  it('catches truncation of the most recent entries', () => {
    const rows = chainOf(['one', 'two', 'three']);
    const anchors = [
      anchor({ date: '2026-08-03', seq: 3, headHashHex: rows[2]!.rowHash.toString('hex') }),
    ];
    const truncated = rows.slice(0, 2);
    expect(verifyChain(truncated).ok).toBe(true);
    const checked = verifyChain(truncated, { expectedAnchors: anchorsToExpectedMap(anchors) });
    expect(checked.failures.some((f) => f.kind === 'ANCHOR_MISSING')).toBe(true);
  });

  it('produces an anchor whose head hash matches what the chain reports', () => {
    const rows = chainOf(['one', 'two']);
    const verified = verifyChain(rows);
    const line = formatAnchorLine({
      date: '2026-08-03',
      seq: 2,
      headHashHex: verified.headHash!,
      chainOk: verified.ok,
    });
    expect(parseAnchorLine(line)).toEqual({
      date: '2026-08-03',
      seq: 2,
      headHashHex: rows[1]!.rowHash.toString('hex'),
      chainOk: true,
    });
  });
});
