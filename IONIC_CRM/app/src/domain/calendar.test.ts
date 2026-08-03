import { describe, it, expect } from 'vitest';
import {
  assertIsoDate,
  istDateOf,
  addDays,
  dayOfWeek,
  isWeekend,
  isWorkingDay,
  addWorkingDays,
  workingDaysBetween,
  type IsoDate,
} from './calendar';

/** 2026 Indian holidays used as fixtures. Real list is admin-maintained in the DB. */
const HOLIDAYS: ReadonlySet<IsoDate> = new Set([
  '2026-08-15', // Independence Day — a Saturday in 2026
  '2026-10-02', // Gandhi Jayanti — a Friday
  '2026-11-09', // stand-in for Diwali — a Monday
]);
const NONE: ReadonlySet<IsoDate> = new Set();

describe('assertIsoDate', () => {
  it('accepts a real date', () => {
    expect(assertIsoDate('2026-08-03')).toBe('2026-08-03');
  });

  it.each(['2026-8-03', '03-08-2026', '2026/08/03', '20260803', '', 'today'])(
    'rejects malformed %j',
    (bad) => {
      expect(() => assertIsoDate(bad)).toThrow(/not an ISO date/);
    },
  );

  it('rejects dates that do not exist, rather than silently rolling over', () => {
    // new Date(Date.UTC(2026, 1, 30)) rolls to 2 March. Round-tripping catches it.
    expect(() => assertIsoDate('2026-02-30')).toThrow(/not a real calendar date/);
    expect(() => assertIsoDate('2026-13-01')).toThrow(/not a real calendar date/);
  });

  it('accepts a leap day in a leap year and rejects it otherwise', () => {
    expect(assertIsoDate('2028-02-29')).toBe('2028-02-29');
    expect(() => assertIsoDate('2026-02-29')).toThrow(/not a real calendar date/);
  });
});

describe('istDateOf — the timezone boundary', () => {
  // IST is UTC+05:30, so the IST day rolls over at 18:30 UTC the previous day.
  // This is the exact bug class that has bitten this codebase before: a UTC-stamped
  // instant after 18:30 belongs to the NEXT Indian calendar day.
  it('treats 18:29:59Z as still the same IST day', () => {
    expect(istDateOf(new Date('2026-08-03T18:29:59.999Z'))).toBe('2026-08-03');
  });

  it('rolls to the next IST day at exactly 18:30:00Z', () => {
    expect(istDateOf(new Date('2026-08-03T18:30:00.000Z'))).toBe('2026-08-04');
  });

  it('maps UTC midnight to the same IST calendar day', () => {
    // 00:00Z = 05:30 IST, same date.
    expect(istDateOf(new Date('2026-08-03T00:00:00Z'))).toBe('2026-08-03');
  });

  it('crosses a month boundary correctly', () => {
    expect(istDateOf(new Date('2026-08-31T18:30:00Z'))).toBe('2026-09-01');
  });

  it('crosses a year boundary correctly', () => {
    expect(istDateOf(new Date('2026-12-31T18:30:00Z'))).toBe('2027-01-01');
  });

  it('does not depend on the machine timezone', () => {
    // Reading local fields instead of shifted-UTC fields would make this vary by host.
    // Asserting a fixed expectation is the regression guard.
    expect(istDateOf(new Date(Date.UTC(2026, 7, 3, 20, 0, 0)))).toBe('2026-08-04');
  });
});

describe('addDays', () => {
  it('advances and rewinds', () => {
    expect(addDays('2026-08-03', 1)).toBe('2026-08-04');
    expect(addDays('2026-08-03', -1)).toBe('2026-08-02');
    expect(addDays('2026-08-03', 0)).toBe('2026-08-03');
  });

  it('crosses month, year and leap-day boundaries', () => {
    expect(addDays('2026-08-31', 1)).toBe('2026-09-01');
    expect(addDays('2026-12-31', 1)).toBe('2027-01-01');
    expect(addDays('2028-02-28', 1)).toBe('2028-02-29');
    expect(addDays('2026-02-28', 1)).toBe('2026-03-01');
  });
});

describe('weekends and working days', () => {
  it('knows the days of the week', () => {
    expect(dayOfWeek('2026-08-03')).toBe(1); // Monday
    expect(dayOfWeek('2026-08-08')).toBe(6); // Saturday
    expect(dayOfWeek('2026-08-09')).toBe(0); // Sunday
  });

  it('treats Saturday and Sunday as non-working', () => {
    expect(isWeekend('2026-08-08')).toBe(true);
    expect(isWeekend('2026-08-09')).toBe(true);
    expect(isWorkingDay('2026-08-08', NONE)).toBe(false);
    expect(isWorkingDay('2026-08-09', NONE)).toBe(false);
  });

  it('treats an injected holiday as non-working', () => {
    expect(isWorkingDay('2026-10-02', NONE)).toBe(true);
    expect(isWorkingDay('2026-10-02', HOLIDAYS)).toBe(false);
  });
});

describe('addWorkingDays', () => {
  it('returns the same day for n = 0, even on a weekend', () => {
    expect(addWorkingDays('2026-08-08', 0, HOLIDAYS)).toBe('2026-08-08');
  });

  it('skips the weekend', () => {
    // Friday + 1 working day = Monday.
    expect(addWorkingDays('2026-08-07', 1, NONE)).toBe('2026-08-10');
  });

  it('skips a holiday', () => {
    // Thu 2026-10-01 + 1 working day: Fri 10-02 is a holiday, so Mon 10-05.
    expect(addWorkingDays('2026-10-01', 1, HOLIDAYS)).toBe('2026-10-05');
  });

  it('skips a holiday that falls on a Monday', () => {
    // Fri 2026-11-06 + 1: Mon 11-09 is a holiday, so Tue 11-10.
    expect(addWorkingDays('2026-11-06', 1, HOLIDAYS)).toBe('2026-11-10');
  });

  it('walks backwards', () => {
    expect(addWorkingDays('2026-08-10', -1, NONE)).toBe('2026-08-07');
  });

  it('accumulates across several weeks', () => {
    // Mon 2026-08-03 + 10 working days = Mon 2026-08-17 (no holidays in NONE).
    expect(addWorkingDays('2026-08-03', 10, NONE)).toBe('2026-08-17');
  });

  it('rejects a non-integer', () => {
    expect(() => addWorkingDays('2026-08-03', 1.5, NONE)).toThrow(/integer/);
  });

  /** A run of `days` consecutive holidays starting the day after `from`. */
  function holidayRun(from: IsoDate, days: number): Set<IsoDate> {
    const s = new Set<IsoDate>();
    let d = from;
    for (let i = 0; i < days; i++) {
      d = addDays(d, 1);
      s.add(d);
    }
    return s;
  }

  it('walks past a long but finite holiday run rather than giving up', () => {
    // A two-year shutdown is absurd, but the function should still return the right
    // answer rather than bail — the convergence guard is for genuine pathology only.
    const shutdown = holidayRun('2025-12-31', 800);
    const result = addWorkingDays('2026-01-01', 5, shutdown);
    expect(result > '2028-01-01').toBe(true);
    expect(isWorkingDay(result, shutdown)).toBe(true);
  });

  it('throws instead of hanging when no working day exists within the bound', () => {
    // The guard allows |n|*10 + 3660 iterations (~10 years), so the holiday run has to
    // exceed that to prove the guard actually fires.
    const forever = holidayRun('2025-12-31', 4000);
    expect(() => addWorkingDays('2026-01-01', 5, forever)).toThrow(/did not converge/);
  });
});

describe('workingDaysBetween', () => {
  it('counts days strictly after `from`, up to and including `to`', () => {
    expect(workingDaysBetween('2026-08-03', '2026-08-04', NONE)).toBe(1);
    expect(workingDaysBetween('2026-08-03', '2026-08-03', NONE)).toBe(0);
  });

  it('is zero when `to` precedes `from` — elapsed time is never negative here', () => {
    expect(workingDaysBetween('2026-08-05', '2026-08-03', NONE)).toBe(0);
  });

  it('excludes the weekend', () => {
    // Friday to Monday is one working day.
    expect(workingDaysBetween('2026-08-07', '2026-08-10', NONE)).toBe(1);
  });

  it('excludes a holiday in the span', () => {
    // Thu 10-01 → Mon 10-05: Fri 10-02 holiday, weekend, Mon counts. So 1.
    expect(workingDaysBetween('2026-10-01', '2026-10-05', HOLIDAYS)).toBe(1);
    expect(workingDaysBetween('2026-10-01', '2026-10-05', NONE)).toBe(2);
  });

  it('counts a full working week as 5', () => {
    expect(workingDaysBetween('2026-08-02', '2026-08-07', NONE)).toBe(5);
  });
});
