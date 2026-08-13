/**
 * Reading and appending the anchors file.
 *
 * The anchors file is the audit chain's root of trust (see `domain/anchor.ts` for
 * why). This module is the only thing that writes it, and it is deliberately
 * paranoid in three specific ways:
 *
 *   1. IT ONLY EVER APPENDS. There is no update and no delete, because the value
 *      of the file is that yesterday's number cannot change. A function that
 *      could rewrite a line would eventually be called.
 *   2. IT REFUSES TO APPEND OVER A CORRUPT FILE. Appending to something already
 *      unparseable would bury the evidence under a valid-looking new line.
 *   3. IT REFUSES TO CONTRADICT ITSELF. If the file already records a different
 *      head hash for the same seq, that is the strongest signal this system can
 *      produce — either the audit log was rewritten or the file was tampered
 *      with — and it must stop, loudly, rather than quietly add a second answer.
 *
 * The DB read that produces the anchor lives outside this module, so the file
 * behaviour is testable without a database.
 */

import { appendFile, mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname } from 'node:path';
import {
  ANCHORS_FILE_HEADER,
  formatAnchorLine,
  inspectAnchors,
  parseAnchorsFile,
  type AnchorFileProblem,
  type AnchorRecord,
} from '../domain/anchor';

export class AnchorFileError extends Error {
  override readonly name = 'AnchorFileError';
  constructor(
    message: string,
    readonly problems: readonly AnchorFileProblem[] = [],
  ) {
    super(message);
  }
}

async function readIfExists(path: string): Promise<string | null> {
  try {
    return await readFile(path, 'utf8');
  } catch (err) {
    if ((err as { code?: string }).code === 'ENOENT') return null;
    throw err;
  }
}

export interface AnchorFileState {
  readonly exists: boolean;
  readonly anchors: readonly AnchorRecord[];
  readonly problems: readonly AnchorFileProblem[];
  /** The most recent anchor, or null for an empty/absent file. */
  readonly latest: AnchorRecord | null;
}

/** Read and validate. Throws only if the file is unparseable, not if it records a problem. */
export async function readAnchorFile(path: string): Promise<AnchorFileState> {
  const contents = await readIfExists(path);
  if (contents === null) {
    return { exists: false, anchors: [], problems: [], latest: null };
  }
  // A parse failure throws with a line number: an unparseable root of trust is a
  // stop-everything condition, not something to work around.
  const anchors = parseAnchorsFile(contents);
  return {
    exists: true,
    anchors,
    problems: inspectAnchors(anchors),
    latest: anchors.length > 0 ? anchors[anchors.length - 1]! : null,
  };
}

export interface AppendResult {
  readonly appended: boolean;
  /** Set when the append was skipped because the identical record already exists. */
  readonly reason?: string;
  readonly state: AnchorFileState;
}

/**
 * Append one anchor.
 *
 * Idempotent: re-running today's anchor when nothing has changed is a no-op
 * rather than a duplicate line. That matters because this runs from a scheduled
 * job, and scheduled jobs get retried.
 */
export async function appendAnchor(path: string, record: AnchorRecord): Promise<AppendResult> {
  const before = await readAnchorFile(path);

  if (before.problems.length > 0) {
    throw new AnchorFileError(
      `refusing to append: the anchors file already records ${before.problems.length} problem(s). ` +
        `Investigate before writing anything further — appending now would bury the evidence ` +
        `under a valid-looking line.`,
      before.problems,
    );
  }

  const existing = before.anchors.find((a) => a.seq === record.seq);
  if (existing !== undefined) {
    if (existing.headHashHex !== record.headHashHex) {
      throw new AnchorFileError(
        `CHAIN MISMATCH: the anchors file records head hash ${existing.headHashHex} for seq ` +
          `${record.seq} (dated ${existing.date}), but the audit log now reports ` +
          `${record.headHashHex}. Either the audit log was rewritten or the anchors file was ` +
          `altered. Do not proceed; escalate.`,
        [
          {
            kind: 'HASH_CHANGED_FOR_SEQ',
            seq: record.seq,
            first: existing.headHashHex,
            then: record.headHashHex,
          },
        ],
      );
    }
    if (existing.date === record.date && existing.chainOk === record.chainOk) {
      return { appended: false, reason: 'identical anchor already recorded', state: before };
    }
  }

  if (before.latest !== null && record.seq < before.latest.seq) {
    throw new AnchorFileError(
      `refusing to append: seq ${record.seq} is behind the last recorded anchor ` +
        `(${before.latest.seq} on ${before.latest.date}). The audit log cannot shrink.`,
    );
  }

  const line = formatAnchorLine(record);

  if (!before.exists) {
    await mkdir(dirname(path), { recursive: true });
    await writeFile(path, [...ANCHORS_FILE_HEADER, line, ''].join('\n'), 'utf8');
  } else {
    // Append, never rewrite. If the file somehow lacks a trailing newline, add one
    // first so the new record does not fuse onto the previous line.
    const contents = await readFile(path, 'utf8');
    const prefix = contents.length > 0 && !contents.endsWith('\n') ? '\n' : '';
    await appendFile(path, `${prefix}${line}\n`, 'utf8');
  }

  return { appended: true, state: await readAnchorFile(path) };
}
