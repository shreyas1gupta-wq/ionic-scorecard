import { describe, it, expect } from 'vitest';
import { ageingOf, buildReport, percentile, UNCATEGORISED, type ReportInput } from './reports';
import type { IsoDate } from './calendar';

const NONE: ReadonlySet<IsoDate> = new Set();
/** 2026-08-14 is a Friday. */
const HOLIDAYS: ReadonlySet<IsoDate> = new Set(['2026-08-14']);

/** Monday 2026-08-17, so weekend handling is exercised by default. */
const NOW = new Date('2026-08-17T06:00:00Z');

function ticket(over: Partial<ReportInput> = {}): ReportInput {
  return {
    id: over.id ?? 't1',
    ref: over.ref ?? 'TKT-2026-0001',
    title: 'x',
    assigneeId: 'alice',
    categoryId: null,
    priority: 'P2',
    status: 'IN_PROGRESS',
    deadline: '2026-08-31',
    originalDeadline: '2026-08-31',
    createdDate: '2026-08-03',
    closedDate: null,
    lastPunchDate: '2026-08-17',
    punchCount: 1,
    ...over,
  };
}

describe('percentile', () => {
  it('returns null for an empty set rather than a misleading zero', () => {
    expect(percentile([], 0.5)).toBeNull();
  });

  it('never interpolates, so every reported value actually happened', () => {
    // Nearest-rank: p50 of [1,2,3,4] is 2, not 2.5.
    expect(percentile([1, 2, 3, 4], 0.5)).toBe(2);
  });

  it('handles a single value', () => {
    expect(percentile([7], 0.5)).toBe(7);
    expect(percentile([7], 0.9)).toBe(7);
  });

  it('returns the extremes at the bounds', () => {
    expect(percentile([1, 5, 9], 0)).toBe(1);
    expect(percentile([1, 5, 9], 1)).toBe(9);
  });

  it('computes p90 by nearest rank', () => {
    const xs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
    expect(percentile(xs, 0.9)).toBe(9);
  });
});

describe('on-time reporting — the whole point of the file', () => {
  it('reports null percentages when nothing is closed, not zero', () => {
    // 0% would read as "we never deliver on time" rather than "no data yet".
    const r = buildReport([ticket()], NONE, NOW);
    expect(r.overall.closed).toBe(0);
    expect(r.overall.onTimePctCurrent).toBeNull();
    expect(r.overall.onTimePctOriginal).toBeNull();
  });

  it('separates the two measures when a deadline was moved', () => {
    // Promised the 10th, pushed to the 21st, delivered the 20th.
    const r = buildReport(
      [
        ticket({
          status: 'DONE',
          originalDeadline: '2026-08-10',
          deadline: '2026-08-21',
          closedDate: '2026-08-20',
        }),
      ],
      NONE,
      NOW,
    );
    expect(r.overall.closed).toBe(1);
    expect(r.overall.onTimePctCurrent).toBe(100);
    expect(r.overall.onTimePctOriginal).toBe(0);
    expect(r.overall.deadlinesMoved).toBe(1);
  });

  it('counts both when the deadline never moved and was met', () => {
    const r = buildReport(
      [ticket({ status: 'DONE', deadline: '2026-08-20', originalDeadline: '2026-08-20', closedDate: '2026-08-19' })],
      NONE,
      NOW,
    );
    expect(r.overall.onTimePctCurrent).toBe(100);
    expect(r.overall.onTimePctOriginal).toBe(100);
    expect(r.overall.deadlinesMoved).toBe(0);
  });

  it('excludes cancelled work from on-time entirely', () => {
    // Otherwise anyone could hit 100% by cancelling whatever they were late on.
    const r = buildReport(
      [
        ticket({ id: 'a', status: 'CANCELLED', closedDate: '2026-08-05' }),
        ticket({ id: 'b', status: 'DONE', deadline: '2026-08-10', originalDeadline: '2026-08-10', closedDate: '2026-08-20' }),
      ],
      NONE,
      NOW,
    );
    expect(r.overall.cancelled).toBe(1);
    expect(r.overall.closed).toBe(1);
    expect(r.overall.onTimePctOriginal).toBe(0);
  });

  it('measures slippage in working days, skipping weekends and holidays', () => {
    // 2026-08-13 (Thu) -> 2026-08-17 (Mon), with Fri 08-14 a holiday: 1 working day.
    const r = buildReport(
      [ticket({ originalDeadline: '2026-08-13', deadline: '2026-08-17' })],
      HOLIDAYS,
      NOW,
    );
    expect(r.overall.workingDaysSlipped).toBe(1);
  });

  it('rounds percentages to one decimal', () => {
    const rows = [
      ticket({ id: 'a', status: 'DONE', deadline: '2026-08-20', originalDeadline: '2026-08-20', closedDate: '2026-08-19' }),
      ticket({ id: 'b', status: 'DONE', deadline: '2026-08-20', originalDeadline: '2026-08-20', closedDate: '2026-08-19' }),
      ticket({ id: 'c', status: 'DONE', deadline: '2026-08-10', originalDeadline: '2026-08-10', closedDate: '2026-08-20' }),
    ];
    const r = buildReport(rows, NONE, NOW);
    expect(r.overall.onTimePctCurrent).toBe(66.7);
  });
});

describe('cycle time', () => {
  it('is measured in working days from raised to closed', () => {
    // Mon 08-03 -> Fri 08-07 is 4 working days.
    const r = buildReport(
      [ticket({ status: 'DONE', createdDate: '2026-08-03', closedDate: '2026-08-07', deadline: '2026-08-31', originalDeadline: '2026-08-31' })],
      NONE,
      NOW,
    );
    expect(r.overall.medianCycleDays).toBe(4);
    expect(r.overall.p90CycleDays).toBe(4);
  });

  it('is null when nothing has closed', () => {
    const r = buildReport([ticket()], NONE, NOW);
    expect(r.overall.medianCycleDays).toBeNull();
  });

  it('reports median and p90 separately across several tickets', () => {
    const closedAfter = (id: string, days: number, closed: IsoDate) =>
      ticket({ id, status: 'DONE', createdDate: '2026-08-03', closedDate: closed, deadline: '2026-12-31', originalDeadline: '2026-12-31', ref: `TKT-2026-000${days}` });
    // Working days from Mon 08-03: 08-04=1, 08-05=2, 08-07=4, 08-24=15
    const r = buildReport(
      [
        closedAfter('a', 1, '2026-08-04'),
        closedAfter('b', 2, '2026-08-05'),
        closedAfter('c', 4, '2026-08-07'),
        closedAfter('d', 15, '2026-08-24'),
      ],
      NONE,
      NOW,
    );
    expect(r.overall.medianCycleDays).toBe(2);
    expect(r.overall.p90CycleDays).toBe(15);
  });
});

describe('open-work counters', () => {
  it('counts overdue only for non-terminal tickets', () => {
    const r = buildReport(
      [
        ticket({ id: 'a', deadline: '2026-08-10' }),
        ticket({ id: 'b', status: 'DONE', deadline: '2020-01-01', closedDate: '2026-08-05' }),
      ],
      NONE,
      NOW,
    );
    expect(r.overall.open).toBe(1);
    expect(r.overall.overdue).toBe(1);
  });

  it('flags a stale P1 and counts never-updated tickets', () => {
    const r = buildReport(
      [
        ticket({ id: 'a', priority: 'P1', lastPunchDate: '2026-08-10', punchCount: 2 }),
        ticket({ id: 'b', priority: 'P1', lastPunchDate: null, punchCount: 0, createdDate: '2026-08-03' }),
      ],
      NONE,
      NOW,
    );
    expect(r.overall.stale).toBe(2);
    expect(r.overall.neverUpdated).toBe(1);
  });

  it('does not flag a ticket updated today', () => {
    const r = buildReport([ticket({ priority: 'P1', lastPunchDate: '2026-08-17' })], NONE, NOW);
    expect(r.overall.stale).toBe(0);
  });
});

describe('grouping', () => {
  it('groups by person, worst problem first', () => {
    const r = buildReport(
      [
        ticket({ id: 'a', assigneeId: 'alice', deadline: '2026-12-31' }),
        ticket({ id: 'b', assigneeId: 'bob', deadline: '2026-08-10' }),
        ticket({ id: 'c', assigneeId: 'bob', deadline: '2026-08-11' }),
      ],
      NONE,
      NOW,
    );
    expect(r.byPerson.map((p) => p.key)).toEqual(['bob', 'alice']);
    expect(r.byPerson[0]!.overdue).toBe(2);
  });

  it('groups uncategorised work under a named key rather than dropping it', () => {
    const r = buildReport(
      [ticket({ id: 'a', categoryId: null }), ticket({ id: 'b', categoryId: 'cat-1' })],
      NONE,
      NOW,
    );
    expect(r.byCategory.map((c) => c.key).sort()).toEqual([UNCATEGORISED, 'cat-1'].sort());
  });
});

describe('ageing', () => {
  it('buckets open tickets by working days since they were raised', () => {
    const rows = [
      // Fri 08-14 is a holiday in this fixture.
      ticket({ id: 'a', createdDate: '2026-08-13' }), // Thu -> Mon = 1 working day
      ticket({ id: 'b', createdDate: '2026-08-10' }), // Mon -> Mon = 4
      ticket({ id: 'c', createdDate: '2026-08-03' }), // 9
      ticket({ id: 'd', createdDate: '2026-07-01' }), // well over 15
    ];
    expect(ageingOf(rows, '2026-08-17', HOLIDAYS)).toEqual({
      d0to3: 1,
      d4to7: 1,
      d8to14: 1,
      d15plus: 1,
    });
  });

  it('ignores closed tickets', () => {
    const rows = [ticket({ status: 'DONE', createdDate: '2026-01-01', closedDate: '2026-02-01' })];
    expect(ageingOf(rows, '2026-08-17', NONE)).toEqual({
      d0to3: 0,
      d4to7: 0,
      d8to14: 0,
      d15plus: 0,
    });
  });
});
