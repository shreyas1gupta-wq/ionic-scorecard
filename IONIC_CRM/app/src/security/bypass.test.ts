/**
 * The workers.dev back door — a config-file assertion, not an end-to-end proof.
 *
 * DESIGN.md §2.2 calls `workers_dev = false` "the single most important line in
 * this file" (wrangler.toml's own header comment says the same thing): a
 * Cloudflare Worker is reachable at `<name>.<subdomain>.workers.dev` unless that
 * route is explicitly disabled, and that URL does not pass through Cloudflare
 * Access — it bypasses the entire authentication layer, JWT verification
 * included, because nothing about the Worker's own code runs any differently
 * when reached that way.
 *
 * WHAT THIS TEST PROVES: the `wrangler.toml` in this repository, read from
 * disk, contains an active (non-commented) `workers_dev = false` line and no
 * active `workers_dev = true` anywhere.
 *
 * WHAT THIS TEST DOES NOT PROVE, AND CANNOT, FROM HERE:
 *   - That this is the `wrangler.toml` actually used by the last deployment.
 *   - That nothing in the Cloudflare dashboard overrides it (dashboard-set
 *     values can diverge from the repo's config file).
 *   - That the setting has "taken" against the real edge — i.e. that a request
 *     to the real `*.workers.dev` hostname actually returns a non-200.
 *
 * That end-to-end check is DESIGN.md §9, check 4, and it requires a live
 * Cloudflare account and a real deployed Worker — neither of which exists in
 * this sandbox. It remains outstanding. Do not read a pass here as evidence
 * that check 4 has been done; it has not.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const wranglerPath = resolve(here, '../../wrangler.toml');

function readWrangler(): string {
  return readFileSync(wranglerPath, 'utf8');
}

function activeLines(toml: string): string[] {
  return toml
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !line.startsWith('#'));
}

describe('workers.dev bypass — config-level check only (see file header)', () => {
  it('sets workers_dev = false as an active, uncommented line', () => {
    const lines = activeLines(readWrangler()).filter((line) => line.startsWith('workers_dev'));
    expect(lines).toHaveLength(1);
    expect(lines[0]).toBe('workers_dev = false');
  });

  it('never sets workers_dev = true anywhere in the file, active or commented', () => {
    // Deliberately checks the raw file, not just active lines: a commented-out
    // `workers_dev = true` left over from "quickly testing something" — the
    // exact temptation wrangler.toml's own header comment warns against — is a
    // landmine for whoever next uncomments the wrong line without reading the
    // warning above it.
    expect(readWrangler()).not.toMatch(/workers_dev\s*=\s*true/);
  });

  it('does not have workers_dev configured more than once', () => {
    // Two active assignments to the same key would make "which one wins"
    // depend on wrangler's parsing order rather than on anything visible here.
    const lines = activeLines(readWrangler()).filter((line) => line.startsWith('workers_dev'));
    expect(lines.length).toBe(1);
  });
});
