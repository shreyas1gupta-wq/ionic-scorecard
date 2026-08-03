/**
 * Rate limiting — fixed-window counters behind a tiny storage interface.
 *
 * CSCRF requires "rate limiting, throttling, and proper authentication and
 * authorisation mechanisms" for APIs at regulated entities (DESIGN.md §8). This
 * module is the first half of that sentence; auth is `src/auth/`'s job, not this
 * file's — see `middleware.ts` for why the two stay separate.
 *
 * FIXED WINDOW, NOT TOKEN BUCKET. A token bucket smooths bursts better, but it
 * needs a fractional-refill calculation on every check and gets more subtle to
 * reason about under a clock that only advances between calls (as in the tests
 * here — no real timers). A fixed window is exact with integer arithmetic, maps
 * losslessly onto the `RateLimit-Reset` header, and is more than enough
 * precision for 10-50 employees doing ticket work. The one known weakness of a
 * fixed window — up to 2x the budget in a burst that straddles a window
 * boundary — is deliberately not fought here: windows are anchored to the first
 * request after expiry rather than wall-clock-aligned buckets, so there is no
 * shared epoch boundary for a client to time against. That halves the usual
 * attack, not eliminates it, which is an acceptable trade for the size of this
 * app.
 */

// =============================================================================
// Storage seam
// =============================================================================

/** One fixed window's state for one key. */
export interface RateLimitWindow {
  /** Epoch ms marking when this window started. */
  readonly windowStart: number;
  /** Requests counted in this window so far. */
  readonly count: number;
}

/**
 * Storage seam, kept deliberately as small as a Cloudflare KV namespace or a
 * Durable Object's storage can satisfy — the method names mirror KV's own
 * `get`/`put` on purpose, so a real adapter is close to a passthrough rather
 * than a translation layer. `checkRateLimit` below never learns which backing
 * it is talking to, which is the whole point: replace `InMemoryRateLimitStore`
 * with a KV/DO adapter later and no caller of `checkRateLimit` or `RateLimiter`
 * changes.
 */
export interface RateLimitStore {
  get(key: string): Promise<RateLimitWindow | undefined>;
  /**
   * `ttlMs` is advisory, for a backing that supports native expiry (KV's
   * `expirationTtl`). The in-memory store below ignores it — see its own
   * comment for why bounded eviction is used instead of a timer.
   */
  put(key: string, value: RateLimitWindow, ttlMs: number): Promise<void>;
}

/**
 * In-memory storage — one process, one Map, capacity-bounded.
 *
 * No timer-based expiry, ever. A Worker isolate is not guaranteed to execute
 * anything outside of handling a request; a `setInterval` sweep might simply
 * never fire, and code that depends on it would be worse than code that
 * doesn't, because it *looks* like it bounds memory without actually doing so.
 * Instead, eviction is bounded by `maxEntries` on every write, least-recently-
 * touched key first (`Map` preserves insertion order, so re-inserting a touched
 * key moves it to the most-recently-used end for free). That makes "memory does
 * not grow without bound" a property that holds by construction for every
 * traffic shape — not one that happens to hold for the shapes a sweep interval
 * was tested against.
 */
export class InMemoryRateLimitStore implements RateLimitStore {
  private readonly windows = new Map<string, RateLimitWindow>();

  constructor(private readonly maxEntries: number = 10_000) {
    if (maxEntries <= 0) throw new RangeError('maxEntries must be positive');
  }

  /** Test-only visibility into the bound; not part of the `RateLimitStore` contract. */
  get size(): number {
    return this.windows.size;
  }

  async get(key: string): Promise<RateLimitWindow | undefined> {
    const value = this.windows.get(key);
    if (value === undefined) return undefined;
    this.windows.delete(key);
    this.windows.set(key, value);
    return value;
  }

  /** `ttlMs` accepted for interface parity with `RateLimitStore`; unused here — see the class comment above for why. */
  async put(key: string, value: RateLimitWindow, ttlMs?: number): Promise<void> {
    void ttlMs;
    this.windows.delete(key);
    this.windows.set(key, value);
    while (this.windows.size > this.maxEntries) {
      const oldest = this.windows.keys().next().value;
      if (oldest === undefined) break;
      this.windows.delete(oldest);
    }
  }
}

// =============================================================================
// Algorithm
// =============================================================================

export interface RateLimitRule {
  readonly windowMs: number;
  readonly max: number;
}

export interface RateLimitDecision {
  readonly allowed: boolean;
  readonly limit: number;
  readonly remaining: number;
  /** Seconds until the current window resets, rounded up. */
  readonly resetSeconds: number;
  /** Present only when `allowed` is false. */
  readonly retryAfterSeconds?: number;
}

/**
 * Check and record one request against one key's fixed window.
 *
 * `now` is a caller-supplied epoch-ms timestamp, never read from the clock
 * inside this function — that is what lets the tests move time forward without
 * a single sleep or real timer, and it is what lets `middleware.ts` pass the
 * same `Date.now()` it already has rather than this module taking its own,
 * possibly-different, reading.
 */
export async function checkRateLimit(
  store: RateLimitStore,
  key: string,
  rule: RateLimitRule,
  now: number,
): Promise<RateLimitDecision> {
  const existing = await store.get(key);
  const windowExpired = existing === undefined || now - existing.windowStart >= rule.windowMs;

  const windowStart = windowExpired ? now : existing.windowStart;
  const countSoFar = windowExpired ? 0 : existing.count;

  const resetSeconds = Math.max(0, Math.ceil((windowStart + rule.windowMs - now) / 1000));

  if (countSoFar >= rule.max) {
    return {
      allowed: false,
      limit: rule.max,
      remaining: 0,
      resetSeconds,
      retryAfterSeconds: resetSeconds,
    };
  }

  const newCount = countSoFar + 1;
  await store.put(key, { windowStart, count: newCount }, rule.windowMs);

  return {
    allowed: true,
    limit: rule.max,
    remaining: rule.max - newCount,
    resetSeconds,
  };
}

/** The `RateLimit-*` / `Retry-After` headers a caller needs to act on a decision. */
export function rateLimitHeaders(decision: RateLimitDecision): Record<string, string> {
  const headers: Record<string, string> = {
    'RateLimit-Limit': String(decision.limit),
    'RateLimit-Remaining': String(decision.remaining),
    'RateLimit-Reset': String(decision.resetSeconds),
  };
  if (decision.retryAfterSeconds !== undefined) {
    headers['Retry-After'] = String(decision.retryAfterSeconds);
  }
  return headers;
}

// =============================================================================
// Budgets and the request-kind split
// =============================================================================

export type RequestKind = 'read' | 'mutate';

export interface RateLimitBudgets {
  readonly read: RateLimitRule;
  readonly mutate: RateLimitRule;
}

/**
 * CSCRF requires rate limiting; it does not hand down numbers. These are sized
 * for 10-50 employees doing normal ticket work — not public traffic: generous
 * enough that a person clicking through the app all day never notices, tight
 * enough that a runaway script, a buggy retry loop, or a compromised session
 * cannot hammer the append-only writer or the database behind it. Mutating
 * requests get a materially tighter budget than reads because every mutation is
 * a database write plus an audit-chain append under a lock (`DESIGN.md` §6) —
 * the thing actually worth protecting is write throughput, not page views.
 *
 * CORRECTED 2026-08-03 — THE FIRST NUMBERS WERE WRONG FOR THIS FIRM.
 *
 * They were 120 reads and 20 mutations per minute, sized as though a key were one
 * person. It is not: this limiter keys by `CF-Connecting-IP`, and a corporate
 * network egresses through a single NAT address. So "per IP" is really "per
 * firm" — fifty employees at ten requests a minute is 500 from one address,
 * against a ceiling of 120. The limiter would have started refusing ordinary
 * work on a busy morning, which is a self-inflicted outage rather than a control.
 *
 * These are therefore a COARSE FLOOD GUARD, not a per-person quota: high enough
 * that the whole office working normally never approaches them, low enough to
 * stop a runaway retry loop or a scripted scrape from reaching the append-only
 * writer thousands of times a minute.
 *
 * The genuine per-person control is a SECOND LAYER that does not exist yet: a
 * budget applied at an authenticated call site, where a verified employee id is
 * already in hand (`app/tickets/actions.ts`). Recorded as outstanding rather
 * than implied to be covered here — this layer cannot do it, because at
 * middleware time there is no verified identity to key on.
 */
export const DEFAULT_BUDGETS: RateLimitBudgets = {
  read: { windowMs: 60_000, max: 2_000 },
  mutate: { windowMs: 60_000, max: 400 },
};

/**
 * Headcount the default budgets are sized for. Used by the test that stops the
 * NAT mistake above from being reintroduced by someone "tightening" the numbers.
 */
export const SIZED_FOR_HEADCOUNT = 50;

/**
 * Wires a store to the two budgets and namespaces keys by request kind, so a
 * key that happens to collide between a read check and a mutate check for the
 * same caller (or between two `RateLimiter` instances sharing one store, as
 * tests do) can never share a counter.
 */
export class RateLimiter {
  constructor(
    private readonly store: RateLimitStore,
    private readonly budgets: RateLimitBudgets = DEFAULT_BUDGETS,
  ) {}

  async check(kind: RequestKind, key: string, now: number): Promise<RateLimitDecision> {
    const rule = this.budgets[kind];
    return checkRateLimit(this.store, `${kind}:${key}`, rule, now);
  }
}

// =============================================================================
// Keying a request that has not been authenticated yet
// =============================================================================

/**
 * The key for a request with no determinable client IP.
 *
 * Two wrong answers were available, and both are worth naming.
 *
 * Fail OPEN — skip the limit entirely when the key is unknown — turns "I can't
 * identify you" into "you have no limit", which is exactly backwards for a
 * security control: the client best placed to evade rate limiting would be the
 * one whose request looks least like a normal one.
 *
 * Fail CLOSED in the strict sense — refuse the request outright whenever a key
 * can't be determined — is wrong in a different way. On the deployed path
 * Cloudflare's edge always sets `CF-Connecting-IP` (see
 * `unauthenticatedRequestKey` below), so this branch should be unreachable in
 * production. But "should be unreachable" is not a property to bet the app's
 * availability on: if a header rename, a platform change, or a misconfigured
 * proxy ever made it common, an outright refusal would turn one bug into total
 * downtime for every user — a self-inflicted denial of service larger than any
 * abuse this module exists to stop.
 *
 * The resolution: every ambiguous-key request lands in ONE shared bucket, held
 * to the same budgets as any other key — nothing here exempts it. It is still
 * genuinely rate-limited: an attacker who strips their identifying headers
 * gains nothing, because the shared bucket fills exactly as fast as a normal
 * one and then blocks every request routed into it, itself included. What is
 * avoided is a hard-coded refusal wired to a condition ("the key is missing")
 * that must never misfire, because eventually every such condition does.
 */
export const AMBIGUOUS_KEY = 'ambiguous';

/**
 * Resolve the rate-limit key for a request the app has not yet authenticated.
 *
 * Only `CF-Connecting-IP` is trusted. Cloudflare's edge sets it from the
 * terminated TCP connection and overwrites any client-supplied header of the
 * same name — on the one path Access allows through (DESIGN.md §2.2), it
 * cannot be spoofed by anyone but Cloudflare itself. `X-Forwarded-For` is tried
 * second, purely for local development where nothing is fronted by Cloudflare
 * and no signal is trustworthy anyway; it is not expected to be reached in
 * production.
 *
 * Deliberately NOT reading `Cf-Access-Jwt-Assertion` here, even though it
 * usually carries an email that would make a more precise key. This module runs
 * before `src/auth` verifies that token (see `middleware.ts`), so at this point
 * the header is exactly what `access.ts`'s own comment warns about: "just a
 * header... anything that can reach the origin can set it." Trusting it for
 * keying would let one attacker mint a fresh unverified identity per request
 * and receive a fresh rate-limit budget every time — not a mis-partition but a
 * complete bypass of the limiter. A verified identity is a legitimate,
 * better-than-IP key for a rate limiter; it just is not available yet at this
 * point in the request pipeline, so it is not used here. (Nothing prevents an
 * authenticated call site — a server action, once it holds a verified actor id
 * — from calling `RateLimiter.check` again with `user:<id>` as the key for a
 * tighter per-person budget layered on top of this one; that is future work,
 * out of this milestone's scope, and this module's key-agnostic API is what
 * would make it a one-line addition rather than a rewrite.)
 */
export function unauthenticatedRequestKey(headers: Headers): string {
  const cfIp = headers.get('cf-connecting-ip')?.trim();
  if (cfIp) return `ip:${cfIp}`;

  const forwarded = headers.get('x-forwarded-for')?.trim();
  if (forwarded) {
    const first = forwarded.split(',')[0]?.trim();
    if (first) return `ip:${first}`;
  }

  return AMBIGUOUS_KEY;
}
