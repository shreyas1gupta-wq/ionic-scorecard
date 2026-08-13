/**
 * Reporting, as pure functions.
 *
 * No database, no clock, no formatting. Everything is computed from a list of
 * ticket summaries plus an explicitly-passed today and holiday set, which is what
 * makes the numbers testable against hand-worked fixtures rather than hopefully
 * correct.
 *
 * THE POINT OF THIS FILE, in one line: report on-time performance against BOTH
 * the original deadline and the current one. A tool that only measures against
 * the current deadline measures nothing, because the current deadline can be
 * moved. The gap between the two figures is the interesting number.
 */

import { istDateOf, workingDaysBetween, type IsoDate } from './calendar';
import { evaluateOnTime, isOverdue, isStale, type Priority, type TicketStatus } from './tickets';

/** The subset of a ticket summary the reports need. */
export interface ReportInput {
  readonly id: string;
  readonly ref: string;
  readonly title: string;
  readonly assigneeId: string;
  readonly categoryId: string | null;
  readonly priority: Priority;
  readonly status: TicketStatus;
  readonly deadline: IsoDate;
  readonly originalDeadline: IsoDate;
  /** IST calendar date the ticket was raised. */
  readonly createdDate: IsoDate;
  readonly closedDate: IsoDate | null;
  readonly lastPunchDate: IsoDate | null;
  readonly punchCount: number;
}

export interface GroupReport {
  /** Employee id, category id, or a synthetic key. */
  readonly key: string;
  readonly open: number;
  readonly overdue: number;
  readonly stale: number;
  readonly neverUpdated: number;
  readonly closed: number;
  readonly cancelled: number;
  /** Of `closed`, how many met the deadline as it stood at the time. */
  readonly onTimeCurrent: number;
  /** Of `closed`, how many met the date first promised. This is the honest one. */
  readonly onTimeOriginal: number;
  /** Null when nothing has been closed — 0% would be a lie. */
  readonly onTimePctCurrent: number | null;
  readonly onTimePctOriginal: number | null;
  /** Working days from raised to closed. Null when nothing closed. */
  readonly medianCycleDays: number | null;
  readonly p90CycleDays: number | null;
  /** Tickets whose deadline was moved at least once. */
  readonly deadlinesMoved: number;
  /** Total working days of slippage across those tickets. */
  readonly workingDaysSlipped: number;
}

export interface AgeingBuckets {
  readonly d0to3: number;
  readonly d4to7: number;
  readonly d8to14: number;
  readonly d15plus: number;
}

export interface Report {
  readonly today: IsoDate;
  readonly overall: GroupReport;
  readonly byPerson: readonly GroupReport[];
  readonly byCategory: readonly GroupReport[];
  /** How long currently-open tickets have been open, in working days. */
  readonly ageing: AgeingBuckets;
}

const TERMINAL: ReadonlySet<TicketStatus> = new Set<TicketStatus>(['DONE', 'CANCELLED']);

/**
 * Nearest-rank percentile on a sorted list.
 *
 * Stated explicitly because percentile definitions differ and a report that
 * silently switches method between versions is worse than one that is slightly
 * crude. p50 of [1,2,3,4] is 2 here, not 2.5 — no interpolation, so every value
 * reported is a value that actually happened.
 */
export function percentile(sortedAscending: readonly number[], p: number): number | null {
  if (sortedAscending.length === 0) return null;
  if (p <= 0) return sortedAscending[0]!;
  if (p >= 1) return sortedAscending[sortedAscending.length - 1]!;
  const rank = Math.ceil(p * sortedAscending.length);
  return sortedAscending[Math.max(0, rank - 1)]!;
}

function pct(numerator: number, denominator: number): number | null {
  if (denominator === 0) return null;
  return Math.round((numerator / denominator) * 1000) / 10;
}

function summarise(
  key: string,
  rows: readonly ReportInput[],
  today: IsoDate,
  holidays: ReadonlySet<IsoDate>,
): GroupReport {
  let open = 0;
  let overdue = 0;
  let stale = 0;
  let neverUpdated = 0;
  let closed = 0;
  let cancelled = 0;
  let onTimeCurrent = 0;
  let onTimeOriginal = 0;
  let deadlinesMoved = 0;
  let workingDaysSlipped = 0;
  const cycles: number[] = [];

  for (const t of rows) {
    if (t.deadline !== t.originalDeadline) {
      deadlinesMoved += 1;
      workingDaysSlipped += workingDaysBetween(t.originalDeadline, t.deadline, holidays);
    }

    if (t.status === 'CANCELLED') {
      cancelled += 1;
      continue;
    }

    if (TERMINAL.has(t.status)) {
      closed += 1;
      const verdict = evaluateOnTime(
        {
          status: t.status,
          deadline: t.deadline,
          originalDeadline: t.originalDeadline,
          closedDate: t.closedDate,
        },
        holidays,
      );
      if (verdict !== null) {
        if (verdict.againstCurrent) onTimeCurrent += 1;
        if (verdict.againstOriginal) onTimeOriginal += 1;
      }
      if (t.closedDate !== null) {
        cycles.push(workingDaysBetween(t.createdDate, t.closedDate, holidays));
      }
      continue;
    }

    open += 1;
    if (isOverdue({ deadline: t.deadline, status: t.status }, today)) overdue += 1;
    if (t.punchCount === 0) neverUpdated += 1;
    if (
      isStale(
        {
          status: t.status,
          priority: t.priority,
          // Never punched: the clock runs from when the work was raised, or a
          // ticket nobody has touched would never be flagged.
          lastActivityDate: t.lastPunchDate ?? t.createdDate,
        },
        today,
        holidays,
      )
    ) {
      stale += 1;
    }
  }

  cycles.sort((a, b) => a - b);

  return {
    key,
    open,
    overdue,
    stale,
    neverUpdated,
    closed,
    cancelled,
    onTimeCurrent,
    onTimeOriginal,
    onTimePctCurrent: pct(onTimeCurrent, closed),
    onTimePctOriginal: pct(onTimeOriginal, closed),
    medianCycleDays: percentile(cycles, 0.5),
    p90CycleDays: percentile(cycles, 0.9),
    deadlinesMoved,
    workingDaysSlipped,
  };
}

function groupBy(
  rows: readonly ReportInput[],
  key: (t: ReportInput) => string,
): Map<string, ReportInput[]> {
  const out = new Map<string, ReportInput[]>();
  for (const t of rows) {
    const k = key(t);
    const bucket = out.get(k);
    if (bucket) bucket.push(t);
    else out.set(k, [t]);
  }
  return out;
}

/** Ageing of currently-open tickets, in working days since they were raised. */
export function ageingOf(
  rows: readonly ReportInput[],
  today: IsoDate,
  holidays: ReadonlySet<IsoDate>,
): AgeingBuckets {
  let d0to3 = 0;
  let d4to7 = 0;
  let d8to14 = 0;
  let d15plus = 0;
  for (const t of rows) {
    if (TERMINAL.has(t.status)) continue;
    const age = workingDaysBetween(t.createdDate, today, holidays);
    if (age <= 3) d0to3 += 1;
    else if (age <= 7) d4to7 += 1;
    else if (age <= 14) d8to14 += 1;
    else d15plus += 1;
  }
  return { d0to3, d4to7, d8to14, d15plus };
}

export const UNCATEGORISED = '(uncategorised)';

export function buildReport(
  rows: readonly ReportInput[],
  holidays: ReadonlySet<IsoDate>,
  now: Date,
): Report {
  const today = istDateOf(now);
  const byPerson = [...groupBy(rows, (t) => t.assigneeId)]
    .map(([key, group]) => summarise(key, group, today, holidays))
    // Most overdue first, then most stale, then busiest.
    .sort((a, b) => b.overdue - a.overdue || b.stale - a.stale || b.open - a.open);

  const byCategory = [...groupBy(rows, (t) => t.categoryId ?? UNCATEGORISED)]
    .map(([key, group]) => summarise(key, group, today, holidays))
    .sort((a, b) => b.open - a.open);

  return {
    today,
    overall: summarise('overall', rows, today, holidays),
    byPerson,
    byCategory,
    ageing: ageingOf(rows, today, holidays),
  };
}
