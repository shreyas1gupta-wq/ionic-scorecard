/**
 * Service rules, run against BOTH repository implementations.
 *
 * The repository contract covers "can this actor read or write this row". This
 * suite covers the rules that make the tool a disciplined tracker rather than a
 * task list: legal transitions, a punch for every status change, a note before a
 * deadline moves, a handover on reassignment, and an audit entry for all of it.
 */

import { describe, it, expect, beforeAll, beforeEach, afterAll } from 'vitest';
import { IMPLEMENTATIONS, type Fixture } from '../repo/fixtures';
import { ValidationError, type Repository, type Uuid } from '../repo/types';
import { istDateOf } from '../domain/calendar';
import {
  createTicket,
  decideDeadlineChange,
  punch,
  reassign,
  requestDeadlineChange,
} from './tickets';

const TODAY = istDateOf(new Date());

describe.each(IMPLEMENTATIONS)('ticket service: %s', (_name, build) => {
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

  /** A ticket raised by the manager and assigned to Alice. */
  const raise = (deadline = '2026-12-31') =>
    as(f.ids.manager, (repo) =>
      createTicket(repo, {
        title: 'Prepare the monthly pack',
        priority: 'P2',
        assigneeId: f.ids.alice,
        deadline,
      }),
    );

  const start = (ticketId: Uuid) =>
    as(f.ids.alice, (repo) =>
      punch(repo, { ticketId, status: 'IN_PROGRESS', note: 'started' }),
    );

  // ===========================================================================
  describe('creating', () => {
    it('always records the raiser as the acting employee', async () => {
      const t = await raise();
      expect(t.raiserId).toBe(f.ids.manager);
      expect(t.status).toBe('OPEN');
    });

    it('writes an audit entry', async () => {
      const t = await raise();
      const log = await as(f.ids.admin, (repo) => repo.audit.list());
      const entry = log.find((e) => e.entityId === t.id);
      expect(entry?.action).toBe('TICKET_CREATED');
      expect(entry?.actorId).toBe(f.ids.manager);
      expect(entry?.payload).toMatchObject({ ref: t.ref, priority: 'P2' });
    });

    it('refuses an empty title', async () => {
      await expect(
        as(f.ids.manager, (repo) =>
          createTicket(repo, {
            title: '   ',
            priority: 'P2',
            assigneeId: f.ids.alice,
            deadline: '2026-12-31',
          }),
        ),
      ).rejects.toBeInstanceOf(ValidationError);
    });
  });

  // ===========================================================================
  describe('transitions', () => {
    it('lets the assignee start work, and moves the ticket', async () => {
      const t = await raise();
      await start(t.id);
      const after = await as(f.ids.alice, (repo) => repo.tickets.findById(t.id));
      expect(after?.status).toBe('IN_PROGRESS');
    });

    it('refuses to skip straight from OPEN to DONE', async () => {
      const t = await raise();
      await expect(
        as(f.ids.alice, (repo) => punch(repo, { ticketId: t.id, status: 'DONE' })),
      ).rejects.toBeInstanceOf(ValidationError);
    });

    it('refuses to let the assignee reopen their own finished work', async () => {
      // If a person can un-finish their own ticket, "done" stops meaning anything.
      const t = await raise();
      await start(t.id);
      await as(f.ids.alice, (repo) => punch(repo, { ticketId: t.id, status: 'DONE' }));
      await expect(
        as(f.ids.alice, (repo) =>
          punch(repo, { ticketId: t.id, status: 'IN_PROGRESS', note: 'more to do' }),
        ),
      ).rejects.toBeInstanceOf(ValidationError);
    });

    it('lets a manager reopen, with a note', async () => {
      const t = await raise();
      await start(t.id);
      await as(f.ids.alice, (repo) => punch(repo, { ticketId: t.id, status: 'DONE' }));
      await as(f.ids.manager, (repo) =>
        punch(repo, { ticketId: t.id, status: 'IN_PROGRESS', note: 'client rejected the pack' }),
      );
      const after = await as(f.ids.manager, (repo) => repo.tickets.findById(t.id));
      expect(after?.status).toBe('IN_PROGRESS');
    });

    it('requires a note for a transition that demands one', async () => {
      const t = await raise();
      await start(t.id);
      await as(f.ids.alice, (repo) => punch(repo, { ticketId: t.id, status: 'DONE' }));
      await expect(
        as(f.ids.manager, (repo) => punch(repo, { ticketId: t.id, status: 'IN_PROGRESS' })),
      ).rejects.toThrow(/requires a note/);
    });

    it('requires a blocked reason', async () => {
      const t = await raise();
      await start(t.id);
      await expect(
        as(f.ids.alice, (repo) =>
          punch(repo, { ticketId: t.id, status: 'BLOCKED', note: 'stuck' }),
        ),
      ).rejects.toThrow(/blocked_reason is required/);
    });

    it('accepts BLOCKED with both a note and a reason', async () => {
      const t = await raise();
      await start(t.id);
      const p = await as(f.ids.alice, (repo) =>
        punch(repo, {
          ticketId: t.id,
          status: 'BLOCKED',
          note: 'waiting',
          blockedReason: 'custodian has not sent the file',
        }),
      );
      expect(p.blockedReason).toBe('custodian has not sent the file');
    });

    it('stamps a closed date on a terminal status', async () => {
      const t = await raise();
      await start(t.id);
      await as(f.ids.alice, (repo) => punch(repo, { ticketId: t.id, status: 'DONE' }));
      const after = await as(f.ids.alice, (repo) => repo.tickets.findById(t.id));
      expect(after?.closedDate).toBe(TODAY);
    });
  });

  // ===========================================================================
  describe('every status change leaves a record', () => {
    it('creates a punch for the change', async () => {
      const t = await raise();
      await start(t.id);
      const history = await as(f.ids.alice, (repo) => repo.tickets.listPunches(t.id));
      expect(history.length).toBe(1);
      expect(history[0]).toMatchObject({ status: 'IN_PROGRESS', note: 'started' });
    });

    it('allows progress notes without a status change', async () => {
      const t = await raise();
      await start(t.id);
      await as(f.ids.alice, (repo) =>
        punch(repo, { ticketId: t.id, note: 'halfway', minutesSpent: 90 }),
      );
      const history = await as(f.ids.alice, (repo) => repo.tickets.listPunches(t.id));
      expect(history.length).toBe(2);
      expect(history[1]).toMatchObject({ status: 'IN_PROGRESS', minutesSpent: 90 });
    });

    it('audits a status change differently from a plain punch', async () => {
      const t = await raise();
      await start(t.id);
      await as(f.ids.alice, (repo) => punch(repo, { ticketId: t.id, note: 'still going' }));
      const log = await as(f.ids.admin, (repo) => repo.audit.list());
      const actions = log.map((e) => e.action);
      expect(actions).toContain('TICKET_STATUS_CHANGED');
      expect(actions).toContain('PUNCH_CREATED');
    });
  });

  // ===========================================================================
  describe('reassignment', () => {
    it('requires a handover note', async () => {
      const t = await raise();
      await expect(
        as(f.ids.manager, (repo) =>
          reassign(repo, { ticketId: t.id, newAssigneeId: f.ids.bob, handoverNote: '  ' }),
        ),
      ).rejects.toBeInstanceOf(ValidationError);
    });

    it('records the handover where the next person will read it', async () => {
      const t = await raise();
      await as(f.ids.manager, (repo) =>
        reassign(repo, {
          ticketId: t.id,
          newAssigneeId: f.ids.bob,
          handoverNote: 'draft is in the shared folder, needs the fee table',
        }),
      );
      const history = await as(f.ids.bob, (repo) => repo.tickets.listPunches(t.id));
      expect(history.at(-1)?.note).toMatch(/^Handover: draft is in the shared folder/);
      const after = await as(f.ids.bob, (repo) => repo.tickets.findById(t.id));
      expect(after?.assigneeId).toBe(f.ids.bob);
    });

    it('refuses to reassign to the current assignee', async () => {
      const t = await raise();
      await expect(
        as(f.ids.manager, (repo) =>
          reassign(repo, { ticketId: t.id, newAssigneeId: f.ids.alice, handoverNote: 'x' }),
        ),
      ).rejects.toThrow(/already the assignee/);
    });

    it('refuses to reassign finished work', async () => {
      const t = await raise();
      await start(t.id);
      await as(f.ids.alice, (repo) => punch(repo, { ticketId: t.id, status: 'DONE' }));
      await expect(
        as(f.ids.manager, (repo) =>
          reassign(repo, { ticketId: t.id, newAssigneeId: f.ids.bob, handoverNote: 'x' }),
        ),
      ).rejects.toThrow(/cannot reassign a DONE/);
    });
  });

  // ===========================================================================
  describe('deadline control', () => {
    it('refuses to move a deadline before anything has been said', async () => {
      // REQUIREMENTS 5: say where things stand, then move the date.
      const t = await raise('2026-09-01');
      await expect(
        as(f.ids.alice, (repo) =>
          requestDeadlineChange(repo, {
            ticketId: t.id,
            toDate: '2026-10-01',
            reason: 'upstream data is late',
          }),
        ),
      ).rejects.toThrow(/say where things stand first/);
    });

    it('allows the request once a punch exists', async () => {
      const t = await raise('2026-09-01');
      await start(t.id);
      const c = await as(f.ids.alice, (repo) =>
        requestDeadlineChange(repo, {
          ticketId: t.id,
          toDate: '2026-10-01',
          reason: 'upstream data is late',
        }),
      );
      expect(c).toMatchObject({ fromDate: '2026-09-01', toDate: '2026-10-01', decision: 'PENDING' });
    });

    it('applies the new date on approval and never touches the original', async () => {
      const t = await raise('2026-09-01');
      await start(t.id);
      const c = await as(f.ids.alice, (repo) =>
        requestDeadlineChange(repo, { ticketId: t.id, toDate: '2026-10-01', reason: 'late' }),
      );
      await as(f.ids.manager, (repo) => decideDeadlineChange(repo, c.id, 'APPROVED'));

      const after = await as(f.ids.alice, (repo) => repo.tickets.findById(t.id));
      expect(after?.deadline).toBe('2026-10-01');
      // The whole point: the promised date survives, so both can be reported.
      expect(after?.originalDeadline).toBe('2026-09-01');
    });

    it('leaves the date alone on rejection', async () => {
      const t = await raise('2026-09-01');
      await start(t.id);
      const c = await as(f.ids.alice, (repo) =>
        requestDeadlineChange(repo, { ticketId: t.id, toDate: '2026-10-01', reason: 'late' }),
      );
      await as(f.ids.manager, (repo) => decideDeadlineChange(repo, c.id, 'REJECTED'));
      const after = await as(f.ids.alice, (repo) => repo.tickets.findById(t.id));
      expect(after?.deadline).toBe('2026-09-01');
    });

    it('audits the request with the original deadline for context', async () => {
      const t = await raise('2026-09-01');
      await start(t.id);
      await as(f.ids.alice, (repo) =>
        requestDeadlineChange(repo, { ticketId: t.id, toDate: '2026-10-01', reason: 'late' }),
      );
      const log = await as(f.ids.admin, (repo) => repo.audit.list());
      const entry = log.find((e) => e.action === 'DEADLINE_CHANGE_REQUESTED');
      expect(entry?.payload).toMatchObject({
        from: '2026-09-01',
        to: '2026-10-01',
        originalDeadline: '2026-09-01',
      });
    });

    it('refuses to move the deadline of finished work', async () => {
      const t = await raise('2026-09-01');
      await start(t.id);
      await as(f.ids.alice, (repo) => punch(repo, { ticketId: t.id, status: 'DONE' }));
      await expect(
        as(f.ids.alice, (repo) =>
          requestDeadlineChange(repo, { ticketId: t.id, toDate: '2026-10-01', reason: 'x' }),
        ),
      ).rejects.toThrow(/cannot move the deadline of a DONE/);
    });
  });

  // ===========================================================================
  describe('the audit chain survives real work', () => {
    it('stays verifiable across a full ticket lifecycle', async () => {
      const t = await raise('2026-09-01');
      await start(t.id);
      await as(f.ids.alice, (repo) =>
        punch(repo, {
          ticketId: t.id, status: 'BLOCKED', note: 'waiting', blockedReason: 'custodian file',
        }),
      );
      await as(f.ids.alice, (repo) =>
        punch(repo, { ticketId: t.id, status: 'IN_PROGRESS', note: 'file arrived' }),
      );
      const c = await as(f.ids.alice, (repo) =>
        requestDeadlineChange(repo, { ticketId: t.id, toDate: '2026-10-01', reason: 'late' }),
      );
      await as(f.ids.manager, (repo) => decideDeadlineChange(repo, c.id, 'APPROVED'));
      await as(f.ids.manager, (repo) =>
        reassign(repo, { ticketId: t.id, newAssigneeId: f.ids.bob, handoverNote: 'over to you' }),
      );
      await as(f.ids.bob, (repo) => punch(repo, { ticketId: t.id, status: 'DONE' }));

      const v = await as(f.ids.admin, (repo) => repo.audit.verify());
      expect(v.failures).toEqual([]);
      expect(v.ok).toBe(true);
      // create, start, block, unblock, request, decide, reassign, done
      expect(v.checked).toBe(8);
    });
  });
});
