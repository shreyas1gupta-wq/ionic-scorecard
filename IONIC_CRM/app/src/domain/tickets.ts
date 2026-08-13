/**
 * Ticket state rules: which transitions are legal, who may make them, and the
 * derived facts (overdue, stale, on-time) that the dashboards report.
 *
 * Everything here is a pure function of state plus an explicitly-passed "today".
 * Nothing reads the clock. That is what makes the midnight and timezone cases
 * testable rather than hopeful.
 */

import { type IsoDate, workingDaysBetween } from './calendar';

export type Role = 'EMPLOYEE' | 'MANAGER' | 'ADMIN';

export type Priority = 'P1' | 'P2' | 'P3';

export type TicketStatus =
  | 'OPEN'
  | 'IN_PROGRESS'
  | 'BLOCKED'
  | 'DONE'
  | 'CANCELLED';

/** Terminal states stop the clock: they are never overdue and never stale. */
const TERMINAL: ReadonlySet<TicketStatus> = new Set<TicketStatus>(['DONE', 'CANCELLED']);

export function isTerminal(s: TicketStatus): boolean {
  return TERMINAL.has(s);
}

/**
 * Working days without a punch before a ticket is flagged stale.
 * P1 = 1 means a P1 must be punched every working day.
 */
export const STALE_THRESHOLD_WORKING_DAYS: Readonly<Record<Priority, number>> = {
  P1: 1,
  P2: 3,
  P3: 5,
};

/** Who may perform a transition, beyond the ticket's assignee. */
export type TransitionActor = 'ASSIGNEE' | 'RAISER' | 'MANAGER' | 'ADMIN';

interface Transition {
  readonly from: TicketStatus;
  readonly to: TicketStatus;
  readonly allowed: ReadonlySet<TransitionActor>;
  /** A human-readable reason is mandatory on the record for these moves. */
  readonly requiresReason: boolean;
}

const A = (...xs: TransitionActor[]) => new Set<TransitionActor>(xs);

/**
 * The complete transition table. Anything absent from this list is illegal —
 * the function below is deny-by-default, so adding a status without adding its
 * transitions makes it unreachable rather than unguarded.
 */
const TRANSITIONS: readonly Transition[] = [
  { from: 'OPEN',        to: 'IN_PROGRESS', allowed: A('ASSIGNEE', 'MANAGER', 'ADMIN'),           requiresReason: false },
  { from: 'IN_PROGRESS', to: 'BLOCKED',     allowed: A('ASSIGNEE', 'MANAGER', 'ADMIN'),           requiresReason: true  },
  { from: 'BLOCKED',     to: 'IN_PROGRESS', allowed: A('ASSIGNEE', 'MANAGER', 'ADMIN'),           requiresReason: false },
  { from: 'IN_PROGRESS', to: 'DONE',        allowed: A('ASSIGNEE', 'MANAGER', 'ADMIN'),           requiresReason: false },
  // Reopen. Deliberately NOT available to the assignee: a person should not be able
  // to un-finish their own work without a manager, or "done" means nothing.
  { from: 'DONE',        to: 'IN_PROGRESS', allowed: A('MANAGER', 'ADMIN'),                       requiresReason: true  },
  { from: 'OPEN',        to: 'CANCELLED',   allowed: A('RAISER', 'MANAGER', 'ADMIN'),             requiresReason: true  },
  { from: 'IN_PROGRESS', to: 'CANCELLED',   allowed: A('RAISER', 'MANAGER', 'ADMIN'),             requiresReason: true  },
  { from: 'BLOCKED',     to: 'CANCELLED',   allowed: A('RAISER', 'MANAGER', 'ADMIN'),             requiresReason: true  },
];

export type TransitionCheck =
  | { readonly ok: true; readonly requiresReason: boolean }
  | { readonly ok: false; readonly reason: string };

/**
 * Is this status change legal for this actor?
 *
 * `actors` is the set of relationships the acting person has to THIS ticket —
 * they may be both its assignee and an admin. Callers compute that set; this
 * function does not guess.
 */
export function checkTransition(
  from: TicketStatus,
  to: TicketStatus,
  actors: ReadonlySet<TransitionActor>,
): TransitionCheck {
  if (from === to) {
    return { ok: false, reason: `already ${from}` };
  }
  const t = TRANSITIONS.find((x) => x.from === from && x.to === to);
  if (!t) {
    return { ok: false, reason: `illegal transition ${from} -> ${to}` };
  }
  const permitted = [...t.allowed].some((a) => actors.has(a));
  if (!permitted) {
    return {
      ok: false,
      reason: `${from} -> ${to} requires one of: ${[...t.allowed].join(', ')}`,
    };
  }
  return { ok: true, requiresReason: t.requiresReason };
}

/**
 * Every status this actor may legally move the ticket to, right now.
 *
 * Derived from the same table `checkTransition` uses, so a UI built on this can
 * never offer an option the service would then reject — and adding a transition
 * in one place cannot leave the other stale.
 */
export function legalTransitions(
  from: TicketStatus,
  actors: ReadonlySet<TransitionActor>,
): TicketStatus[] {
  return TRANSITIONS.filter((t) => t.from === from)
    .filter((t) => [...t.allowed].some((a) => actors.has(a)))
    .map((t) => t.to);
}

export interface OverdueInput {
  readonly deadline: IsoDate;
  readonly status: TicketStatus;
}

/**
 * Overdue is computed at read time from a passed-in today, never written by a
 * scheduled job. A job that stamps "overdue" at midnight is wrong twice: once for
 * whoever runs it in the wrong timezone, and once whenever it fails to run.
 */
export function isOverdue(t: OverdueInput, todayIst: IsoDate): boolean {
  if (isTerminal(t.status)) return false;
  return todayIst > t.deadline;
}

export interface StaleInput {
  readonly status: TicketStatus;
  readonly priority: Priority;
  /** Date of the most recent punch, or the ticket's creation date if never punched. */
  readonly lastActivityDate: IsoDate;
}

/**
 * Stale = in flight but silent. Only IN_PROGRESS and BLOCKED can go stale; an OPEN
 * ticket nobody has started is a scheduling problem, not a reporting-discipline one.
 */
export function isStale(
  t: StaleInput,
  todayIst: IsoDate,
  holidays: ReadonlySet<IsoDate>,
): boolean {
  if (t.status !== 'IN_PROGRESS' && t.status !== 'BLOCKED') return false;
  const elapsed = workingDaysBetween(t.lastActivityDate, todayIst, holidays);
  return elapsed >= STALE_THRESHOLD_WORKING_DAYS[t.priority];
}

export interface OnTimeInput {
  readonly status: TicketStatus;
  readonly deadline: IsoDate;
  readonly originalDeadline: IsoDate;
  readonly closedDate: IsoDate | null;
}

export interface OnTimeResult {
  /** Met the deadline as it stood at closing time. */
  readonly againstCurrent: boolean;
  /** Met the deadline as first promised. This is the honest number. */
  readonly againstOriginal: boolean;
  /** Working days the deadline was pushed out. 0 if never moved. */
  readonly slippedBy: number;
}

/**
 * Both numbers are reported, always. A tool that only measures performance against
 * the current deadline measures nothing, because the current deadline can be moved.
 * The gap between the two figures is the interesting metric.
 *
 * Only DONE tickets are evaluated — cancelled work was never delivered, and counting
 * a cancellation as "on time" would let anyone hit 100% by cancelling.
 */
export function evaluateOnTime(
  t: OnTimeInput,
  holidays: ReadonlySet<IsoDate>,
): OnTimeResult | null {
  if (t.status !== 'DONE' || t.closedDate === null) return null;
  return {
    againstCurrent: t.closedDate <= t.deadline,
    againstOriginal: t.closedDate <= t.originalDeadline,
    slippedBy: workingDaysBetween(t.originalDeadline, t.deadline, holidays),
  };
}
