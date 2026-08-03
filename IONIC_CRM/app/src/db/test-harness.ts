/**
 * Test harness: a real Postgres, in-process, with no server and no admin rights.
 *
 * PGlite is Postgres 18 compiled to WebAssembly. That matters here for one
 * specific reason: the guarantees we care about — revoked privileges, statement
 * triggers, row-level security, SECURITY DEFINER functions — are Postgres
 * behaviours. A mock or an in-memory fake would prove nothing about them.
 *
 * The database runs as superuser, and superusers bypass RLS. So every test that
 * exercises authorisation must go through `asEmployee()`, which switches to the
 * non-privileged `crm_app` role. Forgetting that would make a test pass while
 * the policy it claims to check does nothing — so `asEmployee` is the only path
 * offered for authenticated work.
 */

import { PGlite } from '@electric-sql/pglite';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { migrate, type SqlRunner } from './migrate';

const HERE = dirname(fileURLToPath(import.meta.url));
export const MIGRATIONS_DIR = join(HERE, '..', '..', 'db', 'migrations');

export interface Seed {
  readonly adminId: string;
  readonly managerId: string;
  /** Reports to manager. */
  readonly aliceId: string;
  /** Reports to manager. */
  readonly bobId: string;
  /** Reports to nobody — the isolation control. */
  readonly outsiderId: string;
  readonly categoryId: string;
}

export interface TestDb {
  readonly db: PGlite;
  readonly seed: Seed;
  /** Run as a signed-in employee under the `crm_app` role, with RLS in force. */
  asEmployee<T>(employeeId: string | null, fn: (tx: SqlRunner) => Promise<T>): Promise<T>;
  /** Run as the owner/superuser. For seeding and for testing owner-level guards. */
  asOwner<T>(fn: (tx: SqlRunner) => Promise<T>): Promise<T>;
  close(): Promise<void>;
}

export async function createTestDb(): Promise<TestDb> {
  const db = await PGlite.create();
  await migrate(db as unknown as SqlRunner, MIGRATIONS_DIR);

  // Seeded as superuser, so RLS does not interfere with setup.
  const ins = async (email: string, name: string, role: string, managerId: string | null) => {
    const r = await db.query<{ id: string }>(
      `insert into employees (work_email, display_name, role, manager_id)
       values ($1, $2, $3, $4) returning id`,
      [email, name, role, managerId],
    );
    return r.rows[0]!.id;
  };

  const adminId = await ins('admin@ionic.in', 'Admin', 'ADMIN', null);
  const managerId = await ins('manager@ionic.in', 'Manager', 'MANAGER', null);
  const aliceId = await ins('alice@ionic.in', 'Alice', 'EMPLOYEE', managerId);
  const bobId = await ins('bob@ionic.in', 'Bob', 'EMPLOYEE', managerId);
  const outsiderId = await ins('outsider@ionic.in', 'Outsider', 'EMPLOYEE', null);

  const cat = await db.query<{ id: string }>(
    `insert into categories (name) values ('Ops') returning id`,
  );

  const seed: Seed = {
    adminId,
    managerId,
    aliceId,
    bobId,
    outsiderId,
    categoryId: cat.rows[0]!.id,
  };

  async function asEmployee<T>(
    employeeId: string | null,
    fn: (tx: SqlRunner) => Promise<T>,
  ): Promise<T> {
    return db.transaction(async (tx) => {
      // Set the identity GUC first, then drop privilege. `true` makes it
      // transaction-local, so it cannot leak into the next test.
      await tx.query('select set_config($1, $2, true)', ['app.employee_id', employeeId ?? '']);
      await tx.exec('set local role crm_app');
      return fn(tx as unknown as SqlRunner);
    }) as Promise<T>;
  }

  async function asOwner<T>(fn: (tx: SqlRunner) => Promise<T>): Promise<T> {
    return db.transaction(async (tx) => fn(tx as unknown as SqlRunner)) as Promise<T>;
  }

  return {
    db,
    seed,
    asEmployee,
    asOwner,
    close: () => db.close(),
  };
}

/**
 * Wipe all transactional data, keeping employees, categories, holidays and the
 * schema itself. For reusing one database across tests instead of building a new
 * Postgres per test.
 *
 * WHY THIS IS NOT A HOLE IN THE APPEND-ONLY GUARANTEE:
 *
 *  - `ALTER TABLE ... DISABLE TRIGGER` requires TABLE OWNERSHIP. The application
 *    connects as `crm_app`, which owns nothing, so this is unreachable from any
 *    code path that serves a request.
 *  - The privilege revokes in 0002 are untouched: even with triggers disabled,
 *    `crm_app` still has no UPDATE or DELETE on these tables.
 *  - `schema.test.ts` separately proves that the OWNER cannot delete a punch
 *    while the triggers are enabled, which is the property that actually matters.
 *
 * The alternative — a fresh PGlite per test — allocates a whole Postgres WASM
 * heap each time and exhausts the test worker's memory once the suite grows.
 */
export async function resetTransactionalData(db: PGlite): Promise<void> {
  const appendOnly = ['status_updates', 'audit_log', 'access_events'];
  for (const t of appendOnly) {
    await db.exec(`alter table ${t} disable trigger user`);
  }
  try {
    // Children before parents: no ON DELETE CASCADE on the audit trail, by design.
    await db.exec(`
      delete from status_updates;
      delete from audit_log;
      delete from access_events;
      delete from ticket_watchers;
      delete from deadline_changes;
      delete from tickets;
      delete from ticket_counters;
    `);
  } finally {
    // Restored even if the delete fails, so one bad test cannot silently leave
    // the guarantee switched off for every test after it.
    for (const t of appendOnly) {
      await db.exec(`alter table ${t} enable trigger user`);
    }
  }
}

/**
 * Insert a ticket directly, bypassing RLS. For arranging test state only —
 * never a substitute for exercising the real insert path.
 */
export async function seedTicket(
  t: TestDb,
  opts: {
    ref: string;
    assigneeId: string;
    raiserId: string;
    priority?: 'P1' | 'P2' | 'P3';
    deadline?: string;
    status?: string;
  },
): Promise<string> {
  const deadline = opts.deadline ?? '2026-12-31';
  const r = await t.db.query<{ id: string }>(
    `insert into tickets (ref, title, priority, assignee_id, raiser_id, deadline, original_deadline, status)
     values ($1, $2, $3, $4, $5, $6, $6, $7) returning id`,
    [
      opts.ref,
      `Ticket ${opts.ref}`,
      opts.priority ?? 'P2',
      opts.assigneeId,
      opts.raiserId,
      deadline,
      opts.status ?? 'OPEN',
    ],
  );
  return r.rows[0]!.id;
}

/** Assert a promise rejects, and return the message for further matching. */
export async function expectReject(p: Promise<unknown>): Promise<string> {
  try {
    await p;
  } catch (err) {
    return (err as Error).message;
  }
  throw new Error('expected the operation to be rejected, but it succeeded');
}
