/**
 * Tests against a real filesystem, in a temp directory.
 *
 * Deliberately not mocked. The properties under test are "it appends rather than
 * rewrites" and "it refuses to write over evidence" — both of which are claims
 * about what ends up on disk, and a mocked `fs` would let either of them be false
 * while the tests stayed green.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { appendAnchor, AnchorFileError, readAnchorFile } from './anchor-file';
import { formatAnchorLine, type AnchorRecord } from '../domain/anchor';

const H = (n: number): string => n.toString(16).padStart(2, '0').repeat(32);

function anchor(over: Partial<AnchorRecord> = {}): AnchorRecord {
  return { date: '2026-08-03', seq: 10, headHashHex: H(1), chainOk: true, ...over };
}

let dir: string;
let path: string;

beforeEach(async () => {
  dir = await mkdtemp(join(tmpdir(), 'ionic-anchor-'));
  path = join(dir, 'nested', 'anchors.txt');
});

afterEach(async () => {
  await rm(dir, { recursive: true, force: true });
});

describe('readAnchorFile', () => {
  it('reports a missing file without throwing', async () => {
    const s = await readAnchorFile(path);
    expect(s).toMatchObject({ exists: false, anchors: [], latest: null });
  });

  it('throws with a line number on an unparseable file', async () => {
    // An unparseable root of trust is a stop-everything condition.
    await appendAnchor(path, anchor());
    await writeFile(path, (await readFile(path, 'utf8')) + 'garbage\n', 'utf8');
    await expect(readAnchorFile(path)).rejects.toThrow(/line \d+/);
  });
});

describe('appendAnchor — creating the file', () => {
  it('creates missing directories and writes the header', async () => {
    const r = await appendAnchor(path, anchor());
    expect(r.appended).toBe(true);
    const text = await readFile(path, 'utf8');
    expect(text).toContain('# Ionic CRM — audit chain anchors');
    expect(text).toContain('append-only');
    expect(text.trimEnd().endsWith(formatAnchorLine(anchor()))).toBe(true);
  });

  it('round-trips through readAnchorFile', async () => {
    await appendAnchor(path, anchor());
    const s = await readAnchorFile(path);
    expect(s.exists).toBe(true);
    expect(s.anchors).toEqual([anchor()]);
    expect(s.latest).toEqual(anchor());
  });
});

describe('appendAnchor — appending, never rewriting', () => {
  it('keeps every earlier line intact', async () => {
    await appendAnchor(path, anchor({ date: '2026-08-01', seq: 5, headHashHex: H(1) }));
    await appendAnchor(path, anchor({ date: '2026-08-02', seq: 9, headHashHex: H(2) }));
    await appendAnchor(path, anchor({ date: '2026-08-03', seq: 14, headHashHex: H(3) }));

    const s = await readAnchorFile(path);
    expect(s.anchors.map((a) => a.seq)).toEqual([5, 9, 14]);
    expect(s.anchors.map((a) => a.headHashHex)).toEqual([H(1), H(2), H(3)]);
    expect(s.problems).toEqual([]);
  });

  it('repairs a missing trailing newline instead of fusing two records', async () => {
    await appendAnchor(path, anchor({ seq: 5, headHashHex: H(1) }));
    const text = await readFile(path, 'utf8');
    await writeFile(path, text.replace(/\n+$/, ''), 'utf8');

    await appendAnchor(path, anchor({ date: '2026-08-04', seq: 6, headHashHex: H(2) }));
    const s = await readAnchorFile(path);
    expect(s.anchors.map((a) => a.seq)).toEqual([5, 6]);
  });
});

describe('appendAnchor — idempotence, because scheduled jobs get retried', () => {
  it('is a no-op when the identical anchor is already recorded', async () => {
    await appendAnchor(path, anchor());
    const again = await appendAnchor(path, anchor());
    expect(again.appended).toBe(false);
    expect(again.reason).toMatch(/already recorded/);
    expect((await readAnchorFile(path)).anchors).toHaveLength(1);
  });

  it('records a new day for the same seq when nothing moved', async () => {
    // A quiet day: the head did not move, but the anchor run still happened and
    // recording it is evidence the check was performed.
    await appendAnchor(path, anchor({ date: '2026-08-03', seq: 10 }));
    const r = await appendAnchor(path, anchor({ date: '2026-08-04', seq: 10 }));
    expect(r.appended).toBe(true);
    const s = await readAnchorFile(path);
    expect(s.anchors.map((a) => a.date)).toEqual(['2026-08-03', '2026-08-04']);
    expect(s.problems).toEqual([]);
  });
});

describe('appendAnchor — refusing to write over evidence', () => {
  it('refuses a different hash for a seq already recorded', async () => {
    // The strongest signal the system can produce: the audit log was rewritten,
    // or the anchors file was altered.
    await appendAnchor(path, anchor({ seq: 10, headHashHex: H(1) }));
    const err = await appendAnchor(path, anchor({ date: '2026-08-04', seq: 10, headHashHex: H(9) }))
      .then(() => null, (e: unknown) => e as AnchorFileError);

    expect(err).toBeInstanceOf(AnchorFileError);
    expect(err!.message).toMatch(/CHAIN MISMATCH/);
    expect(err!.message).toMatch(/escalate/);
    expect(err!.problems[0]).toMatchObject({ kind: 'HASH_CHANGED_FOR_SEQ', seq: 10 });
    // And nothing was written.
    expect((await readAnchorFile(path)).anchors).toHaveLength(1);
  });

  it('refuses to append over a file that already records a problem', async () => {
    // Appending a valid-looking line on top would bury the evidence.
    await appendAnchor(path, anchor({ date: '2026-08-01', seq: 9, headHashHex: H(2) }));
    // Hand-corrupt the file the way a tamperer would: a contradictory line.
    await writeFile(
      path,
      (await readFile(path, 'utf8')) +
        formatAnchorLine(anchor({ date: '2026-08-02', seq: 9, headHashHex: H(7) })) +
        '\n',
      'utf8',
    );

    const err = await appendAnchor(path, anchor({ date: '2026-08-03', seq: 20, headHashHex: H(3) }))
      .then(() => null, (e: unknown) => e as AnchorFileError);
    expect(err).toBeInstanceOf(AnchorFileError);
    expect(err!.message).toMatch(/bury the evidence/);
    expect(err!.problems.length).toBeGreaterThan(0);
  });

  it('refuses a seq behind the last recorded one — the log cannot shrink', async () => {
    await appendAnchor(path, anchor({ date: '2026-08-03', seq: 20, headHashHex: H(1) }));
    await expect(
      appendAnchor(path, anchor({ date: '2026-08-04', seq: 12, headHashHex: H(2) })),
    ).rejects.toThrow(/cannot shrink/);
  });

  it('records a broken chain rather than refusing to write it', async () => {
    // The anchor must capture "the chain was broken on this date" — that is
    // evidence, and suppressing it would be the worst possible response.
    const r = await appendAnchor(path, anchor({ chainOk: false }));
    expect(r.appended).toBe(true);
    const text = await readFile(path, 'utf8');
    expect(text).toMatch(/ BROKEN$/m);
  });

  it('then refuses further appends once a broken anchor is on record', async () => {
    await appendAnchor(path, anchor({ seq: 10, chainOk: false }));
    await expect(
      appendAnchor(path, anchor({ date: '2026-08-04', seq: 11, headHashHex: H(4) })),
    ).rejects.toThrow(/Investigate before writing anything further/);
  });
});
