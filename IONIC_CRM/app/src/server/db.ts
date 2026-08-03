/**
 * The server's repository factory.
 *
 * TWO MODES.
 *
 *   development — the in-memory repository. Starts instantly, uses almost no RAM,
 *           and is safe to build UI against because `src/repo/contract.test.ts`
 *           runs one suite of rules against both it and a real Postgres. If the
 *           two ever diverge, that suite fails.
 *
 *   production  — Postgres over Supabase's session-mode pooler (`pg-client.ts`).
 *
 * NO PGLITE MODE HERE, DELIBERATELY. An earlier version offered a
 * `CRM_DEV_STORE=pglite` mode that ran a Postgres compiled to WebAssembly inside
 * the dev server. It was removed for two reasons, the second decisive:
 *
 *   1. It needed roughly a gigabyte of spare RAM, which this machine does not
 *      reliably have — it exhausted V8's allocator outright.
 *   2. Next.js traces dynamic imports, so merely *mentioning* PGlite in this file
 *      pulled the entire WASM Postgres into the production Worker bundle. The
 *      Cloudflare Workers free plan caps a Worker at 3 MiB compressed; a test
 *      database has no business being deployed at all, let alone spending that
 *      budget.
 *
 * PGlite still runs every migration and every RLS policy — in the TEST suite,
 * which is where it belongs. `npm run test:db` and `npm run test:repo` are what
 * verify a policy change.
 *
 * THE HONEST LIMITATION: the in-memory store enforces the authorisation rules in
 * TypeScript, so it cannot catch a mistake in an RLS policy. Only the test suite
 * can. Change a policy → run the tests.
 */

import { createMemoryRepository } from '../repo/memory';
import { createPostgresRepository } from '../repo/postgres';
import { createPgClient } from './pg-client';
import type { RepositoryFactory } from '../repo/types';

export class NotConfiguredError extends Error {
  override readonly name = 'NotConfiguredError';
}

/** The development team. */
const DEV_TEAM = [
  { workEmail: 'admin@ionic.in', displayName: 'Admin User', role: 'ADMIN' as const },
  { workEmail: 'manager@ionic.in', displayName: 'Priya Manager', role: 'MANAGER' as const },
  {
    workEmail: 'alice@ionic.in',
    displayName: 'Alice Analyst',
    role: 'EMPLOYEE' as const,
    managerEmail: 'manager@ionic.in',
  },
  {
    workEmail: 'bob@ionic.in',
    displayName: 'Bob Associate',
    role: 'EMPLOYEE' as const,
    managerEmail: 'manager@ionic.in',
  },
];

const DEV_HOLIDAYS: [string, string][] = [
  ['2026-08-15', 'Independence Day'],
  ['2026-10-02', 'Gandhi Jayanti'],
  ['2026-11-09', 'Diwali'],
  ['2026-12-25', 'Christmas'],
];

const DEV_CATEGORIES = ['Operations', 'Client Reporting', 'Compliance', 'Research'];

/**
 * Cached on globalThis, not in a module variable.
 *
 * Next.js reloads modules on every edit in development; a module-level singleton
 * would build a fresh store per reload and leak databases until the process died.
 */
interface Cache {
  factory?: Promise<RepositoryFactory>;
}
const globalCache = globalThis as unknown as { __ionicCrmDb?: Cache };
globalCache.__ionicCrmDb ??= {};
const cache = globalCache.__ionicCrmDb;

async function createMemoryDevFactory(): Promise<RepositoryFactory> {
  const factory = createMemoryRepository({
    employees: DEV_TEAM,
    holidays: DEV_HOLIDAYS.map(([d]) => d),
    categories: DEV_CATEGORIES,
  });

  const alice = factory.idByEmail('alice@ionic.in');
  const bob = factory.idByEmail('bob@ionic.in');
  const manager = factory.idByEmail('manager@ionic.in');

  /**
   * Seed data chosen to exercise the states that are easy to get wrong: a healthy
   * ticket, one that is overdue, one that is stale (in flight but silent), and one
   * never touched since it was raised. A seed where everything looks fine hides
   * exactly the bugs these views exist to surface.
   */
  await factory.withActor({ employeeId: manager }, async (repo) => {
    const pack = await repo.tickets.create({
      title: 'Prepare the August client reporting pack',
      description: 'Standard monthly pack. Deadline is the 5th working day.',
      priority: 'P2',
      assigneeId: alice,
      raiserId: manager,
      deadline: '2026-08-07',
    });
    await repo.tickets.create({
      title: 'Reconcile the quarterly fee schedule',
      priority: 'P1',
      assigneeId: alice,
      raiserId: manager,
      // Deliberately in the past, so the overdue path renders.
      deadline: '2026-07-31',
    });
    const stale = await repo.tickets.create({
      title: 'Chase the custodian for the missing trade file',
      priority: 'P1',
      assigneeId: bob,
      raiserId: manager,
      deadline: '2026-08-20',
    });
    await repo.tickets.create({
      title: 'Refresh the compliance training tracker',
      priority: 'P3',
      assigneeId: bob,
      raiserId: manager,
      deadline: '2026-09-15',
    });

    // Two tickets moved to IN_PROGRESS with punches, because only IN_PROGRESS and
    // BLOCKED can go stale — an untouched OPEN ticket is a scheduling problem, not
    // a reporting-discipline one. `stale` was last touched long enough ago that a
    // P1 trips its one-working-day window; `pack` was updated today and should not.
    await repo.tickets.addPunch({
      ticketId: pack.id,
      actorId: manager,
      punchDate: '2026-08-03',
      status: 'IN_PROGRESS',
      note: 'Drafting. Waiting on the custodian file for the holdings table.',
    });
    await repo.tickets.setStatus({ ticketId: pack.id, status: 'IN_PROGRESS' });

    await repo.tickets.addPunch({
      ticketId: stale.id,
      actorId: manager,
      punchDate: '2026-07-24',
      status: 'IN_PROGRESS',
      note: 'First chase sent to the custodian.',
    });
    await repo.tickets.setStatus({ ticketId: stale.id, status: 'IN_PROGRESS' });
  });

  return factory;
}

/**
 * Production: a real Postgres over Supabase's session-mode pooler.
 *
 * `createPgClient` refuses a transaction-mode connection string at construction —
 * that mode connects fine and silently breaks row-level security, so it is caught
 * here as a boot failure rather than discovered as a data leak.
 */
function createProductionFactory(): RepositoryFactory {
  const url = process.env.CRM_DATABASE_URL?.trim();
  if (!url) {
    throw new NotConfiguredError(
      'CRM_DATABASE_URL is not set. Set it as a Worker secret:\n' +
        '  npx wrangler secret put CRM_DATABASE_URL\n' +
        'Use the Supabase SESSION-mode pooler (port 5432), not 6543. ' +
        'See IONIC_CRM/SETUP_ACCOUNTS.md.',
    );
  }
  return createPostgresRepository(createPgClient(url));
}

export function getRepositories(): Promise<RepositoryFactory> {
  if (process.env.NODE_ENV === 'production') {
    cache.factory ??= Promise.resolve(createProductionFactory());
    return cache.factory;
  }
  cache.factory ??= createMemoryDevFactory();
  return cache.factory;
}
