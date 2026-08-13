/**
 * ONE suite, run against BOTH implementations.
 *
 * This is what makes the in-memory repository safe to develop and test against.
 * A fake whose behaviour is merely *believed* to match the database is worse than
 * no fake at all: it makes the fast tests green while the real thing refuses. So
 * every rule below is asserted twice - once against Postgres, once against the
 * fake - and any divergence fails here rather than in production.
 *
 * The Postgres side runs on PGlite, so this needs no server and no credentials.
 * Fixtures live in ./fixtures.ts and are shared with the service suite.
 */

import { describe, it, expect, beforeAll, beforeEach, afterAll } from 'vitest';
import {
  CATEGORIES,
  EMAILS,
  HOLIDAY,
  HOLIDAY_NAME,
  IMPLEMENTATIONS,
  type Fixture,
} from './fixtures';
import { AuthorizationError, ValidationError, type Repository, type Uuid } from './types';

/**
 * A unique work email per call.
 *
 * `reset()` between tests clears tickets, punches and audit rows but deliberately
 * keeps the team — the schema has no way to delete an employee, and inventing one
 * for test convenience would be inventing one an attacker could use. So every
 * admin test works on a throwaway colleague of its own and leaves the seeded five
 * untouched.
 */
let unique = 0;
const nextUnique = () => (unique += 1);
const nextJoiner = () => {
  const n = nextUnique();
  return { workEmail: `joiner${n}@ionic.in`, displayName: `Joiner ${n}` };
};

describe.each(IMPLEMENTATIONS)('repository contract: %s', (_name, build) => {
  let f: Fixture;

  beforeAll(async () => {
    f = await build();
  });

  beforeEach(async () => {
    await f.reset();
  });

  afterAll(async () => {
    await f?.teardown();
  });

  /** Run a block as `actor`, with the return type inferred from the block. */
  const as = <T>(actor: Uuid, fn: (repo: Repository) => Promise<T>): Promise<T> =>
    f.factory.withActor({ employeeId: actor }, fn);

  /** Create a ticket as `actor`, assigned to `assignee`. */
  const createTicket = (actor: Uuid, assignee: Uuid, deadline = '2026-12-31') =>
    f.factory.withActor({ employeeId: actor }, (repo) =>
      repo.tickets.create({
        title: 'Prepare the monthly pack',
        priority: 'P2',
        assigneeId: assignee,
        raiserId: actor,
        deadline,
      }),
    );

  // ===========================================================================
  describe('identity', () => {
    it('resolves an allow-listed email', async () => {
      const e = await as(f.ids.alice, (repo) => repo.employees.findByEmail(EMAILS.alice));
      expect(e?.id).toBe(f.ids.alice);
      expect(e?.role).toBe('EMPLOYEE');
      expect(e?.managerId).toBe(f.ids.manager);
    });

    it('is case-insensitive about the email, as mail systems are', async () => {
      const e = await as(f.ids.alice, (repo) => repo.employees.findByEmail('  ALICE@Ionic.IN '));
      expect(e?.id).toBe(f.ids.alice);
    });

    it('returns null for an email that is not allow-listed', async () => {
      const e = await as(f.ids.alice, (repo) => repo.employees.findByEmail('stranger@example.com'));
      expect(e).toBeNull();
    });

    it('exposes the staff directory to any signed-in employee', async () => {
      const list = await as(f.ids.outsider, (repo) => repo.employees.listActive());
      expect(list.length).toBe(5);
    });

    it('resolves an identity before any actor exists', async () => {
      const e = await f.factory.resolveIdentity(EMAILS.bob);
      expect(e?.id).toBe(f.ids.bob);
    });

    it('does not resolve an unknown address', async () => {
      expect(await f.factory.resolveIdentity('nobody@ionic.in')).toBeNull();
    });
  });

  // ===========================================================================
  describe('creating a ticket', () => {
    it('assigns a well-formed reference and mirrors the deadline into original', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice);
      expect(t.ref).toMatch(/^TKT-2026-\d{4,}$/);
      expect(t.deadline).toBe('2026-12-31');
      expect(t.originalDeadline).toBe('2026-12-31');
      expect(t.status).toBe('OPEN');
      expect(t.raiserId).toBe(f.ids.alice);
    });

    it('allocates distinct references', async () => {
      const a = await createTicket(f.ids.alice, f.ids.alice);
      const b = await createTicket(f.ids.alice, f.ids.alice);
      expect(a.ref).not.toBe(b.ref);
    });

    it('refuses a ticket raised in another person name', async () => {
      await expect(
        as(f.ids.alice, (repo) =>
          repo.tickets.create({
            title: 'forged',
            priority: 'P2',
            assigneeId: f.ids.alice,
            raiserId: f.ids.bob,
            deadline: '2026-12-31',
          }),
        ),
      ).rejects.toBeInstanceOf(AuthorizationError);
    });

    it('lets anyone raise work for someone else', async () => {
      // Raising is open; controlling how it is done is not.
      const t = await createTicket(f.ids.manager, f.ids.alice);
      expect(t.assigneeId).toBe(f.ids.alice);
      expect(t.raiserId).toBe(f.ids.manager);
    });
  });

  // ===========================================================================
  describe('visibility', () => {
    it('shows an employee their own ticket', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice);
      const seen = await as(f.ids.alice, (repo) => repo.tickets.findById(t.id));
      expect(seen?.id).toBe(t.id);
    });

    it('hides a colleague ticket, indistinguishably from it not existing', async () => {
      const t = await createTicket(f.ids.bob, f.ids.bob);
      expect(await as(f.ids.alice, (repo) => repo.tickets.findById(t.id))).toBeNull();
    });

    it('hides it by reference too - the obvious way round a hidden id', async () => {
      const t = await createTicket(f.ids.bob, f.ids.bob);
      expect(await as(f.ids.alice, (repo) => repo.tickets.findByRef(t.ref))).toBeNull();
    });

    it('shows a manager their report ticket', async () => {
      const t = await createTicket(f.ids.bob, f.ids.bob);
      const seen = await as(f.ids.manager, (repo) => repo.tickets.findById(t.id));
      expect(seen?.id).toBe(t.id);
    });

    it('shows an admin everything', async () => {
      await createTicket(f.ids.alice, f.ids.alice);
      await createTicket(f.ids.bob, f.ids.bob);
      const all = await as<unknown[]>(f.ids.admin, (repo) => repo.tickets.list());
      expect(all.length).toBe(2);
    });

    it('shows an unrelated employee nothing', async () => {
      await createTicket(f.ids.alice, f.ids.alice);
      await createTicket(f.ids.bob, f.ids.bob);
      expect(await as(f.ids.outsider, (repo) => repo.tickets.list())).toEqual([]);
    });

    it('shows a watcher the one ticket they watch', async () => {
      const mine = await createTicket(f.ids.alice, f.ids.alice);
      const other = await createTicket(f.ids.bob, f.ids.bob);
      await f.addWatcher(other.id, f.ids.outsider);
      const seen = await as<{ id: string }[]>(f.ids.outsider, (repo) => repo.tickets.list());
      expect(seen.map((t) => t.id)).toEqual([other.id]);
      expect(seen.map((t) => t.id)).not.toContain(mine.id);
    });

    it('sorts a list by deadline, soonest first', async () => {
      await createTicket(f.ids.alice, f.ids.alice, '2026-12-31');
      await createTicket(f.ids.alice, f.ids.alice, '2026-09-01');
      const list = await as<{ deadline: string }[]>(f.ids.alice, (repo) => repo.tickets.list());
      expect(list.map((t) => t.deadline)).toEqual(['2026-09-01', '2026-12-31']);
    });

    it('filters by assignee', async () => {
      await createTicket(f.ids.manager, f.ids.alice);
      await createTicket(f.ids.manager, f.ids.bob);
      const mine = await as<{ assigneeId: string }[]>(f.ids.manager, (repo) =>
        repo.tickets.list({ assigneeId: f.ids.bob }),
      );
      expect(mine.length).toBe(1);
      expect(mine[0]!.assigneeId).toBe(f.ids.bob);
    });
  });

  // ===========================================================================
  describe('punching status', () => {
    it('records a punch and returns it in the ticket history', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice);
      const p = await as<{ id: string; status: string; note: string }>(f.ids.alice, (repo) =>
        repo.tickets.addPunch({
          ticketId: t.id,
          actorId: f.ids.alice,
          punchDate: '2026-08-03',
          status: 'IN_PROGRESS',
          note: 'drafting',
        }),
      );
      expect(p.status).toBe('IN_PROGRESS');
      const history = await as<{ id: string }[]>(f.ids.alice, (repo) =>
        repo.tickets.listPunches(t.id),
      );
      expect(history.map((x) => x.id)).toEqual([p.id]);
    });

    it('orders history chronologically', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice);
      await as(f.ids.alice, async (repo) => {
        await repo.tickets.addPunch({
          ticketId: t.id, actorId: f.ids.alice, punchDate: '2026-08-03',
          status: 'IN_PROGRESS', note: 'first',
        });
        await repo.tickets.addPunch({
          ticketId: t.id, actorId: f.ids.alice, punchDate: '2026-08-04',
          status: 'IN_PROGRESS', note: 'second',
        });
      });
      const history = await as<{ note: string }[]>(f.ids.alice, (repo) =>
        repo.tickets.listPunches(t.id),
      );
      expect(history.map((x) => x.note)).toEqual(['first', 'second']);
    });

    it('refuses a punch attributed to someone else', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice);
      await expect(
        as(f.ids.alice, (repo) =>
          repo.tickets.addPunch({
            ticketId: t.id, actorId: f.ids.bob, punchDate: '2026-08-03', status: 'IN_PROGRESS',
          }),
        ),
      ).rejects.toBeInstanceOf(AuthorizationError);
    });

    it('refuses a punch on a ticket you cannot see', async () => {
      const t = await createTicket(f.ids.bob, f.ids.bob);
      await expect(
        as(f.ids.alice, (repo) =>
          repo.tickets.addPunch({
            ticketId: t.id, actorId: f.ids.alice, punchDate: '2026-08-03', status: 'IN_PROGRESS',
          }),
        ),
      ).rejects.toBeInstanceOf(AuthorizationError);
    });

    it('requires a reason when reporting BLOCKED', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice);
      await expect(
        as(f.ids.alice, (repo) =>
          repo.tickets.addPunch({
            ticketId: t.id, actorId: f.ids.alice, punchDate: '2026-08-03',
            status: 'BLOCKED', note: 'stuck',
          }),
        ),
      ).rejects.toBeInstanceOf(ValidationError);
    });

    it('accepts BLOCKED with a reason', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice);
      const p = await as<{ blockedReason: string | null }>(f.ids.alice, (repo) =>
        repo.tickets.addPunch({
          ticketId: t.id, actorId: f.ids.alice, punchDate: '2026-08-03',
          status: 'BLOCKED', note: 'stuck', blockedReason: 'waiting on compliance',
        }),
      );
      expect(p.blockedReason).toBe('waiting on compliance');
    });

    it('rejects an impossible time-spent value', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice);
      await expect(
        as(f.ids.alice, (repo) =>
          repo.tickets.addPunch({
            ticketId: t.id, actorId: f.ids.alice, punchDate: '2026-08-03',
            status: 'IN_PROGRESS', minutesSpent: 5000,
          }),
        ),
      ).rejects.toBeInstanceOf(ValidationError);
    });

    it('returns no history for a ticket you cannot see', async () => {
      const t = await createTicket(f.ids.bob, f.ids.bob);
      await as(f.ids.bob, (repo) =>
        repo.tickets.addPunch({
          ticketId: t.id, actorId: f.ids.bob, punchDate: '2026-08-03',
          status: 'IN_PROGRESS', note: 'bob at work',
        }),
      );
      expect(await as(f.ids.alice, (repo) => repo.tickets.listPunches(t.id))).toEqual([]);
    });

    it('lets a manager punch on a report ticket', async () => {
      const t = await createTicket(f.ids.bob, f.ids.bob);
      const p = await as<{ actorId: string }>(f.ids.manager, (repo) =>
        repo.tickets.addPunch({
          ticketId: t.id, actorId: f.ids.manager, punchDate: '2026-08-03',
          status: 'IN_PROGRESS', note: 'picked this up',
        }),
      );
      expect(p.actorId).toBe(f.ids.manager);
    });
  });

  // ===========================================================================
  describe('mutating a ticket', () => {
    it('lets the assignee change status', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice);
      const u = await as<{ status: string }>(f.ids.alice, (repo) =>
        repo.tickets.setStatus({ ticketId: t.id, status: 'IN_PROGRESS' }),
      );
      expect(u.status).toBe('IN_PROGRESS');
    });

    it('refuses a status change from someone who cannot write the ticket', async () => {
      const t = await createTicket(f.ids.bob, f.ids.bob);
      await expect(
        as(f.ids.alice, (repo) =>
          repo.tickets.setStatus({ ticketId: t.id, status: 'IN_PROGRESS' }),
        ),
      ).rejects.toBeInstanceOf(AuthorizationError);
    });

    it('refuses a write from the raiser alone', async () => {
      // Raising work does not confer control over how it is done.
      const t = await createTicket(f.ids.outsider, f.ids.bob);
      await expect(
        as(f.ids.outsider, (repo) =>
          repo.tickets.setStatus({ ticketId: t.id, status: 'IN_PROGRESS' }),
        ),
      ).rejects.toBeInstanceOf(AuthorizationError);
    });

    it('records a closed date on a terminal status', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice);
      const u = await as<{ closedDate: string | null }>(f.ids.alice, (repo) =>
        repo.tickets.setStatus({ ticketId: t.id, status: 'DONE', closedDate: '2026-08-05' }),
      );
      expect(u.closedDate).toBe('2026-08-05');
    });

    it('reassigns', async () => {
      const t = await createTicket(f.ids.manager, f.ids.alice);
      const u = await as<{ assigneeId: string }>(f.ids.manager, (repo) =>
        repo.tickets.setAssignee(t.id, f.ids.bob),
      );
      expect(u.assigneeId).toBe(f.ids.bob);
    });

    it('moves the current deadline but never the original', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice, '2026-09-01');
      const u = await as<{ deadline: string; originalDeadline: string }>(f.ids.alice, (repo) =>
        repo.tickets.setDeadline(t.id, '2026-10-01'),
      );
      expect(u.deadline).toBe('2026-10-01');
      expect(u.originalDeadline).toBe('2026-09-01');
    });
  });

  // ===========================================================================
  describe('deadline changes', () => {
    it('records a request against the current deadline', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice, '2026-09-01');
      const c = await as<{ fromDate: string; toDate: string; decision: string }>(
        f.ids.alice,
        (repo) =>
          repo.tickets.requestDeadlineChange({
            ticketId: t.id,
            toDate: '2026-10-01',
            reason: 'upstream data is late',
          }),
      );
      expect(c.fromDate).toBe('2026-09-01');
      expect(c.toDate).toBe('2026-10-01');
      expect(c.decision).toBe('PENDING');
    });

    it('lists requests on a visible ticket', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice, '2026-09-01');
      await as(f.ids.alice, (repo) =>
        repo.tickets.requestDeadlineChange({
          ticketId: t.id, toDate: '2026-10-01', reason: 'late',
        }),
      );
      const list = await as<unknown[]>(f.ids.alice, (repo) =>
        repo.tickets.listDeadlineChanges(t.id),
      );
      expect(list.length).toBe(1);
    });

    it('lets the assignee manager approve', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice, '2026-09-01');
      const c = await as<{ id: string }>(f.ids.alice, (repo) =>
        repo.tickets.requestDeadlineChange({
          ticketId: t.id, toDate: '2026-10-01', reason: 'late',
        }),
      );
      const decided = await as<{ decision: string; approvedBy: string | null }>(
        f.ids.manager,
        (repo) => repo.tickets.decideDeadlineChange(c.id, 'APPROVED'),
      );
      expect(decided.decision).toBe('APPROVED');
      expect(decided.approvedBy).toBe(f.ids.manager);
    });

    it('refuses to let the requester approve their own request', async () => {
      // Self-approval would make the approval meaningless.
      const t = await createTicket(f.ids.alice, f.ids.alice, '2026-09-01');
      const c = await as<{ id: string }>(f.ids.alice, (repo) =>
        repo.tickets.requestDeadlineChange({
          ticketId: t.id, toDate: '2026-10-01', reason: 'late',
        }),
      );
      await expect(
        as(f.ids.alice, (repo) => repo.tickets.decideDeadlineChange(c.id, 'APPROVED')),
      ).rejects.toBeInstanceOf(AuthorizationError);
    });

    it('refuses to decide the same request twice', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice, '2026-09-01');
      const c = await as<{ id: string }>(f.ids.alice, (repo) =>
        repo.tickets.requestDeadlineChange({
          ticketId: t.id, toDate: '2026-10-01', reason: 'late',
        }),
      );
      await as(f.ids.manager, (repo) => repo.tickets.decideDeadlineChange(c.id, 'APPROVED'));
      await expect(
        as(f.ids.manager, (repo) => repo.tickets.decideDeadlineChange(c.id, 'REJECTED')),
      ).rejects.toBeInstanceOf(AuthorizationError);
    });

    it('refuses a request with no reason', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice, '2026-09-01');
      await expect(
        as(f.ids.alice, (repo) =>
          repo.tickets.requestDeadlineChange({ ticketId: t.id, toDate: '2026-10-01', reason: '  ' }),
        ),
      ).rejects.toBeInstanceOf(ValidationError);
    });

    it('refuses a request that does not move the date', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice, '2026-09-01');
      await expect(
        as(f.ids.alice, (repo) =>
          repo.tickets.requestDeadlineChange({
            ticketId: t.id, toDate: '2026-09-01', reason: 'no-op',
          }),
        ),
      ).rejects.toBeInstanceOf(ValidationError);
    });
  });

  // ===========================================================================
  describe('audit chain', () => {
    it('appends a verifiable chain', async () => {
      await as(f.ids.alice, async (repo) => {
        await repo.audit.append({
          action: 'TICKET_CREATED', entity: 'tickets', entityId: 'a', payload: { n: 1 },
        });
        await repo.audit.append({
          action: 'PUNCH_CREATED', entity: 'status_updates', entityId: 'b', payload: { n: 2 },
        });
      });
      const v = await as<{ ok: boolean; checked: number; headHashHex: string | null }>(
        f.ids.admin,
        (repo) => repo.audit.verify(),
      );
      expect(v.ok).toBe(true);
      expect(v.checked).toBe(2);
      expect(v.headHashHex).toMatch(/^[0-9a-f]{64}$/);
    });

    it('links each entry to its predecessor', async () => {
      const [one, two] = await as<{ prevHashHex: string; rowHashHex: string }[]>(
        f.ids.alice,
        async (repo) => [
          await repo.audit.append({
            action: 'A', entity: 'tickets', entityId: null, payload: {},
          }),
          await repo.audit.append({
            action: 'B', entity: 'tickets', entityId: null, payload: {},
          }),
        ],
      );
      expect(one!.prevHashHex).toBe('00'.repeat(32));
      expect(two!.prevHashHex).toBe(one!.rowHashHex);
    });

    it('attributes the entry to the acting employee, not a parameter', async () => {
      const r = await as<{ actorId: string | null }>(f.ids.bob, (repo) =>
        repo.audit.append({ action: 'A', entity: 'tickets', entityId: null, payload: {} }),
      );
      expect(r.actorId).toBe(f.ids.bob);
    });

    it('keeps the log admin-only', async () => {
      await as(f.ids.alice, (repo) =>
        repo.audit.append({ action: 'A', entity: 'tickets', entityId: null, payload: {} }),
      );
      expect(await as(f.ids.alice, (repo) => repo.audit.list())).toEqual([]);
      const asAdmin = await as<unknown[]>(f.ids.admin, (repo) => repo.audit.list());
      expect(asAdmin.length).toBe(1);
    });

    it('verifies an empty chain', async () => {
      const v = await as<{ ok: boolean; checked: number }>(f.ids.admin, (repo) =>
        repo.audit.verify(),
      );
      expect(v).toMatchObject({ ok: true, checked: 0 });
    });
  });

  // ===========================================================================
  describe('access events', () => {
    it('accepts a record from a signed-in employee', async () => {
      await as(f.ids.alice, (repo) =>
        repo.accessLog.record({ event: 'VIEW', entity: 'tickets', entityId: 'x' }),
      );
    });

    it('accepts a login event with no entity', async () => {
      await as(f.ids.alice, (repo) => repo.accessLog.record({ event: 'LOGIN' }));
    });
  });

  // ===========================================================================
  describe('summaries for list views', () => {
    it('reports no punches for a fresh ticket', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice);
      const s = await as(f.ids.alice, (repo) => repo.tickets.listSummaries());
      expect(s.length).toBe(1);
      expect(s[0]).toMatchObject({ lastPunchDate: null, lastPunchBy: null, punchCount: 0 });
      expect(s[0]!.ticket.id).toBe(t.id);
    });

    it('reports the latest punch date and its author', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice);
      await as(f.ids.alice, async (repo) => {
        await repo.tickets.addPunch({
          ticketId: t.id, actorId: f.ids.alice, punchDate: '2026-08-03',
          status: 'IN_PROGRESS', note: 'one',
        });
        await repo.tickets.addPunch({
          ticketId: t.id, actorId: f.ids.alice, punchDate: '2026-08-06',
          status: 'IN_PROGRESS', note: 'two',
        });
      });
      const s = await as(f.ids.alice, (repo) => repo.tickets.listSummaries());
      expect(s[0]).toMatchObject({
        lastPunchDate: '2026-08-06',
        lastPunchBy: f.ids.alice,
        punchCount: 2,
      });
    });

    it('takes the latest DATE, not the latest row - backdating must not win', async () => {
      const t = await createTicket(f.ids.alice, f.ids.alice);
      await as(f.ids.alice, async (repo) => {
        await repo.tickets.addPunch({
          ticketId: t.id, actorId: f.ids.alice, punchDate: '2026-08-06',
          status: 'IN_PROGRESS', note: 'recent',
        });
        // Written second, but dated earlier.
        await repo.tickets.addPunch({
          ticketId: t.id, actorId: f.ids.alice, punchDate: '2026-08-01',
          status: 'IN_PROGRESS', note: 'backdated',
        });
      });
      const s = await as(f.ids.alice, (repo) => repo.tickets.listSummaries());
      expect(s[0]!.lastPunchDate).toBe('2026-08-06');
    });

    it('honours visibility exactly as list does', async () => {
      await createTicket(f.ids.alice, f.ids.alice);
      await createTicket(f.ids.bob, f.ids.bob);
      const mine = await as(f.ids.alice, (repo) => repo.tickets.listSummaries());
      const all = await as(f.ids.admin, (repo) => repo.tickets.listSummaries());
      expect(mine.length).toBe(1);
      expect(all.length).toBe(2);
      expect(await as(f.ids.outsider, (repo) => repo.tickets.listSummaries())).toEqual([]);
    });

    it('applies the same filters as list', async () => {
      await createTicket(f.ids.manager, f.ids.alice);
      await createTicket(f.ids.manager, f.ids.bob);
      const s = await as(f.ids.manager, (repo) =>
        repo.tickets.listSummaries({ assigneeId: f.ids.bob }),
      );
      expect(s.length).toBe(1);
      expect(s[0]!.ticket.assigneeId).toBe(f.ids.bob);
    });

    it('orders by deadline like list', async () => {
      await createTicket(f.ids.alice, f.ids.alice, '2026-12-31');
      await createTicket(f.ids.alice, f.ids.alice, '2026-09-01');
      const s = await as(f.ids.alice, (repo) => repo.tickets.listSummaries());
      expect(s.map((x) => x.ticket.deadline)).toEqual(['2026-09-01', '2026-12-31']);
    });
  });

  // ===========================================================================
  describe('reference data', () => {
    it('lists active categories alphabetically', async () => {
      const cats = await as(f.ids.alice, (repo) => repo.reference.categories());
      expect(cats.map((c) => c.name)).toEqual(
        [...CATEGORIES].sort((a, b) => a.localeCompare(b)),
      );
      expect(cats.every((c) => c.active)).toBe(true);
    });

    it('lets an admin add a category, and it becomes selectable', async () => {
      const name = `Custody ${nextUnique()}`;
      const made = await as(f.ids.admin, (repo) => repo.reference.createCategory(name));
      expect(made).toMatchObject({ name, active: true });
      const cats = await as(f.ids.alice, (repo) => repo.reference.categories());
      expect(cats.map((c) => c.name)).toContain(name);
    });

    it('refuses a duplicate category name', async () => {
      await expect(
        as(f.ids.admin, (repo) => repo.reference.createCategory(CATEGORIES[0])),
      ).rejects.toBeInstanceOf(ValidationError);
    });

    it('refuses a category from a non-admin', async () => {
      await expect(
        as(f.ids.manager, (repo) => repo.reference.createCategory('Manager idea')),
      ).rejects.toBeInstanceOf(AuthorizationError);
    });

    it('retires a category from pickers but keeps it visible to the console', async () => {
      // Otherwise retiring one would be irreversible: the row would vanish from
      // every list that could supply its id.
      const name = `Retired ${nextUnique()}`;
      const made = await as(f.ids.admin, (repo) => repo.reference.createCategory(name));
      await as(f.ids.admin, (repo) => repo.reference.setCategoryActive(made.id, false));

      const pickable = await as(f.ids.alice, (repo) => repo.reference.categories());
      expect(pickable.map((c) => c.id)).not.toContain(made.id);

      const all = await as(f.ids.admin, (repo) => repo.reference.allCategories());
      expect(all.find((c) => c.id === made.id)).toMatchObject({ name, active: false });

      const restored = await as(f.ids.admin, (repo) =>
        repo.reference.setCategoryActive(made.id, true),
      );
      expect(restored.active).toBe(true);
    });
  });

  // ===========================================================================
  describe('calendar', () => {
    it('returns the seeded holidays for injection into date maths', async () => {
      const h = await as<ReadonlySet<string>>(f.ids.alice, (repo) => repo.calendar.holidays());
      expect(h.has(HOLIDAY)).toBe(true);
      expect(h.has('2026-08-13')).toBe(false);
    });

    it('lists holidays with their names, earliest first', async () => {
      // Asserted as "contains, and is sorted" rather than an exact list: holidays
      // survive reset(), so a test that demanded an exact set would depend on the
      // order tests happen to run in.
      await as(f.ids.admin, (repo) => repo.calendar.addHoliday('2026-01-26', 'Republic Day'));
      const list = await as(f.ids.alice, (repo) => repo.calendar.listHolidays());
      expect(list.find((h) => h.date === '2026-01-26')?.name).toBe('Republic Day');
      expect(list.find((h) => h.date === HOLIDAY)?.name).toBe(HOLIDAY_NAME);
      const dates = list.map((h) => h.date);
      expect(dates).toEqual([...dates].sort());
      await as(f.ids.admin, (repo) => repo.calendar.removeHoliday('2026-01-26'));
    });

    it('feeds a newly added holiday into the set the date maths reads', async () => {
      // The point of the port: a day the admin blocks out must actually change
      // working-day arithmetic, not just appear in a list.
      await as(f.ids.admin, (repo) => repo.calendar.addHoliday('2026-10-02', 'Gandhi Jayanti'));
      const h = await as<ReadonlySet<string>>(f.ids.alice, (repo) => repo.calendar.holidays());
      expect(h.has('2026-10-02')).toBe(true);
      await as(f.ids.admin, (repo) => repo.calendar.removeHoliday('2026-10-02'));
      const after = await as<ReadonlySet<string>>(f.ids.alice, (repo) => repo.calendar.holidays());
      expect(after.has('2026-10-02')).toBe(false);
    });

    it('refuses a duplicate holiday date', async () => {
      await expect(
        as(f.ids.admin, (repo) => repo.calendar.addHoliday(HOLIDAY, 'Duplicate')),
      ).rejects.toBeInstanceOf(ValidationError);
    });

    it('refuses a holiday from a non-admin, in both directions', async () => {
      await expect(
        as(f.ids.manager, (repo) => repo.calendar.addHoliday('2026-11-11', 'Manager day off')),
      ).rejects.toBeInstanceOf(AuthorizationError);
      await expect(
        as(f.ids.manager, (repo) => repo.calendar.removeHoliday(HOLIDAY)),
      ).rejects.toBeInstanceOf(AuthorizationError);
      const h = await as<ReadonlySet<string>>(f.ids.alice, (repo) => repo.calendar.holidays());
      expect(h.has(HOLIDAY)).toBe(true);
    });

    it('refuses to remove a date that is not a holiday', async () => {
      await expect(
        as(f.ids.admin, (repo) => repo.calendar.removeHoliday('2026-03-03')),
      ).rejects.toBeInstanceOf(AuthorizationError);
    });
  });

  // ===========================================================================
  describe('people administration', () => {
    const joiner = (actor: Uuid) =>
      as(actor, (repo) =>
        repo.employees.create({ ...nextJoiner(), role: 'EMPLOYEE', managerId: null }),
      );

    it('adds someone to the allow-list, active, with the email folded to lowercase', async () => {
      const email = nextJoiner().workEmail.toUpperCase();
      const made = await as(f.ids.admin, (repo) =>
        repo.employees.create({
          workEmail: `  ${email} `,
          displayName: 'New Joiner',
          role: 'EMPLOYEE',
          managerId: f.ids.manager,
        }),
      );
      expect(made.workEmail).toBe(email.toLowerCase());
      expect(made.status).toBe('ACTIVE');
      expect(made.managerId).toBe(f.ids.manager);
      // The allow-list IS the login path: resolveIdentity must now find them.
      expect((await f.factory.resolveIdentity(email))?.id).toBe(made.id);
    });

    it('refuses a duplicate work email, case-insensitively', async () => {
      await expect(
        as(f.ids.admin, (repo) =>
          repo.employees.create({
            workEmail: EMAILS.alice.toUpperCase(),
            displayName: 'Impostor',
            role: 'EMPLOYEE',
            managerId: null,
          }),
        ),
      ).rejects.toBeInstanceOf(ValidationError);
    });

    it('refuses to add anyone at all from a non-admin', async () => {
      await expect(joiner(f.ids.manager)).rejects.toBeInstanceOf(AuthorizationError);
      await expect(joiner(f.ids.alice)).rejects.toBeInstanceOf(AuthorizationError);
    });

    it('changes a role, but never the actor own role', async () => {
      const j = await joiner(f.ids.admin);
      const promoted = await as(f.ids.admin, (repo) =>
        repo.employees.setRole(j.id, 'MANAGER'),
      );
      expect(promoted.role).toBe('MANAGER');

      await expect(
        as(f.ids.admin, (repo) => repo.employees.setRole(f.ids.admin, 'EMPLOYEE')),
      ).rejects.toBeInstanceOf(AuthorizationError);
      const me = await as(f.ids.admin, (repo) => repo.employees.findById(f.ids.admin));
      expect(me?.role).toBe('ADMIN');
    });

    it('refuses a role change from a non-admin, including a self-promotion', async () => {
      await expect(
        as(f.ids.alice, (repo) => repo.employees.setRole(f.ids.alice, 'ADMIN')),
      ).rejects.toBeInstanceOf(AuthorizationError);
      await expect(
        as(f.ids.manager, (repo) => repo.employees.setRole(f.ids.bob, 'ADMIN')),
      ).rejects.toBeInstanceOf(AuthorizationError);
      const alice = await as(f.ids.alice, (repo) => repo.employees.findById(f.ids.alice));
      expect(alice?.role).toBe('EMPLOYEE');
    });

    it('sets and clears a manager', async () => {
      const j = await joiner(f.ids.admin);
      const linked = await as(f.ids.admin, (repo) =>
        repo.employees.setManager(j.id, f.ids.manager),
      );
      expect(linked.managerId).toBe(f.ids.manager);
      const cleared = await as(f.ids.admin, (repo) => repo.employees.setManager(j.id, null));
      expect(cleared.managerId).toBeNull();
    });

    it('refuses self-management', async () => {
      const j = await joiner(f.ids.admin);
      await expect(
        as(f.ids.admin, (repo) => repo.employees.setManager(j.id, j.id)),
      ).rejects.toBeInstanceOf(ValidationError);
    });

    it('refuses a two-step management cycle', async () => {
      const a = await joiner(f.ids.admin);
      const b = await joiner(f.ids.admin);
      await as(f.ids.admin, (repo) => repo.employees.setManager(b.id, a.id));
      await expect(
        as(f.ids.admin, (repo) => repo.employees.setManager(a.id, b.id)),
      ).rejects.toBeInstanceOf(ValidationError);
      // And the refused edge left nothing behind.
      const stillA = await as(f.ids.admin, (repo) => repo.employees.findById(a.id));
      expect(stillA?.managerId).toBeNull();
    });

    it('refuses an unknown manager', async () => {
      const j = await joiner(f.ids.admin);
      await expect(
        as(f.ids.admin, (repo) =>
          repo.employees.setManager(j.id, '00000000-0000-4000-8000-000000000000'),
        ),
      ).rejects.toBeInstanceOf(ValidationError);
    });

    it('refuses a deactivation with no reason', async () => {
      const j = await joiner(f.ids.admin);
      await expect(
        as(f.ids.admin, (repo) => repo.employees.deactivate(j.id, '   ')),
      ).rejects.toBeInstanceOf(ValidationError);
      const still = await as(f.ids.admin, (repo) => repo.employees.findById(j.id));
      expect(still?.status).toBe('ACTIVE');
    });

    it('refuses a deactivation while open work is still assigned, and allows it after handover', async () => {
      const j = await joiner(f.ids.admin);
      const t = await as(f.ids.admin, (repo) =>
        repo.tickets.create({
          title: 'Half-finished migration',
          priority: 'P2',
          assigneeId: j.id,
          raiserId: f.ids.admin,
          deadline: '2026-12-31',
        }),
      );

      await expect(
        as(f.ids.admin, (repo) => repo.employees.deactivate(j.id, 'left the firm')),
      ).rejects.toBeInstanceOf(ValidationError);

      await as(f.ids.admin, (repo) => repo.tickets.setAssignee(t.id, f.ids.alice));

      const gone = await as(f.ids.admin, (repo) =>
        repo.employees.deactivate(j.id, 'left the firm'),
      );
      expect(gone.status).toBe('DEACTIVATED');
    });

    it('counts only non-terminal work as blocking a deactivation', async () => {
      const j = await joiner(f.ids.admin);
      const t = await as(f.ids.admin, (repo) =>
        repo.tickets.create({
          title: 'Finished work',
          priority: 'P3',
          assigneeId: j.id,
          raiserId: f.ids.admin,
          deadline: '2026-12-31',
        }),
      );
      await as(f.ids.admin, (repo) =>
        repo.tickets.setStatus({ ticketId: t.id, status: 'DONE', closedDate: '2026-08-03' }),
      );
      const gone = await as(f.ids.admin, (repo) => repo.employees.deactivate(j.id, 'retired'));
      expect(gone.status).toBe('DEACTIVATED');
    });

    it('never removes the person: the row and their punches survive deactivation', async () => {
      const j = await joiner(f.ids.admin);
      const t = await as(f.ids.admin, (repo) =>
        repo.tickets.create({
          title: 'Work with a history',
          priority: 'P2',
          assigneeId: j.id,
          raiserId: f.ids.admin,
          deadline: '2026-12-31',
        }),
      );
      await as(j.id, (repo) =>
        repo.tickets.addPunch({
          ticketId: t.id,
          actorId: j.id,
          punchDate: '2026-08-03',
          status: 'IN_PROGRESS',
          note: 'started before leaving',
        }),
      );
      await as(f.ids.admin, (repo) =>
        repo.tickets.setStatus({ ticketId: t.id, status: 'DONE', closedDate: '2026-08-04' }),
      );
      await as(f.ids.admin, (repo) => repo.employees.deactivate(j.id, 'left the firm'));

      const row = await as(f.ids.admin, (repo) => repo.employees.findById(j.id));
      expect(row).toMatchObject({ id: j.id, status: 'DEACTIVATED', displayName: j.displayName });

      const history = await as(f.ids.admin, (repo) => repo.tickets.listPunches(t.id));
      expect(history.map((p) => p.actorId)).toEqual([j.id]);
    });

    it('shows deactivated accounts to listAll and hides them from listActive', async () => {
      const j = await joiner(f.ids.admin);
      await as(f.ids.admin, (repo) => repo.employees.deactivate(j.id, 'contract ended'));

      const all = await as(f.ids.admin, (repo) => repo.employees.listAll());
      const active = await as(f.ids.admin, (repo) => repo.employees.listActive());
      expect(all.map((e) => e.id)).toContain(j.id);
      expect(active.map((e) => e.id)).not.toContain(j.id);
      expect(all.length).toBeGreaterThan(active.length);
    });

    it('locks a deactivated person out of the login path immediately', async () => {
      const j = await joiner(f.ids.admin);
      expect(await f.factory.resolveIdentity(j.workEmail)).not.toBeNull();
      await as(f.ids.admin, (repo) => repo.employees.deactivate(j.id, 'offboarded'));
      expect(await f.factory.resolveIdentity(j.workEmail)).toBeNull();
    });

    it('gives one indistinguishable refusal for an id that does not exist', async () => {
      const missing = '00000000-0000-4000-8000-000000000000';
      await expect(
        as(f.ids.admin, (repo) => repo.employees.setRole(missing, 'MANAGER')),
      ).rejects.toBeInstanceOf(AuthorizationError);
      await expect(
        as(f.ids.admin, (repo) => repo.employees.deactivate(missing, 'never existed')),
      ).rejects.toBeInstanceOf(AuthorizationError);
    });
  });

  // ===========================================================================
  describe('access events for the review', () => {
    it('returns one person events newest first, to an admin only', async () => {
      await as(f.ids.alice, async (repo) => {
        await repo.accessLog.record({ event: 'LOGIN' });
        await repo.accessLog.record({ event: 'VIEW', entity: 'tickets', entityId: 'x' });
      });

      const asAdmin = await as(f.ids.admin, (repo) => repo.accessLog.recentFor(f.ids.alice));
      expect(asAdmin.map((e) => e.event)).toEqual(['VIEW', 'LOGIN']);
      expect(asAdmin.every((e) => e.employeeId === f.ids.alice)).toBe(true);

      // A colleague cannot audit a colleague, not even themselves.
      expect(await as(f.ids.manager, (repo) => repo.accessLog.recentFor(f.ids.alice))).toEqual([]);
      expect(await as(f.ids.alice, (repo) => repo.accessLog.recentFor(f.ids.alice))).toEqual([]);
    });

    it('honours the limit', async () => {
      await as(f.ids.alice, async (repo) => {
        await repo.accessLog.record({ event: 'LOGIN' });
        await repo.accessLog.record({ event: 'VIEW' });
        await repo.accessLog.record({ event: 'LIST' });
      });
      const two = await as(f.ids.admin, (repo) => repo.accessLog.recentFor(f.ids.alice, 2));
      expect(two.length).toBe(2);
      expect(two[0]!.event).toBe('LIST');
    });

    it('reports the last login as the timestamp of a LOGIN event', async () => {
      await as(f.ids.bob, (repo) => repo.accessLog.record({ event: 'LOGIN' }));
      const [login] = await as(f.ids.admin, (repo) => repo.accessLog.recentFor(f.ids.bob));
      const last = await as(f.ids.admin, (repo) => repo.accessLog.lastLoginAt(f.ids.bob));
      expect(login!.event).toBe('LOGIN');
      expect(last).toBe(login!.occurredAt);
    });

    it('reports no last login when the account has only been read from', async () => {
      // The distinction that makes the review worth running: activity is not a login.
      await as(f.ids.bob, (repo) => repo.accessLog.record({ event: 'VIEW', entity: 'tickets' }));
      expect(await as(f.ids.admin, (repo) => repo.accessLog.lastLoginAt(f.ids.bob))).toBeNull();
    });

    it('reports no last login for an account that has never been seen', async () => {
      expect(await as(f.ids.admin, (repo) => repo.accessLog.lastLoginAt(f.ids.outsider))).toBeNull();
    });

    it('tells a non-admin nothing about anyone last login', async () => {
      await as(f.ids.bob, (repo) => repo.accessLog.record({ event: 'LOGIN' }));
      expect(await as(f.ids.manager, (repo) => repo.accessLog.lastLoginAt(f.ids.bob))).toBeNull();
    });
  });
});
