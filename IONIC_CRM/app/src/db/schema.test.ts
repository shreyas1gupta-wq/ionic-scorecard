import { describe, it, expect, beforeAll, afterAll, beforeEach } from 'vitest';
import { createTestDb, seedTicket, expectReject, type TestDb } from './test-harness';
import {
  GENESIS_HASH,
  canonicalTimestamp,
  computeRowHash,
  verifyChain,
  type AuditRow,
} from '../domain/hash-chain';

let t: TestDb;

beforeAll(async () => {
  t = await createTestDb();
});

afterAll(async () => {
  await t?.close();
});

/**
 * Fresh tickets per test, with monotonically increasing references.
 *
 * Nothing is deleted between tests: status_updates and audit_log are append-only
 * even for the owner, by design, so a truncating fixture would have to defeat the
 * very guarantee under test. Instead every assertion is written to be independent
 * of accumulated rows — either scoped to specific ids, or a "must see none" /
 * "must see at least" bound.
 */
let refCounter = 1000;
let aliceTicket: string;
let bobTicket: string;

beforeEach(async () => {
  aliceTicket = await seedTicket(t, {
    ref: `TKT-2026-${++refCounter}`,
    assigneeId: t.seed.aliceId,
    raiserId: t.seed.aliceId,
  });
  bobTicket = await seedTicket(t, {
    ref: `TKT-2026-${++refCounter}`,
    assigneeId: t.seed.bobId,
    raiserId: t.seed.bobId,
  });
});

// =============================================================================
// The harness itself must be trustworthy first.
//
// Superusers bypass RLS. If `set local role crm_app` silently failed, every
// authorisation test below would pass while proving nothing at all. So the very
// first thing to establish is that privilege really was dropped.
// =============================================================================
describe('harness integrity', () => {
  it('actually drops to the crm_app role', async () => {
    const who = await t.asEmployee(t.seed.aliceId, async (tx) => {
      const r = await tx.query<{ u: string }>('select current_user as u');
      return r.rows[0]!.u;
    });
    expect(who).toBe('crm_app');
  });

  it('crm_app is not a superuser and does not bypass RLS', async () => {
    const flags = await t.asEmployee(t.seed.aliceId, async (tx) => {
      const r = await tx.query<{ super: boolean; bypass: boolean }>(
        `select rolsuper as "super", rolbypassrls as bypass
         from pg_roles where rolname = current_user`,
      );
      return r.rows[0]!;
    });
    expect(flags.super).toBe(false);
    expect(flags.bypass).toBe(false);
  });

  it('exposes the acting employee to SQL', async () => {
    const id = await t.asEmployee(t.seed.aliceId, async (tx) => {
      const r = await tx.query<{ id: string | null }>('select app.current_employee() as id');
      return r.rows[0]!.id;
    });
    expect(id).toBe(t.seed.aliceId);
  });

  it('fails closed when no employee is set', async () => {
    const rows = await t.asEmployee(null, async (tx) => {
      const r = await tx.query('select id from tickets');
      return r.rows.length;
    });
    expect(rows).toBe(0);
  });
});

// =============================================================================
// Append-only: the property everything else rests on.
// =============================================================================
describe('status_updates is append-only', () => {
  beforeEach(async () => {
    await t.asEmployee(t.seed.aliceId, async (tx) => {
      await tx.query(
        `insert into status_updates (ticket_id, actor_id, punch_date, status, note)
         values ($1, $2, '2026-08-03', 'IN_PROGRESS', 'started')`,
        [aliceTicket, t.seed.aliceId],
      );
    });
  });

  it('rejects UPDATE as crm_app', async () => {
    const msg = await expectReject(
      t.asEmployee(t.seed.aliceId, (tx) =>
        tx.query(`update status_updates set note = 'rewritten'`),
      ),
    );
    expect(msg).toMatch(/append-only|permission denied/i);
  });

  it('rejects DELETE as crm_app', async () => {
    const msg = await expectReject(
      t.asEmployee(t.seed.aliceId, (tx) => tx.query('delete from status_updates')),
    );
    expect(msg).toMatch(/append-only|permission denied/i);
  });

  // The trigger layer exists precisely for this case: the owner holds every
  // privilege, so only the trigger stops them.
  it('rejects UPDATE even as the owner', async () => {
    const msg = await expectReject(
      t.asOwner((tx) => tx.query(`update status_updates set note = 'owner rewrite'`)),
    );
    expect(msg).toMatch(/append-only/i);
  });

  it('rejects DELETE even as the owner', async () => {
    const msg = await expectReject(t.asOwner((tx) => tx.query('delete from status_updates')));
    expect(msg).toMatch(/append-only/i);
  });

  it('rejects TRUNCATE even as the owner', async () => {
    const msg = await expectReject(t.asOwner((tx) => tx.query('truncate status_updates')));
    expect(msg).toMatch(/append-only/i);
  });

  it('rejects a no-op UPDATE too — the guard is not row-dependent', async () => {
    const msg = await expectReject(
      t.asOwner((tx) => tx.query(`update status_updates set note = note where false`)),
    );
    expect(msg).toMatch(/append-only/i);
  });
});

describe('audit_log is append-only and app-insert-proof', () => {
  it('refuses a direct INSERT by crm_app — writes must go through append_audit', async () => {
    const msg = await expectReject(
      t.asEmployee(t.seed.adminId, (tx) =>
        tx.query(
          `insert into audit_log (action, entity, prev_hash, row_hash)
           values ('FORGED', 'tickets', $1, $1)`,
          [GENESIS_HASH],
        ),
      ),
    );
    expect(msg).toMatch(/permission denied/i);
  });

  it('rejects UPDATE and DELETE even as the owner', async () => {
    expect(await expectReject(t.asOwner((tx) => tx.query(`update audit_log set action = 'x'`))))
      .toMatch(/append-only/i);
    expect(await expectReject(t.asOwner((tx) => tx.query('delete from audit_log'))))
      .toMatch(/append-only/i);
  });
});

// =============================================================================
// Row-level security — the defence against IDOR.
// =============================================================================
describe('ticket visibility', () => {
  it('lets an employee see their own ticket', async () => {
    const n = await t.asEmployee(t.seed.aliceId, async (tx) => {
      const r = await tx.query('select id from tickets where id = $1', [aliceTicket]);
      return r.rows.length;
    });
    expect(n).toBe(1);
  });

  it("does NOT let an employee see a colleague's ticket", async () => {
    const n = await t.asEmployee(t.seed.aliceId, async (tx) => {
      const r = await tx.query('select id from tickets where id = $1', [bobTicket]);
      return r.rows.length;
    });
    expect(n).toBe(0);
  });

  it("lets a manager see a report's ticket", async () => {
    const n = await t.asEmployee(t.seed.managerId, async (tx) => {
      const r = await tx.query('select id from tickets where id in ($1, $2)', [
        aliceTicket,
        bobTicket,
      ]);
      return r.rows.length;
    });
    expect(n).toBe(2);
  });

  it('does not let an unrelated employee see anything', async () => {
    const n = await t.asEmployee(t.seed.outsiderId, async (tx) => {
      const r = await tx.query('select id from tickets');
      return r.rows.length;
    });
    expect(n).toBe(0);
  });

  it('lets an admin see everything', async () => {
    const n = await t.asEmployee(t.seed.adminId, async (tx) => {
      const r = await tx.query('select id from tickets');
      return r.rows.length;
    });
    expect(n).toBeGreaterThanOrEqual(2);
  });

  it('makes a watcher able to see the ticket they watch', async () => {
    await t.db.query(
      'insert into ticket_watchers (ticket_id, employee_id) values ($1, $2)',
      [bobTicket, t.seed.outsiderId],
    );
    const n = await t.asEmployee(t.seed.outsiderId, async (tx) => {
      const r = await tx.query('select id from tickets where id = $1', [bobTicket]);
      return r.rows.length;
    });
    expect(n).toBe(1);
  });

  it('hides punches on tickets you cannot see', async () => {
    await t.asEmployee(t.seed.bobId, async (tx) => {
      await tx.query(
        `insert into status_updates (ticket_id, actor_id, punch_date, status, note)
         values ($1, $2, '2026-08-03', 'IN_PROGRESS', 'bob at work')`,
        [bobTicket, t.seed.bobId],
      );
    });
    const n = await t.asEmployee(t.seed.aliceId, async (tx) => {
      const r = await tx.query('select id from status_updates where ticket_id = $1', [bobTicket]);
      return r.rows.length;
    });
    expect(n).toBe(0);
  });

  it('keeps the audit log admin-only', async () => {
    const asAlice = await t.asEmployee(t.seed.aliceId, async (tx) => {
      const r = await tx.query('select seq from audit_log');
      return r.rows.length;
    });
    expect(asAlice).toBe(0);
  });
});

describe('identity cannot be forged', () => {
  it('refuses a punch whose actor_id is someone else', async () => {
    // The realistic attack: a request that passes another employee's id.
    const msg = await expectReject(
      t.asEmployee(t.seed.aliceId, (tx) =>
        tx.query(
          `insert into status_updates (ticket_id, actor_id, punch_date, status, note)
           values ($1, $2, '2026-08-03', 'IN_PROGRESS', 'not me')`,
          [aliceTicket, t.seed.bobId],
        ),
      ),
    );
    expect(msg).toMatch(/row-level security|violates/i);
  });

  it('refuses a punch on a ticket you cannot see', async () => {
    const msg = await expectReject(
      t.asEmployee(t.seed.aliceId, (tx) =>
        tx.query(
          `insert into status_updates (ticket_id, actor_id, punch_date, status, note)
           values ($1, $2, '2026-08-03', 'IN_PROGRESS', 'trespass')`,
          [bobTicket, t.seed.aliceId],
        ),
      ),
    );
    expect(msg).toMatch(/row-level security|violates/i);
  });

  it('refuses a ticket raised in someone else’s name', async () => {
    const msg = await expectReject(
      t.asEmployee(t.seed.aliceId, (tx) =>
        tx.query(
          `insert into tickets (ref, title, priority, assignee_id, raiser_id, deadline, original_deadline)
           values ('TKT-2026-7777', 'forged', 'P2', $1, $2, '2026-12-31', '2026-12-31')`,
          [t.seed.aliceId, t.seed.bobId],
        ),
      ),
    );
    expect(msg).toMatch(/row-level security|violates/i);
  });

  it('denies all access to ticket_counters, which has no policy', async () => {
    const msg = await expectReject(
      t.asEmployee(t.seed.adminId, (tx) => tx.query('select * from ticket_counters')),
    );
    expect(msg).toMatch(/permission denied|row-level security/i);
  });

  it('still allocates references through the definer function', async () => {
    const [a, b] = await t.asEmployee(t.seed.aliceId, async (tx) => {
      const r1 = await tx.query<{ s: number }>('select app.next_ticket_seq(2026) as s');
      const r2 = await tx.query<{ s: number }>('select app.next_ticket_seq(2026) as s');
      return [r1.rows[0]!.s, r2.rows[0]!.s];
    });
    expect(b).toBe(a + 1);
  });
});

// =============================================================================
// Immutable columns.
// =============================================================================
describe('write-once columns', () => {
  it('refuses to change original_deadline', async () => {
    const msg = await expectReject(
      t.asOwner((tx) =>
        tx.query(`update tickets set original_deadline = '2027-01-01' where id = $1`, [
          aliceTicket,
        ]),
      ),
    );
    expect(msg).toMatch(/original_deadline is immutable/i);
  });

  it('allows the current deadline to move', async () => {
    await t.asOwner((tx) =>
      tx.query(`update tickets set deadline = '2027-01-01' where id = $1`, [aliceTicket]),
    );
    const r = await t.db.query<{ deadline: Date }>(
      'select deadline from tickets where id = $1',
      [aliceTicket],
    );
    expect(r.rows.length).toBe(1);
  });

  it('refuses to change the ticket reference', async () => {
    const msg = await expectReject(
      t.asOwner((tx) =>
        tx.query(`update tickets set ref = 'TKT-2026-0002' where id = $1`, [aliceTicket]),
      ),
    );
    expect(msg).toMatch(/ref is immutable/i);
  });

  it('refuses to change the raiser', async () => {
    const msg = await expectReject(
      t.asOwner((tx) =>
        tx.query('update tickets set raiser_id = $1 where id = $2', [t.seed.bobId, aliceTicket]),
      ),
    );
    expect(msg).toMatch(/raiser_id is immutable/i);
  });
});

// =============================================================================
// Data integrity constraints.
// =============================================================================
describe('constraints', () => {
  it('requires a reason when a punch reports BLOCKED', async () => {
    const msg = await expectReject(
      t.asEmployee(t.seed.aliceId, (tx) =>
        tx.query(
          `insert into status_updates (ticket_id, actor_id, punch_date, status, note)
           values ($1, $2, '2026-08-03', 'BLOCKED', 'stuck')`,
          [aliceTicket, t.seed.aliceId],
        ),
      ),
    );
    expect(msg).toMatch(/blocked_needs_reason/i);
  });

  it('accepts BLOCKED when a reason is given', async () => {
    await t.asEmployee(t.seed.aliceId, (tx) =>
      tx.query(
        `insert into status_updates (ticket_id, actor_id, punch_date, status, note, blocked_reason)
         values ($1, $2, '2026-08-03', 'BLOCKED', 'stuck', 'waiting on legal')`,
        [aliceTicket, t.seed.aliceId],
      ),
    );
  });

  it('requires a reason to deactivate an employee', async () => {
    const msg = await expectReject(
      t.asOwner((tx) =>
        tx.query(
          `update employees set status = 'DEACTIVATED', deactivated_at = now() where id = $1`,
          [t.seed.outsiderId],
        ),
      ),
    );
    expect(msg).toMatch(/deactivation_complete/i);
  });

  it('rejects a malformed ticket reference', async () => {
    const msg = await expectReject(
      t.asOwner((tx) =>
        tx.query(
          `insert into tickets (ref, title, priority, assignee_id, raiser_id, deadline, original_deadline)
           values ('TICKET-1', 'bad ref', 'P2', $1, $1, '2026-12-31', '2026-12-31')`,
          [t.seed.aliceId],
        ),
      ),
    );
    expect(msg).toMatch(/ref_check|violates check/i);
  });

  it('rejects a non-lowercase work email', async () => {
    const msg = await expectReject(
      t.asOwner((tx) =>
        tx.query(`insert into employees (work_email, display_name) values ('Mixed@Ionic.in', 'X')`),
      ),
    );
    expect(msg).toMatch(/work_email_check|violates check/i);
  });

  it('stops an employee managing themselves', async () => {
    const msg = await expectReject(
      t.asOwner((tx) =>
        tx.query('update employees set manager_id = id where id = $1', [t.seed.aliceId]),
      ),
    );
    expect(msg).toMatch(/no_self_manage/i);
  });

  it('requires a cancel reason when cancelling', async () => {
    const msg = await expectReject(
      t.asOwner((tx) =>
        tx.query(
          `update tickets set status = 'CANCELLED', closed_at = now(), closed_date = '2026-08-03'
           where id = $1`,
          [aliceTicket],
        ),
      ),
    );
    expect(msg).toMatch(/cancel_reason/i);
  });
});

// =============================================================================
// access_events — CSCRF 2-year retention, append-only with one narrow exception.
// =============================================================================
describe('access_events', () => {
  it('accepts an insert from a signed-in employee', async () => {
    await t.asEmployee(t.seed.aliceId, (tx) =>
      tx.query(
        `insert into access_events (employee_id, event, entity, entity_id)
         values ($1, 'VIEW', 'tickets', $2)`,
        [t.seed.aliceId, aliceTicket],
      ),
    );
  });

  it('keeps them readable only by an admin', async () => {
    const asAlice = await t.asEmployee(t.seed.aliceId, async (tx) => {
      const r = await tx.query('select seq from access_events');
      return r.rows.length;
    });
    expect(asAlice).toBe(0);

    const asAdmin = await t.asEmployee(t.seed.adminId, async (tx) => {
      const r = await tx.query('select seq from access_events');
      return r.rows.length;
    });
    expect(asAdmin).toBeGreaterThan(0);
  });

  it('permits stamping archived_at', async () => {
    await t.asOwner((tx) =>
      tx.query('update access_events set archived_at = now() where archived_at is null'),
    );
  });

  it('refuses to rewrite any other column', async () => {
    const msg = await expectReject(
      t.asOwner((tx) => tx.query(`update access_events set event = 'LOGIN'`)),
    );
    expect(msg).toMatch(/append-only except archived_at/i);
  });

  it('refuses to delete a row that was never archived', async () => {
    await t.db.query(
      `insert into access_events (employee_id, event) values ($1, 'LOGIN')`,
      [t.seed.bobId],
    );
    const msg = await expectReject(
      t.asOwner((tx) => tx.query('delete from access_events where archived_at is null')),
    );
    expect(msg).toMatch(/archive it first/i);
  });

  it('allows deleting a row once archived — the pruning path', async () => {
    await t.db.query(
      `insert into access_events (employee_id, event, archived_at) values ($1, 'VIEW', now())`,
      [t.seed.bobId],
    );
    const deleted = await t.asOwner(async (tx) => {
      const r = await tx.query<{ seq: string }>(
        'delete from access_events where archived_at is not null returning seq',
      );
      return r.rows.length;
    });
    expect(deleted).toBeGreaterThan(0);
  });
});

// =============================================================================
// The hash chain, end to end: the TypeScript implementation and the SQL writer
// must agree, or verification fails for reasons nobody can find.
// =============================================================================
describe('audit chain through app.append_audit', () => {
  async function append(
    actorId: string,
    action: string,
    entity: string,
    entityId: string | null,
    payload: Record<string, unknown>,
    occurredAt: string,
  ): Promise<void> {
    await t.asEmployee(actorId, async (tx) => {
      const head = await tx.query<{ h: Uint8Array; s: string }>(
        'select app.audit_chain_head() as h, app.audit_next_seq() as s',
      );
      const prev = Buffer.from(head.rows[0]!.h);
      const seq = Number(head.rows[0]!.s);
      const row = {
        seq,
        occurredAt: canonicalTimestamp(occurredAt),
        actorId,
        action,
        entity,
        entityId,
        payload: payload as never,
      };
      const rowHash = computeRowHash(prev, row);
      await tx.query(
        `select app.append_audit($1::bigint, $2::timestamptz, $3::uuid, $4, $5, $6, $7::jsonb, $8::bytea, $9::bytea)`,
        [seq, occurredAt, actorId, action, entity, entityId, JSON.stringify(payload), prev, rowHash],
      );
    });
  }

  it('writes a chain that the TypeScript verifier accepts', async () => {
    await append(t.seed.aliceId, 'TICKET_CREATED', 'tickets', aliceTicket, { a: 1 }, '2026-08-03 09:00:00+00');
    await append(t.seed.aliceId, 'PUNCH_CREATED', 'status_updates', 'x', { b: 2 }, '2026-08-03 09:05:00+00');
    await append(t.seed.bobId, 'TICKET_CREATED', 'tickets', bobTicket, { c: 3 }, '2026-08-03 09:10:00+00');

    const rows = await t.asEmployee(t.seed.adminId, async (tx) => {
      const r = await tx.query<{
        seq: string;
        occurred_at: Date;
        actor_id: string | null;
        action: string;
        entity: string;
        entity_id: string | null;
        payload: Record<string, unknown>;
        prev_hash: Uint8Array;
        row_hash: Uint8Array;
      }>('select * from audit_log order by seq');
      return r.rows;
    });

    expect(rows.length).toBeGreaterThanOrEqual(3);

    const chain: AuditRow[] = rows.map((r) => ({
      seq: Number(r.seq),
      occurredAt: canonicalTimestamp(r.occurred_at),
      actorId: r.actor_id,
      action: r.action,
      entity: r.entity,
      entityId: r.entity_id,
      payload: r.payload as never,
      prevHash: Buffer.from(r.prev_hash),
      rowHash: Buffer.from(r.row_hash),
    }));

    const result = verifyChain(chain);
    expect(result.failures).toEqual([]);
    expect(result.ok).toBe(true);
  });

  it('rejects an append whose prev_hash is stale — the concurrent-writer case', async () => {
    // Simulates two writers reading the same head: the second must be refused
    // rather than silently forking the chain.
    const msg = await expectReject(
      t.asEmployee(t.seed.aliceId, async (tx) => {
        const s = await tx.query<{ s: string }>('select app.audit_next_seq() as s');
        const seq = Number(s.rows[0]!.s);
        const stale = GENESIS_HASH; // deliberately not the real head
        const row = {
          seq,
          occurredAt: canonicalTimestamp('2026-08-03 10:00:00+00'),
          actorId: t.seed.aliceId,
          action: 'STALE',
          entity: 'tickets',
          entityId: null,
          payload: {} as never,
        };
        return tx.query(
          `select app.append_audit($1::bigint, $2::timestamptz, $3::uuid, $4, $5, $6, $7::jsonb, $8::bytea, $9::bytea)`,
          [
            seq,
            '2026-08-03 10:00:00+00',
            t.seed.aliceId,
            'STALE',
            'tickets',
            null,
            '{}',
            stale,
            computeRowHash(stale, row),
          ],
        );
      }),
    );
    expect(msg).toMatch(/chain head moved/i);
  });

  it('rejects an append whose seq is not the next one', async () => {
    const msg = await expectReject(
      t.asEmployee(t.seed.aliceId, async (tx) => {
        const head = await tx.query<{ h: Uint8Array }>('select app.audit_chain_head() as h');
        const prev = Buffer.from(head.rows[0]!.h);
        const wrongSeq = 9999;
        const row = {
          seq: wrongSeq,
          occurredAt: canonicalTimestamp('2026-08-03 11:00:00+00'),
          actorId: t.seed.aliceId,
          action: 'GAP',
          entity: 'tickets',
          entityId: null,
          payload: {} as never,
        };
        return tx.query(
          `select app.append_audit($1::bigint, $2::timestamptz, $3::uuid, $4, $5, $6, $7::jsonb, $8::bytea, $9::bytea)`,
          [
            wrongSeq,
            '2026-08-03 11:00:00+00',
            t.seed.aliceId,
            'GAP',
            'tickets',
            null,
            '{}',
            prev,
            computeRowHash(prev, row),
          ],
        );
      }),
    );
    expect(msg).toMatch(/seq mismatch/i);
  });
});
