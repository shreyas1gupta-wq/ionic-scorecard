import { describe, it, expect } from 'vitest';
import {
  AMBIGUOUS_KEY,
  DEFAULT_BUDGETS,
  SIZED_FOR_HEADCOUNT,
  InMemoryRateLimitStore,
  RateLimiter,
  checkRateLimit,
  rateLimitHeaders,
  unauthenticatedRequestKey,
  type RateLimitRule,
} from './rate-limit';

// All times below are hand-picked epoch-ms fixtures moved forward explicitly.
// No sleeps, no real timers — `checkRateLimit` takes `now` as a plain argument.
const T0 = 1_000_000_000_000; // an arbitrary fixed instant

const RULE: RateLimitRule = { windowMs: 60_000, max: 3 };

// =============================================================================
describe('checkRateLimit — core algorithm', () => {
  it('allows requests under the limit', async () => {
    const store = new InMemoryRateLimitStore();
    const a = await checkRateLimit(store, 'k', RULE, T0);
    const b = await checkRateLimit(store, 'k', RULE, T0 + 1);
    expect(a.allowed).toBe(true);
    expect(b.allowed).toBe(true);
    expect(a.remaining).toBe(2);
    expect(b.remaining).toBe(1);
  });

  it('allows exactly the request at the limit boundary', async () => {
    const store = new InMemoryRateLimitStore();
    await checkRateLimit(store, 'k', RULE, T0);
    await checkRateLimit(store, 'k', RULE, T0);
    const third = await checkRateLimit(store, 'k', RULE, T0);
    expect(third.allowed).toBe(true);
    expect(third.remaining).toBe(0);
  });

  it('blocks the request that exceeds the limit', async () => {
    const store = new InMemoryRateLimitStore();
    await checkRateLimit(store, 'k', RULE, T0);
    await checkRateLimit(store, 'k', RULE, T0);
    await checkRateLimit(store, 'k', RULE, T0);
    const fourth = await checkRateLimit(store, 'k', RULE, T0);
    expect(fourth.allowed).toBe(false);
    expect(fourth.remaining).toBe(0);
    expect(fourth.retryAfterSeconds).toBeDefined();
  });

  it('keeps blocking further over-limit requests, not just the first one past it', async () => {
    const store = new InMemoryRateLimitStore();
    for (let i = 0; i < RULE.max; i++) await checkRateLimit(store, 'k', RULE, T0);
    const fourth = await checkRateLimit(store, 'k', RULE, T0 + 10);
    const fifth = await checkRateLimit(store, 'k', RULE, T0 + 20);
    expect(fourth.allowed).toBe(false);
    expect(fifth.allowed).toBe(false);
  });

  it('reports retryAfterSeconds only when blocked', async () => {
    const store = new InMemoryRateLimitStore();
    const allowed = await checkRateLimit(store, 'k', RULE, T0);
    expect(allowed.retryAfterSeconds).toBeUndefined();
  });

  it('rolls the window over once windowMs has elapsed, resetting the count', async () => {
    const store = new InMemoryRateLimitStore();
    for (let i = 0; i < RULE.max; i++) await checkRateLimit(store, 'k', RULE, T0);
    const blocked = await checkRateLimit(store, 'k', RULE, T0 + RULE.windowMs - 1);
    expect(blocked.allowed).toBe(false);

    const afterRollover = await checkRateLimit(store, 'k', RULE, T0 + RULE.windowMs);
    expect(afterRollover.allowed).toBe(true);
    expect(afterRollover.remaining).toBe(RULE.max - 1);
  });

  it('does not roll over one millisecond early', async () => {
    const store = new InMemoryRateLimitStore();
    for (let i = 0; i < RULE.max; i++) await checkRateLimit(store, 'k', RULE, T0);
    const stillBlocked = await checkRateLimit(store, 'k', RULE, T0 + RULE.windowMs - 1);
    expect(stillBlocked.allowed).toBe(false);
  });

  it('anchors the new window to the request that triggered rollover, not the old boundary', async () => {
    const store = new InMemoryRateLimitStore();
    await checkRateLimit(store, 'k', RULE, T0);
    const rolledAt = T0 + RULE.windowMs + 5_000;
    const decision = await checkRateLimit(store, 'k', RULE, rolledAt);
    // resetSeconds counts from `rolledAt`, i.e. windowMs away from the new
    // anchor — not from the original T0 window, which is long expired.
    expect(decision.resetSeconds).toBe(RULE.windowMs / 1000);
  });

  it('gives separate keys entirely independent budgets', async () => {
    const store = new InMemoryRateLimitStore();
    for (let i = 0; i < RULE.max; i++) await checkRateLimit(store, 'alice', RULE, T0);
    const aliceBlocked = await checkRateLimit(store, 'alice', RULE, T0);
    const bobAllowed = await checkRateLimit(store, 'bob', RULE, T0);
    expect(aliceBlocked.allowed).toBe(false);
    expect(bobAllowed.allowed).toBe(true);
  });

  it('reports the configured limit on every decision', async () => {
    const store = new InMemoryRateLimitStore();
    const decision = await checkRateLimit(store, 'k', RULE, T0);
    expect(decision.limit).toBe(RULE.max);
  });
});

// =============================================================================
describe('rateLimitHeaders', () => {
  it('always carries RateLimit-Limit/Remaining/Reset', () => {
    const headers = rateLimitHeaders({ allowed: true, limit: 5, remaining: 4, resetSeconds: 30 });
    expect(headers['RateLimit-Limit']).toBe('5');
    expect(headers['RateLimit-Remaining']).toBe('4');
    expect(headers['RateLimit-Reset']).toBe('30');
    expect(headers['Retry-After']).toBeUndefined();
  });

  it('adds Retry-After only when the decision blocked the request', () => {
    const headers = rateLimitHeaders({
      allowed: false,
      limit: 5,
      remaining: 0,
      resetSeconds: 12,
      retryAfterSeconds: 12,
    });
    expect(headers['Retry-After']).toBe('12');
  });
});

// =============================================================================
describe('RateLimiter — read vs mutate budgets', () => {
  it('gives read and mutate independent counters for the same underlying key', async () => {
    const store = new InMemoryRateLimitStore();
    const limiter = new RateLimiter(store, {
      read: { windowMs: 60_000, max: 2 },
      mutate: { windowMs: 60_000, max: 2 },
    });

    await limiter.check('read', 'ip:1.2.3.4', T0);
    await limiter.check('read', 'ip:1.2.3.4', T0);
    const readBlocked = await limiter.check('read', 'ip:1.2.3.4', T0);

    // Same key, different kind: mutate has its own untouched counter.
    const mutateAllowed = await limiter.check('mutate', 'ip:1.2.3.4', T0);

    expect(readBlocked.allowed).toBe(false);
    expect(mutateAllowed.allowed).toBe(true);
  });

  it('applies a materially tighter default budget to mutations than reads', () => {
    expect(DEFAULT_BUDGETS.mutate.max).toBeLessThan(DEFAULT_BUDGETS.read.max);
  });

  /**
   * Guards against reintroducing a real mistake: the first budgets were 120
   * reads/min, sized as though a key were one person. It is not — the key is
   * `CF-Connecting-IP`, and a corporate network egresses through one NAT address,
   * so the budget is shared by the whole firm. Anyone "tightening" these numbers
   * back toward per-person values fails here and reads the comment.
   */
  it('is sized for a whole office behind one NAT address, not one person', () => {
    const busyReadsPerPersonPerMinute = 10;
    const busyMutationsPerPersonPerMinute = 3;

    expect(DEFAULT_BUDGETS.read.max).toBeGreaterThanOrEqual(
      SIZED_FOR_HEADCOUNT * busyReadsPerPersonPerMinute,
    );
    expect(DEFAULT_BUDGETS.mutate.max).toBeGreaterThanOrEqual(
      SIZED_FOR_HEADCOUNT * busyMutationsPerPersonPerMinute,
    );
  });

  it('still bounds a runaway script well below what one could send', () => {
    // The point of a coarse ceiling: normal office traffic never reaches it, but
    // a retry loop doing tens of thousands a minute is stopped.
    expect(DEFAULT_BUDGETS.read.max).toBeLessThan(10_000);
    expect(DEFAULT_BUDGETS.mutate.max).toBeLessThan(2_000);
  });

  it('exhausting the mutate budget does not affect the read budget for the same key', async () => {
    const store = new InMemoryRateLimitStore();
    const limiter = new RateLimiter(store, {
      read: { windowMs: 60_000, max: 5 },
      mutate: { windowMs: 60_000, max: 1 },
    });

    await limiter.check('mutate', 'k', T0);
    const mutateBlocked = await limiter.check('mutate', 'k', T0);
    const readStillFine = await limiter.check('read', 'k', T0);

    expect(mutateBlocked.allowed).toBe(false);
    expect(readStillFine.allowed).toBe(true);
  });
});

// =============================================================================
describe('unauthenticatedRequestKey', () => {
  it('prefers CF-Connecting-IP', () => {
    const headers = new Headers({ 'cf-connecting-ip': '203.0.113.9', 'x-forwarded-for': '10.0.0.1' });
    expect(unauthenticatedRequestKey(headers)).toBe('ip:203.0.113.9');
  });

  it('falls back to the first hop of X-Forwarded-For when CF-Connecting-IP is absent', () => {
    const headers = new Headers({ 'x-forwarded-for': '198.51.100.7, 10.0.0.1' });
    expect(unauthenticatedRequestKey(headers)).toBe('ip:198.51.100.7');
  });

  it('falls back to the shared ambiguous bucket when no IP signal is present at all', () => {
    const headers = new Headers();
    expect(unauthenticatedRequestKey(headers)).toBe(AMBIGUOUS_KEY);
  });

  it('treats an empty CF-Connecting-IP as absent rather than as a literal key', () => {
    const headers = new Headers({ 'cf-connecting-ip': '   ' });
    expect(unauthenticatedRequestKey(headers)).toBe(AMBIGUOUS_KEY);
  });

  it('the ambiguous bucket is one shared key, so ambiguous requests share one budget', async () => {
    // Direct test of the fail-closed-not-a-DoS design: two different callers
    // that both fail to resolve an IP land in the SAME bucket and can exhaust
    // each other's budget — the point being that ambiguity is still governed
    // by the ordinary budget, not exempted from it.
    const store = new InMemoryRateLimitStore();
    const rule: RateLimitRule = { windowMs: 60_000, max: 1 };
    const keyA = unauthenticatedRequestKey(new Headers());
    const keyB = unauthenticatedRequestKey(new Headers({ 'cf-connecting-ip': '' }));
    expect(keyA).toBe(keyB);

    await checkRateLimit(store, keyA, rule, T0);
    const second = await checkRateLimit(store, keyB, rule, T0);
    expect(second.allowed).toBe(false);
  });
});

// =============================================================================
describe('InMemoryRateLimitStore — bounded memory', () => {
  it('never exceeds maxEntries no matter how many distinct keys are written', async () => {
    const store = new InMemoryRateLimitStore(10);
    for (let i = 0; i < 1_000; i++) {
      await store.put(`key-${i}`, { windowStart: T0, count: 1 }, 60_000);
    }
    expect(store.size).toBeLessThanOrEqual(10);
  });

  it('evicts the least-recently-touched key first, not an arbitrary one', async () => {
    const store = new InMemoryRateLimitStore(2);
    await store.put('a', { windowStart: T0, count: 1 }, 60_000);
    await store.put('b', { windowStart: T0, count: 1 }, 60_000);
    // Touch 'a' so it becomes the most-recently-used of the two.
    await store.get('a');
    // Adding a third key must evict 'b' (least-recently-touched), not 'a'.
    await store.put('c', { windowStart: T0, count: 1 }, 60_000);

    expect(await store.get('a')).toBeDefined();
    expect(await store.get('b')).toBeUndefined();
    expect(await store.get('c')).toBeDefined();
    expect(store.size).toBe(2);
  });

  it('rejects a non-positive capacity rather than silently building an unbounded store', () => {
    expect(() => new InMemoryRateLimitStore(0)).toThrow(RangeError);
    expect(() => new InMemoryRateLimitStore(-5)).toThrow(RangeError);
  });

  it('a full, sustained attack from many distinct keys still self-limits via eviction', async () => {
    // Not a timing benchmark — just a structural check that hammering the
    // store with a large number of one-shot keys (the shape of a distributed
    // scan, one request per source before moving on) cannot make it grow past
    // its bound, which is the property the eviction exists to guarantee.
    const store = new InMemoryRateLimitStore(50);
    for (let i = 0; i < 5_000; i++) {
      await checkRateLimit(store, `scanner-${i}`, RULE, T0 + i);
    }
    expect(store.size).toBeLessThanOrEqual(50);
  });
});
