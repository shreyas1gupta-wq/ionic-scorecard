/**
 * Calendar arithmetic for IST business dates.
 *
 * Deadlines in this system are CALENDAR DATES, not instants. "Due 2026-08-14" means
 * end of that day in India, and it means the same thing regardless of where the server
 * or the reader happens to be. Representing them as `Date` objects is what creates the
 * entire class of off-by-one-day bugs, so we don't: an `IsoDate` string is the type.
 *
 * ISO `YYYY-MM-DD` strings also compare correctly with `<` and `>`, which is why
 * `isOverdue` can be a string comparison instead of date maths.
 */

/** An IST calendar date, `YYYY-MM-DD`. Lexicographically ordered. */
export type IsoDate = string;

/**
 * India is UTC+05:30 and has never observed daylight saving. A fixed offset is
 * therefore correct here — which is emphatically NOT true for most timezones, so
 * don't lift this constant into a general-purpose date library.
 */
const IST_OFFSET_MS = (5 * 60 + 30) * 60 * 1000;

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export function assertIsoDate(d: string): IsoDate {
  if (!ISO_DATE_RE.test(d)) {
    throw new Error(`not an ISO date (YYYY-MM-DD): ${JSON.stringify(d)}`);
  }
  // Reject 2026-02-30 and friends: round-tripping catches Date's silent rollover.
  if (formatUtcMidnight(parseUtcMidnight(d)) !== d) {
    throw new Error(`not a real calendar date: ${d}`);
  }
  return d;
}

/**
 * The IST calendar date an instant falls on.
 *
 * Shift the instant by the IST offset, then read UTC fields. Reading *local* fields
 * would make the result depend on the machine's timezone, which is exactly the bug
 * this function exists to prevent.
 */
export function istDateOf(instant: Date): IsoDate {
  return formatUtcMidnight(new Date(instant.getTime() + IST_OFFSET_MS));
}

function parseUtcMidnight(d: IsoDate): Date {
  const y = Number(d.slice(0, 4));
  const m = Number(d.slice(5, 7));
  const day = Number(d.slice(8, 10));
  return new Date(Date.UTC(y, m - 1, day));
}

function formatUtcMidnight(dt: Date): IsoDate {
  const y = String(dt.getUTCFullYear()).padStart(4, '0');
  const m = String(dt.getUTCMonth() + 1).padStart(2, '0');
  const d = String(dt.getUTCDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function addDays(d: IsoDate, n: number): IsoDate {
  const dt = parseUtcMidnight(d);
  dt.setUTCDate(dt.getUTCDate() + n);
  return formatUtcMidnight(dt);
}

/** 0 = Sunday … 6 = Saturday. */
export function dayOfWeek(d: IsoDate): number {
  return parseUtcMidnight(d).getUTCDay();
}

export function isWeekend(d: IsoDate): boolean {
  const dow = dayOfWeek(d);
  return dow === 0 || dow === 6;
}

/**
 * Holidays are always INJECTED, never read from a module-level constant or a network
 * call. The firm maintains its own list (see REQUIREMENTS §5) precisely so that this
 * function has no hidden dependency that can go stale.
 */
export function isWorkingDay(d: IsoDate, holidays: ReadonlySet<IsoDate>): boolean {
  return !isWeekend(d) && !holidays.has(d);
}

/**
 * The date `n` working days after `start`.
 *
 * `n = 0` returns `start` unchanged even if `start` is itself a holiday — callers
 * asking for "zero working days later" are asking for the same day, not the next
 * working one. Negative `n` walks backwards.
 */
export function addWorkingDays(
  start: IsoDate,
  n: number,
  holidays: ReadonlySet<IsoDate>,
): IsoDate {
  if (!Number.isInteger(n)) throw new Error(`n must be an integer, got ${n}`);
  if (n === 0) return start;

  const step = n > 0 ? 1 : -1;
  let remaining = Math.abs(n);
  let cursor = start;

  // Bounded so a pathological holiday set can't hang the process.
  const maxIterations = Math.abs(n) * 10 + 3660;
  for (let i = 0; remaining > 0; i++) {
    if (i > maxIterations) {
      throw new Error(`addWorkingDays did not converge from ${start} (n=${n})`);
    }
    cursor = addDays(cursor, step);
    if (isWorkingDay(cursor, holidays)) remaining--;
  }
  return cursor;
}

/**
 * Working days strictly after `from`, up to and including `to`.
 *
 * So Monday→Tuesday is 1, Monday→Monday is 0, and Friday→Monday is 1. Returns 0 when
 * `to` is not after `from`; elapsed time is never negative in this system's use of it.
 */
export function workingDaysBetween(
  from: IsoDate,
  to: IsoDate,
  holidays: ReadonlySet<IsoDate>,
): number {
  if (to <= from) return 0;
  let count = 0;
  let cursor = from;
  while (cursor < to) {
    cursor = addDays(cursor, 1);
    if (isWorkingDay(cursor, holidays)) count++;
  }
  return count;
}
