/**
 * The server's repository factory.
 *
 * THREE MODES, and the default is deliberately the cheap one.
 *
 *   memory  (default in development) — the in-memory repository. Starts
 *           instantly, uses almost no RAM, and is safe to build UI against
 *           because `src/repo/contract.test.ts` runs one suite of rules against
 *           both it and Postgres. If the two ever diverge, CI fails.
 *
 *   pglite  (opt-in via CRM_DEV_STORE=pglite) — a real Postgres compiled to
 *           WebAssembly, persisted to `.pgdata/`, running the SAME migrations
 *           and the SAME row-level-security policies as production. This is what
 *           you use when changing a policy or a migration, because the in-memory
 *           store cannot prove anything about SQL. It costs roughly a gigabyte of
 *           RAM and a few seconds of startup.
 *
 *   production — not wired yet. That is milestone M11 and needs the Principal's
 *           Supabase project. `getRepositories()` throws something specific and
 *           actionable rather than leaving a silent placeholder.
 *
 * WHY MEMORY IS THE DEFAULT: this was measured, not assumed. The development
 * machine had 2.3 GB free of 15.6 GB, and loading PGlite inside the Turbopack dev
 * server exhausted V8's allocator outright ("Fatal process out of memory: Zone").
 * Making the UI's day-to-day loop depend on a gigabyte of spare RAM would be a
 * bad trade when a contract-verified fake costs nothing.
 *
 * THE HONEST LIMITATION: the in-memory store enforces the authorisation rules in
 * TypeScript, so it cannot catch a mistake in an RLS policy. Only `pglite` mode
 * and the test suite can. Change a policy → run the tests, and run dev in pglite
 * mode at least once before shipping it.
 */

import { migrate, type SqlRunner } from '../db/migrate';
import { createMemoryRepository } from '../repo/memory';
import { createPostgresRepository, type SqlClient } from '../repo/postgres';
import type { RepositoryFactory } from '../repo/types';

export class NotConfiguredError extends Error {
  override readonly name = 'NotConfiguredError';
}

export type DevStore = 'memory' | 'pglite';

export function devStoreFromEnv(env: NodeJS.ProcessEnv = process.env): DevStore {
  return env.CRM_DEV_STORE?.trim().toLowerCase() === 'pglite' ? 'pglite' : 'memory';
}

/** The development team. Shared by both dev stores so they behave alike. */
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

async function createPgliteDevFactory(): Promise<RepositoryFactory> {
  // Imported lazily so `memory` mode never pays the cost of loading a Postgres
  // WASM binary it is not going to use.
  const { PGlite } = await import('@electric-sql/pglite');
  const { fileURLToPath } = await import('node:url');
  const { dirname, join } = await import('node:path');

  const here = dirname(fileURLToPath(import.meta.url));
  const migrationsDir = join(here, '..', '..', 'db', 'migrations');
  const dataDir = join(here, '..', '..', '.pgdata');

  const db = await PGlite.create({ dataDir });
  await migrate(db as unknown as SqlRunner, migrationsDir);

  // Guarded on the table being empty rather than a flag file, so deleting
  // `.pgdata/` is all it takes to start over.
  const existing = await db.query<{ n: number }>('select count(*)::int as n from employees');
  if ((existing.rows[0]?.n ?? 0) === 0) {
    const byEmail = new Map<string, string>();
    for (const e of DEV_TEAM) {
      const managerId = 'managerEmail' in e ? byEmail.get(e.managerEmail) ?? null : null;
      const r = await db.query<{ id: string }>(
        `insert into employees (work_email, display_name, role, manager_id)
         values ($1, $2, $3, $4) returning id`,
        [e.workEmail, e.displayName, e.role, managerId],
      );
      byEmail.set(e.workEmail, r.rows[0]!.id);
    }
    for (const name of DEV_CATEGORIES) {
      await db.query('insert into categories (name) values ($1)', [name]);
    }
    for (const [date, label] of DEV_HOLIDAYS) {
      await db.query('insert into holidays (holiday_date, name) values ($1, $2)', [date, label]);
    }
  }

  return createPostgresRepository(db as unknown as SqlClient);
}

export function getRepositories(): Promise<RepositoryFactory> {
  if (process.env.NODE_ENV === 'production') {
    throw new NotConfiguredError(
      'No production database adapter is configured yet (milestone M11). ' +
        'This needs a Supabase project in ap-south-1 and CRM_DATABASE_URL set as a ' +
        'Worker secret. See IONIC_CRM/PLAN.md M11 and DESIGN.md §9.',
    );
  }
  cache.factory ??=
    devStoreFromEnv() === 'pglite' ? createPgliteDevFactory() : createMemoryDevFactory();
  return cache.factory;
}
