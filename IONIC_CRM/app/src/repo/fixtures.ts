/**
 * Shared test fixtures: the same five-person team, backed either by the
 * in-memory repository or by a real Postgres.
 *
 * Extracted so the repository contract suite and the service suite exercise
 * identical setups. Every behavioural test in this project runs twice — once
 * against each implementation — which is what keeps the fake honest.
 */

import { PGlite } from '@electric-sql/pglite';
import { migrate } from '../db/migrate';
import { MIGRATIONS_DIR, resetTransactionalData } from '../db/test-harness';
import { createMemoryRepository } from './memory';
import { createPostgresRepository, type SqlClient } from './postgres';
import type { RepositoryFactory, Uuid } from './types';

export const HOLIDAY = '2026-08-14';
/** Seeded with the same name in both stores, so the contract can assert it. */
export const HOLIDAY_NAME = 'Independence Day';

/** Seeded in both stores. Deliberately not alphabetical, so ordering is tested. */
export const CATEGORIES = ['Operations', 'Compliance', 'Client Reporting'] as const;

export const EMAILS = {
  admin: 'admin@ionic.in',
  manager: 'manager@ionic.in',
  alice: 'alice@ionic.in',
  bob: 'bob@ionic.in',
  outsider: 'outsider@ionic.in',
} as const;

export interface Ids {
  admin: Uuid;
  manager: Uuid;
  /** Reports to manager. */
  alice: Uuid;
  /** Reports to manager. */
  bob: Uuid;
  /** Reports to nobody — the isolation control. */
  outsider: Uuid;
}

export interface Fixture {
  readonly factory: RepositoryFactory;
  readonly ids: Ids;
  addWatcher(ticketId: Uuid, employeeId: Uuid): Promise<void>;
  /** Clear tickets, punches, audit and access rows between tests; keep the team. */
  reset(): Promise<void>;
  teardown(): Promise<void>;
}

export async function memoryFixture(): Promise<Fixture> {
  const factory = createMemoryRepository({
    employees: [
      { workEmail: EMAILS.admin, displayName: 'Admin', role: 'ADMIN' },
      { workEmail: EMAILS.manager, displayName: 'Manager', role: 'MANAGER' },
      {
        workEmail: EMAILS.alice,
        displayName: 'Alice',
        role: 'EMPLOYEE',
        managerEmail: EMAILS.manager,
      },
      { workEmail: EMAILS.bob, displayName: 'Bob', role: 'EMPLOYEE', managerEmail: EMAILS.manager },
      { workEmail: EMAILS.outsider, displayName: 'Outsider', role: 'EMPLOYEE' },
    ],
    holidays: [{ date: HOLIDAY, name: HOLIDAY_NAME }],
    categories: CATEGORIES,
  });

  return {
    factory,
    ids: {
      admin: factory.idByEmail(EMAILS.admin),
      manager: factory.idByEmail(EMAILS.manager),
      alice: factory.idByEmail(EMAILS.alice),
      bob: factory.idByEmail(EMAILS.bob),
      outsider: factory.idByEmail(EMAILS.outsider),
    },
    async addWatcher(ticketId, employeeId) {
      factory.addWatcher(ticketId, employeeId);
    },
    async reset() {
      factory.reset();
    },
    async teardown() {
      await factory.close();
    },
  };
}

/**
 * ONE database for the whole run, with transactional data wiped between tests.
 *
 * A fresh Postgres per test would be tidier in principle, but each PGlite instance
 * allocates a full Postgres WASM heap and ~30 of them exhaust the test worker —
 * presenting as `ERR_IPC_CHANNEL_CLOSED`, which looks nothing like the
 * out-of-memory error it is. See `resetTransactionalData` for why the reset does
 * not weaken the append-only guarantee.
 */
export async function postgresFixture(): Promise<Fixture> {
  const db = await PGlite.create();
  await migrate(db as never, MIGRATIONS_DIR);

  const insert = async (email: string, name: string, role: string, managerId: string | null) => {
    const r = await db.query<{ id: string }>(
      `insert into employees (work_email, display_name, role, manager_id)
       values ($1, $2, $3, $4) returning id`,
      [email, name, role, managerId],
    );
    return r.rows[0]!.id;
  };

  const admin = await insert(EMAILS.admin, 'Admin', 'ADMIN', null);
  const manager = await insert(EMAILS.manager, 'Manager', 'MANAGER', null);
  const alice = await insert(EMAILS.alice, 'Alice', 'EMPLOYEE', manager);
  const bob = await insert(EMAILS.bob, 'Bob', 'EMPLOYEE', manager);
  const outsider = await insert(EMAILS.outsider, 'Outsider', 'EMPLOYEE', null);
  await db.query('insert into holidays (holiday_date, name) values ($1, $2)', [
    HOLIDAY,
    HOLIDAY_NAME,
  ]);
  for (const name of CATEGORIES) {
    await db.query('insert into categories (name) values ($1)', [name]);
  }

  const factory = createPostgresRepository(db as unknown as SqlClient);

  return {
    factory,
    ids: { admin, manager, alice, bob, outsider },
    async addWatcher(ticketId, employeeId) {
      await db.query('insert into ticket_watchers (ticket_id, employee_id) values ($1, $2)', [
        ticketId,
        employeeId,
      ]);
    },
    async reset() {
      await resetTransactionalData(db);
    },
    async teardown() {
      await db.close();
    },
  };
}

/** Feed this to `describe.each` so every suite runs against both stores. */
export const IMPLEMENTATIONS: readonly [string, () => Promise<Fixture>][] = [
  ['in-memory', memoryFixture],
  ['postgres', postgresFixture],
];
