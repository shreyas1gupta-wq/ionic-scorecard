/**
 * Administration rules, run against BOTH repository implementations.
 *
 * The contract suite proves the two stores refuse the same things. This suite
 * proves the service layer on top of them does the two things it exists for:
 * every administrative action is gated on a role read from the store, and every
 * one of them leaves an entry in the hash chain. A refused action must leave
 * nothing at all — a chain that records attempts as though they succeeded is
 * worse than no chain.
 */

import { describe, it, expect, beforeAll, beforeEach, afterAll } from 'vitest';
import { EMAILS, HOLIDAY, IMPLEMENTATIONS, type Fixture } from '../repo/fixtures';
import { AuthorizationError, ValidationError, type Repository, type Uuid } from '../repo/types';
import { istDateOf } from '../domain/calendar';
import {
  DORMANT_AFTER_DAYS,
  addCategory,
  addEmployee,
  addHoliday,
  buildAccessReview,
  deactivateEmployee,
  isDormant,
  readAuditLog,
  recordAccessReview,
  removeHoliday,
  setCategoryActive,
  setEmployeeManager,
  setEmployeeRole,
} from './admin';

/**
 * Unique per call: `reset()` keeps the team between tests, because the schema
 * offers no way to delete an employee and inventing one for test convenience
 * would be inventing one an attacker could use.
 */
let unique = 0;
const nextJoiner = () => {
  const n = (unique += 1);
  return { workEmail: `admintest${n}@ionic.in`, displayName: `Admin Test ${n}` };
};

// =============================================================================
// The dormancy rule is pure, so it is tested directly rather than through a store.
// =============================================================================
describe('dormancy', () => {
  const TODAY = '2026-08-03';

  const daysBefore = (n: number): string => {
    const ms = Date.parse(`${TODAY}T00:00:00+05:30`) - n * 86_400_000;
    return new Date(ms).toISOString();
  };

  it('flags an account that has never signed in', () => {
    expect(isDormant(null, TODAY)).toBe(true);
  });

  it('does not flag an account used yesterday', () => {
    expect(isDormant(daysBefore(1), TODAY)).toBe(false);
  });

  it('does not flag an account used exactly on the threshold', () => {
    expect(isDormant(daysBefore(DORMANT_AFTER_DAYS), TODAY)).toBe(false);
  });

  it('flags an account one day past the threshold', () => {
    expect(isDormant(daysBefore(DORMANT_AFTER_DAYS + 1), TODAY)).toBe(true);
  });

  it('reads the login instant as an IST date, not a UTC one', () => {
    // 18:30 UTC is midnight IST, so a login at 18:31 UTC on 5 May happened on
    // 6 May in IST. Reading the UTC date instead would age the account by a day.
    const justAfterIstMidnight = '2026-05-05T18:31:00.000Z';
    expect(istDateOf(new Date(justAfterIstMidnight))).toBe('2026-05-06');

    // Chosen so the two readings disagree: 90 days before 2026-08-04 is
    // 2026-05-06. The IST date lands exactly on the threshold (not dormant); the
    // UTC date would land a day before it (dormant). This assertion fails if
    // anyone reverts to `instant.slice(0, 10)`.
    expect(isDormant(justAfterIstMidnight, '2026-08-04')).toBe(false);
    expect(isDormant(justAfterIstMidnight, '2026-08-05')).toBe(true);
  });
});

// =============================================================================
describe.each(IMPLEMENTATIONS)('admin service: %s', (_name, build) => {
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

  const as = <T>(actor: Uuid, fn: (repo: Repository) => Promise<T>): Promise<T> =>
    f.factory.withActor({ employeeId: actor }, fn);

  const auditLog = () => as(f.ids.admin, (repo) => repo.audit.list());

  const joiner = () =>
    as(f.ids.admin, (repo) =>
      addEmployee(repo, { ...nextJoiner(), role: 'EMPLOYEE', managerId: null }),
    );

  // ===========================================================================
  describe('the role gate', () => {
    it('refuses every administrative action to a manager', async () => {
      const attempts: ((repo: Repository) => Promise<unknown>)[] = [
        (repo) => addEmployee(repo, { ...nextJoiner(), role: 'EMPLOYEE', managerId: null }),
        (repo) => setEmployeeRole(repo, f.ids.alice, 'MANAGER'),
        (repo) => setEmployeeManager(repo, f.ids.alice, null),
        (repo) => deactivateEmployee(repo, f.ids.alice, 'because'),
        (repo) => addHoliday(repo, '2026-12-25', 'Christmas'),
        (repo) => removeHoliday(repo, HOLIDAY),
        (repo) => addCategory(repo, 'Manager idea'),
        (repo) => buildAccessReview(repo),
        (repo) => recordAccessReview(repo),
        (repo) => readAuditLog(repo),
      ];
      for (const attempt of attempts) {
        await expect(as(f.ids.manager, attempt)).rejects.toBeInstanceOf(AuthorizationError);
      }
      // And nothing was recorded as having happened.
      expect(await auditLog()).toEqual([]);
    });

    it('refuses an employee who claims nothing and simply asks', async () => {
      await expect(
        as(f.ids.alice, (repo) => setEmployeeRole(repo, f.ids.bob, 'ADMIN')),
      ).rejects.toBeInstanceOf(AuthorizationError);
    });

    it('refuses a deactivated administrator', async () => {
      // The role is read from the store on every call, so offboarding an admin
      // takes effect immediately — there is no cached claim to expire.
      const j = await joiner();
      await as(f.ids.admin, (repo) => setEmployeeRole(repo, j.id, 'ADMIN'));
      await as(f.ids.admin, (repo) => deactivateEmployee(repo, j.id, 'left the firm'));

      await expect(
        as(j.id, (repo) => addCategory(repo, 'Ex-admin idea')),
      ).rejects.toBeInstanceOf(AuthorizationError);
    });
  });

  // ===========================================================================
  describe('adding people', () => {
    it('creates the account and audits the role it was granted', async () => {
      const details = nextJoiner();
      const created = await as(f.ids.admin, (repo) =>
        addEmployee(repo, { ...details, role: 'MANAGER', managerId: f.ids.admin }),
      );
      expect(created.workEmail).toBe(details.workEmail);
      expect(created.status).toBe('ACTIVE');

      const entry = (await auditLog()).find((e) => e.entityId === created.id);
      expect(entry?.action).toBe('EMPLOYEE_CREATED');
      expect(entry?.actorId).toBe(f.ids.admin);
      expect(entry?.payload).toMatchObject({
        workEmail: details.workEmail,
        role: 'MANAGER',
        managerId: f.ids.admin,
      });
    });

    it('refuses a duplicate work email whatever the casing, and records nothing', async () => {
      await expect(
        as(f.ids.admin, (repo) =>
          addEmployee(repo, {
            workEmail: EMAILS.bob.toUpperCase(),
            displayName: 'Second Bob',
            role: 'EMPLOYEE',
            managerId: null,
          }),
        ),
      ).rejects.toBeInstanceOf(ValidationError);
      expect(await auditLog()).toEqual([]);
    });

    it('refuses a blank display name', async () => {
      await expect(
        as(f.ids.admin, (repo) =>
          addEmployee(repo, {
            workEmail: nextJoiner().workEmail,
            displayName: '   ',
            role: 'EMPLOYEE',
            managerId: null,
          }),
        ),
      ).rejects.toBeInstanceOf(ValidationError);
    });
  });

  // ===========================================================================
  describe('roles', () => {
    it('records what the role was, not only what it became', async () => {
      const j = await joiner();
      await as(f.ids.admin, (repo) => setEmployeeRole(repo, j.id, 'MANAGER'));

      const entry = (await auditLog()).find((e) => e.action === 'EMPLOYEE_ROLE_CHANGED');
      expect(entry?.payload).toMatchObject({
        workEmail: j.workEmail,
        from: 'EMPLOYEE',
        to: 'MANAGER',
      });
    });

    it('refuses to let an administrator change their own role, and leaves no trace', async () => {
      // Privilege escalation is the one authorisation bug an admin console can
      // introduce that matters: without this, "demote yourself to test something"
      // and "promote yourself" are the same code path.
      await expect(
        as(f.ids.admin, (repo) => setEmployeeRole(repo, f.ids.admin, 'EMPLOYEE')),
      ).rejects.toBeInstanceOf(AuthorizationError);

      const me = await as(f.ids.admin, (repo) => repo.employees.findById(f.ids.admin));
      expect(me?.role).toBe('ADMIN');
      expect(await auditLog()).toEqual([]);
    });

    it('refuses the actor own role while allowing the same call on someone else', async () => {
      // The discriminating pair. One actor, two targets, one call: proof that the
      // refusal is about being oneself, not about lacking the privilege.
      const second = await joiner();
      await as(f.ids.admin, (repo) => setEmployeeRole(repo, second.id, 'ADMIN'));
      const target = await joiner();

      await expect(
        as(second.id, (repo) => setEmployeeRole(repo, second.id, 'EMPLOYEE')),
      ).rejects.toBeInstanceOf(AuthorizationError);

      const changed = await as(second.id, (repo) => setEmployeeRole(repo, target.id, 'MANAGER'));
      expect(changed.role).toBe('MANAGER');
    });
  });

  // ===========================================================================
  describe('reporting lines', () => {
    it('sets a manager and audits both ends of the change', async () => {
      const j = await joiner();
      await as(f.ids.admin, (repo) => setEmployeeManager(repo, j.id, f.ids.manager));
      const entry = (await auditLog()).find((e) => e.action === 'EMPLOYEE_MANAGER_CHANGED');
      expect(entry?.payload).toMatchObject({ from: null, to: f.ids.manager });
    });

    it('refuses self-management', async () => {
      const j = await joiner();
      await expect(
        as(f.ids.admin, (repo) => setEmployeeManager(repo, j.id, j.id)),
      ).rejects.toBeInstanceOf(ValidationError);
    });

    it('refuses a cycle, so the reporting chain always terminates', async () => {
      // app.manages() is used by row-level security. A cycle would make
      // visibility circular and "who approves this" unanswerable.
      const a = await joiner();
      const b = await joiner();
      await as(f.ids.admin, (repo) => setEmployeeManager(repo, b.id, a.id));
      await expect(
        as(f.ids.admin, (repo) => setEmployeeManager(repo, a.id, b.id)),
      ).rejects.toBeInstanceOf(ValidationError);

      const stillA = await as(f.ids.admin, (repo) => repo.employees.findById(a.id));
      expect(stillA?.managerId).toBeNull();
    });
  });

  // ===========================================================================
  describe('deactivation', () => {
    const assign = (to: Uuid) =>
      as(f.ids.admin, (repo) =>
        repo.tickets.create({
          title: 'Unfinished business',
          priority: 'P2',
          assigneeId: to,
          raiserId: f.ids.admin,
          deadline: '2026-12-31',
        }),
      );

    it('requires a reason', async () => {
      const j = await joiner();
      await expect(
        as(f.ids.admin, (repo) => deactivateEmployee(repo, j.id, '  ')),
      ).rejects.toBeInstanceOf(ValidationError);
      const still = await as(f.ids.admin, (repo) => repo.employees.findById(j.id));
      expect(still?.status).toBe('ACTIVE');
    });

    it('refuses while the person still holds open work', async () => {
      const j = await joiner();
      await assign(j.id);
      await expect(
        as(f.ids.admin, (repo) => deactivateEmployee(repo, j.id, 'resigned')),
      ).rejects.toBeInstanceOf(ValidationError);
      const still = await as(f.ids.admin, (repo) => repo.employees.findById(j.id));
      expect(still?.status).toBe('ACTIVE');
    });

    it('goes through once the work has been reassigned', async () => {
      const j = await joiner();
      const t = await assign(j.id);
      await as(f.ids.admin, (repo) => repo.tickets.setAssignee(t.id, f.ids.alice));

      const gone = await as(f.ids.admin, (repo) => deactivateEmployee(repo, j.id, 'resigned'));
      expect(gone.status).toBe('DEACTIVATED');

      const entry = (await auditLog()).find((e) => e.action === 'EMPLOYEE_DEACTIVATED');
      expect(entry?.payload).toMatchObject({ workEmail: j.workEmail, reason: 'resigned' });
    });

    it('keeps the person and their work history', async () => {
      const j = await joiner();
      const t = await assign(j.id);
      await as(j.id, (repo) =>
        repo.tickets.addPunch({
          ticketId: t.id,
          actorId: j.id,
          punchDate: istDateOf(new Date()),
          status: 'IN_PROGRESS',
          note: 'got this far',
        }),
      );
      await as(f.ids.admin, (repo) => repo.tickets.setAssignee(t.id, f.ids.alice));
      await as(f.ids.admin, (repo) => deactivateEmployee(repo, j.id, 'resigned'));

      const row = await as(f.ids.admin, (repo) => repo.employees.findById(j.id));
      expect(row).toMatchObject({ id: j.id, status: 'DEACTIVATED' });

      const punches = await as(f.ids.admin, (repo) => repo.tickets.listPunches(t.id));
      expect(punches.some((p) => p.actorId === j.id && p.note === 'got this far')).toBe(true);
    });

    it('refuses a second deactivation, so the chain cannot say it happened twice', async () => {
      const j = await joiner();
      await as(f.ids.admin, (repo) => deactivateEmployee(repo, j.id, 'resigned'));
      await expect(
        as(f.ids.admin, (repo) => deactivateEmployee(repo, j.id, 'resigned again')),
      ).rejects.toBeInstanceOf(ValidationError);
      expect(
        (await auditLog()).filter((e) => e.action === 'EMPLOYEE_DEACTIVATED').length,
      ).toBe(1);
    });
  });

  // ===========================================================================
  describe('calendar and categories', () => {
    it('audits a holiday, because adding one changes whether past work was late', async () => {
      await as(f.ids.admin, (repo) => addHoliday(repo, '2026-12-25', 'Christmas'));
      const added = (await auditLog()).find((e) => e.action === 'HOLIDAY_ADDED');
      expect(added?.payload).toMatchObject({ date: '2026-12-25', name: 'Christmas' });

      await as(f.ids.admin, (repo) => removeHoliday(repo, '2026-12-25'));
      const removed = (await auditLog()).find((e) => e.action === 'HOLIDAY_REMOVED');
      expect(removed?.payload).toMatchObject({ date: '2026-12-25' });

      const holidays = await as<ReadonlySet<string>>(f.ids.alice, (repo) =>
        repo.calendar.holidays(),
      );
      expect(holidays.has('2026-12-25')).toBe(false);
    });

    it('refuses a holiday with no name, and records nothing', async () => {
      await expect(
        as(f.ids.admin, (repo) => addHoliday(repo, '2026-12-26', ' ')),
      ).rejects.toBeInstanceOf(ValidationError);
      expect(await auditLog()).toEqual([]);
    });

    it('audits retiring and restoring a category', async () => {
      const name = `Audited ${nextJoiner().displayName}`;
      const cat = await as(f.ids.admin, (repo) => addCategory(repo, name));
      await as(f.ids.admin, (repo) => setCategoryActive(repo, cat.id, false));
      const off = (await auditLog()).find((e) => e.action === 'CATEGORY_ACTIVE_CHANGED');
      expect(off?.payload).toMatchObject({ name: cat.name, active: false });

      const back = await as(f.ids.admin, (repo) => setCategoryActive(repo, cat.id, true));
      expect(back.active).toBe(true);
    });
  });

  // ===========================================================================
  describe('the half-yearly access review', () => {
    it('covers every account, deactivated ones included, and names the manager', async () => {
      const j = await joiner();
      await as(f.ids.admin, (repo) => setEmployeeManager(repo, j.id, f.ids.manager));
      await as(f.ids.admin, (repo) => deactivateEmployee(repo, j.id, 'contract ended'));

      const review = await as(f.ids.admin, (repo) => buildAccessReview(repo));
      const row = review.accounts.find((a) => a.employee.id === j.id);
      expect(row?.employee.status).toBe('DEACTIVATED');
      expect(row?.managerName).toBe('Manager');
      expect(review.deactivatedCount).toBeGreaterThanOrEqual(1);
      expect(review.accounts.length).toBe(review.activeCount + review.deactivatedCount);
    });

    it('flags every privileged account whether or not it is being used', async () => {
      const review = await as(f.ids.admin, (repo) => buildAccessReview(repo));
      const admins = review.accounts.filter((a) => a.privileged);
      expect(admins.map((a) => a.employee.workEmail)).toContain(EMAILS.admin);
      expect(admins.every((a) => a.employee.role === 'ADMIN')).toBe(true);
      expect(review.privilegedCount).toBe(admins.length);
    });

    it('puts the findings at the top', async () => {
      const review = await as(f.ids.admin, (repo) => buildAccessReview(repo));
      expect(review.accounts[0]?.privileged).toBe(true);
    });

    it('reports the last login it can actually see', async () => {
      await as(f.ids.alice, (repo) => repo.accessLog.record({ event: 'LOGIN' }));
      const review = await as(f.ids.admin, (repo) => buildAccessReview(repo));
      const alice = review.accounts.find((a) => a.employee.id === f.ids.alice);
      expect(alice?.lastLoginAt).not.toBeNull();
      expect(alice?.dormant).toBe(false);
    });

    it('separates "last seen" from "last login"', async () => {
      // A read is not an authentication. Conflating them would let a dormant
      // account with a live session look current.
      await as(f.ids.bob, (repo) => repo.accessLog.record({ event: 'VIEW', entity: 'tickets' }));
      const review = await as(f.ids.admin, (repo) => buildAccessReview(repo));
      const bob = review.accounts.find((a) => a.employee.id === f.ids.bob);
      expect(bob?.lastSeenAt).not.toBeNull();
      expect(bob?.lastLoginAt).toBeNull();
      expect(bob?.dormant).toBe(true);
    });

    it('writes the evidence that the review happened, with the names it covered', async () => {
      const entry = await as(f.ids.admin, (repo) =>
        recordAccessReview(repo, 'Half-yearly review, H1 FY27'),
      );
      expect(entry.action).toBe('ACCESS_REVIEW_PERFORMED');
      expect(entry.actorId).toBe(f.ids.admin);
      expect(entry.payload).toMatchObject({
        reviewDate: istDateOf(new Date()),
        reviewedBy: EMAILS.admin,
        dormantThresholdDays: DORMANT_AFTER_DAYS,
        note: 'Half-yearly review, H1 FY27',
      });
      expect(entry.payload.privileged).toContain(EMAILS.admin);
      expect(Array.isArray(entry.payload.dormant)).toBe(true);
    });

    it('leaves the evidence inside a chain that still verifies', async () => {
      await as(f.ids.admin, (repo) => recordAccessReview(repo));
      const v = await as(f.ids.admin, (repo) => repo.audit.verify());
      expect(v.ok).toBe(true);
      expect(v.headHashHex).toMatch(/^[0-9a-f]{64}$/);
    });
  });

  // ===========================================================================
  describe('the audit log viewer', () => {
    it('records the fact that the log was read', async () => {
      const view = await as(f.ids.admin, (repo) => readAuditLog(repo));
      expect(view.entries[0]?.action).toBe('AUDIT_LOG_VIEWED');
      expect(view.entries[0]?.actorId).toBe(f.ids.admin);
    });

    it('returns newest first and reports a head hash that matches the newest row', async () => {
      // The head hash is what gets published as the day's external anchor, so it
      // has to be the hash of the entry actually at the top of the page.
      const j = await joiner();
      await as(f.ids.admin, (repo) => setEmployeeRole(repo, j.id, 'MANAGER'));
      const view = await as(f.ids.admin, (repo) => readAuditLog(repo));

      expect(view.verification.ok).toBe(true);
      expect(view.entries[0]?.rowHashHex).toBe(view.verification.headHashHex);
      const seqs = view.entries.map((e) => e.seq);
      expect(seqs).toEqual([...seqs].sort((a, b) => b - a));
    });

    it('honours the limit while still verifying the whole chain', async () => {
      const j = await joiner();
      await as(f.ids.admin, (repo) => setEmployeeRole(repo, j.id, 'MANAGER'));
      await as(f.ids.admin, (repo) => setEmployeeManager(repo, j.id, f.ids.manager));

      const view = await as(f.ids.admin, (repo) => readAuditLog(repo, 2));
      expect(view.entries.length).toBe(2);
      // Four entries exist by now (create, role, manager, view); the check covers
      // all of them, not just the page.
      expect(view.verification.checked).toBeGreaterThan(view.entries.length);
    });
  });
});
