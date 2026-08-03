import { describe, it, expect } from 'vitest';
import {
  checkTransition,
  isOverdue,
  isStale,
  isTerminal,
  evaluateOnTime,
  legalTransitions,
  STALE_THRESHOLD_WORKING_DAYS,
  type TicketStatus,
  type TransitionActor,
} from './tickets';
import type { IsoDate } from './calendar';

const NONE: ReadonlySet<IsoDate> = new Set();
const HOLIDAYS: ReadonlySet<IsoDate> = new Set(['2026-08-14']); // Friday

const actors = (...xs: TransitionActor[]) => new Set<TransitionActor>(xs);

const ALL_STATUSES: TicketStatus[] = ['OPEN', 'IN_PROGRESS', 'BLOCKED', 'DONE', 'CANCELLED'];

describe('checkTransition — legal moves', () => {
  it('lets the assignee start, block, unblock and finish', () => {
    const a = actors('ASSIGNEE');
    expect(checkTransition('OPEN', 'IN_PROGRESS', a).ok).toBe(true);
    expect(checkTransition('IN_PROGRESS', 'BLOCKED', a).ok).toBe(true);
    expect(checkTransition('BLOCKED', 'IN_PROGRESS', a).ok).toBe(true);
    expect(checkTransition('IN_PROGRESS', 'DONE', a).ok).toBe(true);
  });

  it('requires a reason when blocking', () => {
    const r = checkTransition('IN_PROGRESS', 'BLOCKED', actors('ASSIGNEE'));
    expect(r).toEqual({ ok: true, requiresReason: true });
  });

  it('does not require a reason to start work', () => {
    const r = checkTransition('OPEN', 'IN_PROGRESS', actors('ASSIGNEE'));
    expect(r).toEqual({ ok: true, requiresReason: false });
  });
});

describe('checkTransition — reopen is a manager action', () => {
  it('forbids the assignee from reopening their own finished work', () => {
    // If a person can un-finish their own ticket, "done" stops meaning anything.
    const r = checkTransition('DONE', 'IN_PROGRESS', actors('ASSIGNEE'));
    expect(r.ok).toBe(false);
  });

  it('allows a manager to reopen, with a reason', () => {
    expect(checkTransition('DONE', 'IN_PROGRESS', actors('MANAGER'))).toEqual({
      ok: true,
      requiresReason: true,
    });
  });

  it('allows an admin to reopen', () => {
    expect(checkTransition('DONE', 'IN_PROGRESS', actors('ADMIN')).ok).toBe(true);
  });

  it('allows someone who is both assignee and manager', () => {
    expect(checkTransition('DONE', 'IN_PROGRESS', actors('ASSIGNEE', 'MANAGER')).ok).toBe(true);
  });
});

describe('checkTransition — deny by default', () => {
  it('rejects a no-op transition', () => {
    const r = checkTransition('OPEN', 'OPEN', actors('ADMIN'));
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.reason).toMatch(/already OPEN/);
  });

  it('rejects skipping straight from OPEN to DONE', () => {
    expect(checkTransition('OPEN', 'DONE', actors('ADMIN')).ok).toBe(false);
  });

  it('treats CANCELLED as terminal for every actor', () => {
    for (const to of ALL_STATUSES) {
      expect(checkTransition('CANCELLED', to, actors('ADMIN')).ok).toBe(false);
    }
  });

  it('allows no transition at all to an empty actor set', () => {
    const none = actors();
    for (const from of ALL_STATUSES) {
      for (const to of ALL_STATUSES) {
        expect(checkTransition(from, to, none).ok).toBe(false);
      }
    }
  });

  it('permits exactly the 8 transitions in the table and no others', () => {
    // Deny-by-default regression guard: if someone adds a status without adding its
    // transitions, this count changes and the test says so.
    const everyone = actors('ASSIGNEE', 'RAISER', 'MANAGER', 'ADMIN');
    let legal = 0;
    for (const from of ALL_STATUSES) {
      for (const to of ALL_STATUSES) {
        if (checkTransition(from, to, everyone).ok) legal++;
      }
    }
    expect(legal).toBe(8);
  });
});

describe('legalTransitions', () => {
  it('offers the assignee exactly what they may do from OPEN', () => {
    expect(legalTransitions('OPEN', actors('ASSIGNEE'))).toEqual(['IN_PROGRESS']);
  });

  it('offers block and finish from IN_PROGRESS', () => {
    expect(legalTransitions('IN_PROGRESS', actors('ASSIGNEE')).sort()).toEqual(
      ['BLOCKED', 'DONE'].sort(),
    );
  });

  it('does not offer the assignee a reopen', () => {
    expect(legalTransitions('DONE', actors('ASSIGNEE'))).toEqual([]);
  });

  it('offers a manager the reopen', () => {
    expect(legalTransitions('DONE', actors('MANAGER'))).toEqual(['IN_PROGRESS']);
  });

  it('offers nothing from a terminal CANCELLED, to anyone', () => {
    expect(legalTransitions('CANCELLED', actors('ADMIN'))).toEqual([]);
  });

  it('offers nothing to an actor with no relationship to the ticket', () => {
    expect(legalTransitions('OPEN', actors())).toEqual([]);
  });

  it('never offers anything checkTransition would reject', () => {
    // The UI is built from this function, so any disagreement would show a
    // control that fails when clicked.
    const roleSets: TransitionActor[][] = [
      ['ASSIGNEE'], ['RAISER'], ['MANAGER'], ['ADMIN'], ['ASSIGNEE', 'MANAGER'], [],
    ];
    for (const from of ALL_STATUSES) {
      for (const set of roleSets) {
        const a = actors(...set);
        for (const to of legalTransitions(from, a)) {
          expect(checkTransition(from, to, a).ok).toBe(true);
        }
      }
    }
  });
});

describe('isOverdue', () => {
  it('is false before the deadline and on the deadline day', () => {
    expect(isOverdue({ deadline: '2026-08-10', status: 'OPEN' }, '2026-08-09')).toBe(false);
    // A deadline means END of that day, so the deadline day itself is not late.
    expect(isOverdue({ deadline: '2026-08-10', status: 'OPEN' }, '2026-08-10')).toBe(false);
  });

  it('is true the day after', () => {
    expect(isOverdue({ deadline: '2026-08-10', status: 'OPEN' }, '2026-08-11')).toBe(true);
  });

  it('is false for terminal states however late', () => {
    expect(isOverdue({ deadline: '2020-01-01', status: 'DONE' }, '2026-08-11')).toBe(false);
    expect(isOverdue({ deadline: '2020-01-01', status: 'CANCELLED' }, '2026-08-11')).toBe(false);
  });

  it('is true for blocked work past its deadline — blocked is not an excuse', () => {
    expect(isOverdue({ deadline: '2026-08-10', status: 'BLOCKED' }, '2026-08-11')).toBe(true);
  });

  it('agrees with isTerminal', () => {
    expect(isTerminal('DONE')).toBe(true);
    expect(isTerminal('CANCELLED')).toBe(true);
    expect(isTerminal('BLOCKED')).toBe(false);
  });
});

describe('isStale', () => {
  it('flags a P1 punched yesterday — P1 means punch every working day', () => {
    expect(STALE_THRESHOLD_WORKING_DAYS.P1).toBe(1);
    expect(
      isStale({ status: 'IN_PROGRESS', priority: 'P1', lastActivityDate: '2026-08-03' }, '2026-08-04', NONE),
    ).toBe(true);
  });

  it('does not flag a P1 punched today', () => {
    expect(
      isStale({ status: 'IN_PROGRESS', priority: 'P1', lastActivityDate: '2026-08-04' }, '2026-08-04', NONE),
    ).toBe(false);
  });

  it('does not flag a P3 until 5 working days have passed', () => {
    // Mon 08-03 → Fri 08-07 is 4 working days: not yet stale.
    expect(
      isStale({ status: 'IN_PROGRESS', priority: 'P3', lastActivityDate: '2026-08-03' }, '2026-08-07', NONE),
    ).toBe(false);
    // → Mon 08-10 is 5: stale.
    expect(
      isStale({ status: 'IN_PROGRESS', priority: 'P3', lastActivityDate: '2026-08-03' }, '2026-08-10', NONE),
    ).toBe(true);
  });

  it('does not punish someone for a weekend', () => {
    // Punched Friday, checked Monday: 1 working day, so a P2 (threshold 3) is fine.
    expect(
      isStale({ status: 'IN_PROGRESS', priority: 'P2', lastActivityDate: '2026-08-07' }, '2026-08-10', NONE),
    ).toBe(false);
  });

  it('does not punish someone for a public holiday', () => {
    // Thu 08-13 → Mon 08-17 with Fri 08-14 a holiday = 1 working day.
    expect(
      isStale({ status: 'IN_PROGRESS', priority: 'P2', lastActivityDate: '2026-08-13' }, '2026-08-17', HOLIDAYS),
    ).toBe(false);
    // Without the holiday it would be 2 — still under P2's threshold, but the count differs.
    expect(
      isStale({ status: 'IN_PROGRESS', priority: 'P1', lastActivityDate: '2026-08-13' }, '2026-08-17', HOLIDAYS),
    ).toBe(true);
  });

  it('flags blocked work too — a blocker nobody updates is the worst case', () => {
    expect(
      isStale({ status: 'BLOCKED', priority: 'P1', lastActivityDate: '2026-08-03' }, '2026-08-04', NONE),
    ).toBe(true);
  });

  it('never flags OPEN, DONE or CANCELLED', () => {
    for (const status of ['OPEN', 'DONE', 'CANCELLED'] as TicketStatus[]) {
      expect(
        isStale({ status, priority: 'P1', lastActivityDate: '2020-01-01' }, '2026-08-04', NONE),
      ).toBe(false);
    }
  });
});

describe('evaluateOnTime', () => {
  it('returns null for anything not finished', () => {
    expect(
      evaluateOnTime(
        { status: 'IN_PROGRESS', deadline: '2026-08-10', originalDeadline: '2026-08-10', closedDate: null },
        NONE,
      ),
    ).toBeNull();
  });

  it('returns null for a cancelled ticket — cancelling is not delivering', () => {
    // Otherwise anyone could hit 100% on-time by cancelling whatever they were late on.
    expect(
      evaluateOnTime(
        { status: 'CANCELLED', deadline: '2026-08-10', originalDeadline: '2026-08-10', closedDate: '2026-08-09' },
        NONE,
      ),
    ).toBeNull();
  });

  it('reports on time against both when the deadline never moved', () => {
    expect(
      evaluateOnTime(
        { status: 'DONE', deadline: '2026-08-10', originalDeadline: '2026-08-10', closedDate: '2026-08-10' },
        NONE,
      ),
    ).toEqual({ againstCurrent: true, againstOriginal: true, slippedBy: 0 });
  });

  it('exposes the case the whole design exists for: met the moved deadline, missed the promise', () => {
    // Promised Monday, pushed to Friday, delivered Friday. "On time" by the current
    // deadline, late by the one that was actually promised.
    const r = evaluateOnTime(
      { status: 'DONE', deadline: '2026-08-07', originalDeadline: '2026-08-03', closedDate: '2026-08-07' },
      NONE,
    );
    expect(r).toEqual({ againstCurrent: true, againstOriginal: false, slippedBy: 4 });
  });

  it('reports late against both when it blew even the extended deadline', () => {
    expect(
      evaluateOnTime(
        { status: 'DONE', deadline: '2026-08-07', originalDeadline: '2026-08-03', closedDate: '2026-08-11' },
        NONE,
      ),
    ).toMatchObject({ againstCurrent: false, againstOriginal: false });
  });

  it('measures slippage in working days, ignoring weekends and holidays', () => {
    // 08-13 → 08-17 with 08-14 a holiday: only Mon 08-17 counts.
    const r = evaluateOnTime(
      { status: 'DONE', deadline: '2026-08-17', originalDeadline: '2026-08-13', closedDate: '2026-08-17' },
      HOLIDAYS,
    );
    expect(r?.slippedBy).toBe(1);
  });

  it('never reports negative slippage if a deadline is pulled forward', () => {
    const r = evaluateOnTime(
      { status: 'DONE', deadline: '2026-08-03', originalDeadline: '2026-08-07', closedDate: '2026-08-03' },
      NONE,
    );
    expect(r?.slippedBy).toBe(0);
  });
});
