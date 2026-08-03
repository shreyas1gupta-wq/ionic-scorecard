import { describe, it, expect } from 'vitest';
import { formatTicketRef, parseTicketRef } from './ticket-ref';

describe('formatTicketRef', () => {
  it('pads to four digits', () => {
    expect(formatTicketRef(2026, 1)).toBe('TKT-2026-0001');
    expect(formatTicketRef(2026, 42)).toBe('TKT-2026-0042');
    expect(formatTicketRef(2026, 9999)).toBe('TKT-2026-9999');
  });

  it('grows past four digits rather than colliding', () => {
    // Truncating to 4 digits would make ticket 10000 collide with ticket 0000.
    expect(formatTicketRef(2026, 10000)).toBe('TKT-2026-10000');
  });

  it('rejects a zero or negative sequence', () => {
    expect(() => formatTicketRef(2026, 0)).toThrow(/positive integer/);
    expect(() => formatTicketRef(2026, -1)).toThrow(/positive integer/);
  });

  it('rejects a non-integer sequence', () => {
    expect(() => formatTicketRef(2026, 1.5)).toThrow(/positive integer/);
  });

  it('rejects an implausible year', () => {
    expect(() => formatTicketRef(26, 1)).toThrow(/implausible year/);
    expect(() => formatTicketRef(12026, 1)).toThrow(/implausible year/);
  });
});

describe('parseTicketRef', () => {
  it('round-trips', () => {
    for (const [y, s] of [
      [2026, 1],
      [2026, 9999],
      [2030, 10000],
    ] as const) {
      expect(parseTicketRef(formatTicketRef(y, s))).toEqual({ year: y, sequence: s });
    }
  });

  it('tolerates surrounding whitespace and lower case, as people paste it', () => {
    expect(parseTicketRef('  tkt-2026-0007 ')).toEqual({ year: 2026, sequence: 7 });
  });

  it.each(['TKT-2026-1', 'TKT-26-0001', '2026-0001', 'TKT-2026', 'TKT_2026_0001', ''])(
    'returns null for malformed %j',
    (bad) => {
      expect(parseTicketRef(bad)).toBeNull();
    },
  );
});
