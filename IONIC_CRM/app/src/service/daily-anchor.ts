/**
 * The daily anchor job.
 *
 * Runs once a day (a Cloudflare cron trigger in production — `wrangler.toml`
 * already declares it). It does two things, and the SECOND is the one that
 * matters:
 *
 *   1. Record today's audit-chain head hash in the anchors file.
 *   2. Verify the ENTIRE current chain against EVERY anchor recorded on previous
 *      days.
 *
 * Only step 2 can catch a rewrite. Step 1 alone would merely accumulate numbers
 * nobody ever compares — the audit equivalent of taking backups and never
 * restoring one. A superuser who rewrote the log last night produces a chain that
 * is internally flawless (proved in `hash-chain.test.ts`); it fails only when
 * measured against a hash written down before the rewrite happened.
 *
 * WHY VERIFICATION LIVES HERE AND NOT ON THE REPOSITORY: `AuditStore.verify()`
 * checks internal consistency, which is all a store can know. Comparing against
 * externally-held anchors is the anchor job's concern — the repository has no
 * business knowing that a file on disk exists.
 *
 * THE CALLER MUST BIND AN ADMIN ACTOR. Reading the audit log is admin-only by
 * policy, and correctly so: a job running as a lesser actor would silently see an
 * empty chain and cheerfully anchor a hash of nothing. `runDailyAnchor` therefore
 * refuses to record an anchor when the log looks empty but the anchors file says
 * it should not be — see `EMPTY_BUT_EXPECTED` below.
 */

import { Buffer } from 'node:buffer';
import {
  GENESIS_HASH_HEX,
  anchorsToExpectedMap,
  type AnchorRecord,
} from '../domain/anchor';
import { verifyChain, type AuditRow } from '../domain/hash-chain';
import { istDateOf, type IsoDate } from '../domain/calendar';
import { appendAnchor, readAnchorFile } from './anchor-file';
import type { AuditRecord, Repository } from '../repo/types';

/**
 * How many audit rows to pull for verification.
 *
 * The chain must be walked from the beginning — verification is meaningless on a
 * suffix, because the point is that every row links to its predecessor. This is a
 * ceiling to stop the job trying to load an unbounded table into memory rather
 * than a window: exceeding it is reported as a problem, not silently truncated,
 * because silently verifying a suffix would look exactly like success.
 */
export const MAX_CHAIN_ROWS = 200_000;

export class AnchorJobError extends Error {
  override readonly name = 'AnchorJobError';
}

export interface DailyAnchorResult {
  readonly date: IsoDate;
  readonly seq: number;
  readonly headHashHex: string;
  /** Internal consistency AND agreement with every prior anchor. */
  readonly chainOk: boolean;
  readonly rowsChecked: number;
  readonly anchorsCompared: number;
  readonly appended: boolean;
  readonly skippedReason?: string;
  /** Human-readable, ready for a log line or an alert. Empty when all is well. */
  readonly problems: readonly string[];
}

/** Rehydrate the hash-chain shape from what the repository hands back. */
function toAuditRow(r: AuditRecord): AuditRow {
  return {
    seq: r.seq,
    occurredAt: r.occurredAt,
    actorId: r.actorId,
    action: r.action,
    entity: r.entity,
    entityId: r.entityId,
    payload: r.payload as AuditRow['payload'],
    prevHash: Buffer.from(r.prevHashHex, 'hex'),
    rowHash: Buffer.from(r.rowHashHex, 'hex'),
  };
}

export async function runDailyAnchor(
  repo: Repository,
  anchorsPath: string,
  now: Date = new Date(),
): Promise<DailyAnchorResult> {
  const date = istDateOf(now);
  const problems: string[] = [];

  // Prior anchors first: they are the reference the chain is measured against,
  // and reading them may itself reveal a problem worth stopping for.
  const file = await readAnchorFile(anchorsPath);
  const expectedAnchors = anchorsToExpectedMap(file.anchors);
  for (const p of file.problems) {
    problems.push(`anchors file: ${p.kind}${'seq' in p ? ` (seq ${p.seq})` : ''}`);
  }

  // Newest-first from the store; the chain must be walked in seq order.
  const newestFirst = await repo.audit.list(MAX_CHAIN_ROWS);
  const rows = [...newestFirst].reverse().map(toAuditRow);

  if (rows.length >= MAX_CHAIN_ROWS) {
    // Reported, never silently accepted: verifying a suffix of the chain proves
    // nothing but looks identical to success.
    problems.push(
      `chain exceeds MAX_CHAIN_ROWS (${MAX_CHAIN_ROWS}); verification would cover only a suffix ` +
        `and is therefore not trustworthy. Archive or raise the ceiling deliberately.`,
    );
  }

  /**
   * The admin-actor trap.
   *
   * `audit.list` returns nothing both when the log is genuinely empty and when
   * the caller is not an admin. Anchoring the genesis hash in the second case
   * would quietly replace a real head with a hash of nothing, and the anchors
   * file would then disagree with itself forever.
   */
  if (rows.length === 0 && file.latest !== null && file.latest.seq > 0) {
    throw new AnchorJobError(
      `the audit log reads as empty, but the anchors file records seq ${file.latest.seq} on ` +
        `${file.latest.date}. Either the log was destroyed, or this job is not running as an ` +
        `ADMIN actor and is seeing nothing. Refusing to anchor a hash of nothing.`,
    );
  }

  const verification = verifyChain(rows, { expectedAnchors });
  for (const f of verification.failures) {
    problems.push(`chain: ${f.kind}${'seq' in f ? ` (seq ${f.seq})` : ''}`);
  }

  const seq = rows.length === 0 ? 0 : Number(rows[rows.length - 1]!.seq);
  const headHashHex = verification.headHash ?? GENESIS_HASH_HEX;
  const chainOk = verification.ok;

  const record: AnchorRecord = { date, seq, headHashHex, chainOk };

  // Recorded even when the chain is broken: "the chain was broken on this date"
  // is evidence, and suppressing it would be the worst possible response.
  // `appendAnchor` refuses if the file already holds a contradiction — that
  // refusal is deliberate and propagates.
  const append = await appendAnchor(anchorsPath, record);

  return {
    date,
    seq,
    headHashHex,
    chainOk,
    rowsChecked: verification.checked,
    anchorsCompared: expectedAnchors.size,
    appended: append.appended,
    ...(append.reason !== undefined ? { skippedReason: append.reason } : {}),
    problems,
  };
}
