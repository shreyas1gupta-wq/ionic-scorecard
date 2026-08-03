#!/usr/bin/env node
/**
 * Run the test suites as separate, sequential processes.
 *
 * WHY THIS SCRIPT EXISTS, because it looks like pointless indirection otherwise:
 *
 * Each database-backed suite loads a whole Postgres compiled to WebAssembly.
 * PGlite reserves a large contiguous memory region, and on Windows that counts
 * against the system COMMIT CHARGE rather than only physical RAM — which is the
 * detail that made this confusing to diagnose. The development machine showed
 * 3.5 GB of free RAM but only 1.8 GB of free commit, so two suites back-to-back
 * failed while each passed alone.
 *
 * The failure surfaces as `Fatal process out of memory: Zone` followed by
 * `ERR_IPC_CHANNEL_CLOSED`, neither of which reads as "the OS has not finished
 * releasing the last process's commit yet".
 *
 * So: one suite per process, and a short gap between them so the OS can reclaim.
 * `npm run test:all` runs everything in a single process instead — faster, and
 * fine on a machine with room.
 */

import { spawn } from 'node:child_process';
import { setTimeout as delay } from 'node:timers/promises';

/** Ordered cheapest-first, so a broken build fails fast. */
const SUITES = [
  { name: 'unit (domain + auth)', args: ['src/domain', 'src/auth'] },
  { name: 'database schema', args: ['src/db'] },
  { name: 'repository contract', args: ['src/repo'] },
  { name: 'service rules', args: ['src/service'] },
];

/** Long enough for Windows to release commit charge; short enough not to annoy. */
const GAP_MS = 1500;

/**
 * Run a suite, capturing output as well as streaming it.
 *
 * The capture exists to tell two very different outcomes apart: a test that
 * failed, and a suite that could not start because the machine ran out of memory.
 * Both exit non-zero, and conflating them sends you looking for a bug that is not
 * there.
 */
function runSuite(args) {
  return new Promise((resolve) => {
    const child = spawn('npx', ['vitest', 'run', ...args], {
      stdio: ['inherit', 'pipe', 'pipe'],
      shell: process.platform === 'win32',
    });
    let text = '';
    for (const stream of [child.stdout, child.stderr]) {
      stream?.on('data', (chunk) => {
        const s = String(chunk);
        text += s;
        process.stdout.write(s);
      });
    }
    child.on('close', (code) => resolve({ code: code ?? 1, text }));
  });
}

const OOM = /out of memory|ERR_IPC_CHANNEL_CLOSED|Channel closed/i;

const failures = [];
const exhausted = [];

for (const [i, suite] of SUITES.entries()) {
  process.stdout.write(`\n=== ${suite.name} ===\n`);
  const { code, text } = await runSuite(suite.args);
  if (code !== 0) {
    if (OOM.test(text)) exhausted.push(suite.name);
    else failures.push(suite.name);
  }
  if (i < SUITES.length - 1) await delay(GAP_MS);
}

if (exhausted.length > 0) {
  process.stdout.write(
    `\n${'='.repeat(72)}\n` +
      `COULD NOT RUN (out of memory, not a test failure): ${exhausted.join(', ')}\n\n` +
      `These suites each load a full Postgres compiled to WebAssembly. On Windows that\n` +
      `reservation counts against COMMIT CHARGE, not just free RAM, so a machine can\n` +
      `show gigabytes free and still refuse. Close other memory-heavy applications and\n` +
      `re-run, or run the suites individually:\n` +
      `    npm run test:db  ·  npm run test:repo  ·  npm run test:service\n` +
      `${'='.repeat(72)}\n`,
  );
}
if (failures.length > 0) {
  process.stdout.write(`\nFAILED: ${failures.join(', ')}\n`);
}
if (exhausted.length > 0 || failures.length > 0) process.exit(1);

process.stdout.write('\nAll suites passed.\n');
