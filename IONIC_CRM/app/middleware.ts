/**
 * Rate-limiting pre-filter. Runs before any page, layout or server action.
 *
 * THIS FILE DOES NOT AUTHENTICATE ANYONE. That is `src/auth/`'s job — it
 * verifies the Cloudflare Access JWT against Cloudflare's published keys and
 * resolves the identity to an active employee (`src/auth/identity.ts`). Doing
 * any of that here would duplicate a security-critical check in a second place,
 * which is exactly how the two copies eventually disagree. This file only
 * decides, cheaply and before any of that work runs, whether a request gets to
 * proceed at all.
 *
 * WHY THE LIMITER CANNOT KEY BY IDENTITY HERE: identity is not known yet — that
 * is the previous paragraph, not an oversight. `unauthenticatedRequestKey` (see
 * `src/security/rate-limit.ts`) keys by `CF-Connecting-IP`, the one signal at
 * this point in the pipeline that Cloudflare's edge sets itself and a client
 * cannot spoof on the deployed path. A verified per-employee budget is a
 * reasonable future addition at an authenticated call site (a server action
 * that already holds a verified actor id), layered on top of this one — not a
 * replacement for it, since this filter's whole purpose is to do its job before
 * that identity exists.
 *
 * WHY IN-MEMORY IS ACCEPTABLE HERE, WITH A LIMITATION STATED PLAINLY: the store
 * held in module scope survives across requests only within one warm Worker
 * isolate, not globally. Cloudflare may run several isolates concurrently
 * across colos (or spin up a fresh one on a cold start), each with its own Map
 * and its own counters — so the effective global ceiling is the configured
 * budget multiplied by however many isolates happen to be warm, not a single
 * hard cap. For 10-50 employees doing ordinary ticket work against generous
 * budgets (`DEFAULT_BUDGETS`), that slack is harmless. It would not be adequate
 * for defending a public endpoint against a distributed attacker — which is
 * precisely why `RateLimitStore` exists as an interface: a Durable Object (one
 * global instance, strong consistency) or Cloudflare KV (shared, eventually
 * consistent) can replace `InMemoryRateLimitStore` without this file changing
 * at all beyond the one constructor call below.
 */

import { NextResponse, type NextRequest } from 'next/server';
import {
  InMemoryRateLimitStore,
  RateLimiter,
  rateLimitHeaders,
  unauthenticatedRequestKey,
  type RequestKind,
} from './src/security/rate-limit';

const READ_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

/**
 * Every mutation in this app — a ticket action, a server action's implicit
 * POST — arrives as a non-GET request to a page's own URL; there is no
 * separate `/api` prefix to distinguish (`src/service/tickets.ts`'s callers all
 * go through `app/tickets/actions.ts`). Method is therefore both the simplest
 * and the most robust signal: it does not depend on knowing Next's internal
 * server-action header names, which are not a contract this file should rely
 * on staying stable.
 */
function kindOf(method: string): RequestKind {
  return READ_METHODS.has(method) ? 'read' : 'mutate';
}

// Module scope: constructed once per warm isolate. See the file-level comment
// on the per-isolate limitation this implies.
const store = new InMemoryRateLimitStore();
const limiter = new RateLimiter(store);

export async function middleware(request: NextRequest): Promise<NextResponse> {
  const kind = kindOf(request.method);
  const key = unauthenticatedRequestKey(request.headers);

  let decision;
  try {
    decision = await limiter.check(kind, key, Date.now());
  } catch (err) {
    // A store failure (a future KV/DO backing being unreachable, say) must not
    // take the whole app down with it — that would turn a rate-limiter defect
    // into a bigger denial of service than any abuse this filter exists to
    // stop. Fail open on infrastructure errors, but do not fail silently:
    // console.error here reaches the Worker's own logs (`[observability]` in
    // wrangler.toml).
    console.error('rate-limit store failure; request allowed uninstrumented', err);
    return NextResponse.next();
  }

  const headers = rateLimitHeaders(decision);

  if (!decision.allowed) {
    // Mirrors `denyResponse()` in src/auth/access.ts: no body, no-store. A
    // Retry-After on a 429 is not sensitive information — it is the one thing
    // a well-behaved client needs to back off correctly.
    return new NextResponse(null, {
      status: 429,
      headers: { ...headers, 'cache-control': 'no-store' },
    });
  }

  const response = NextResponse.next();
  for (const [name, value] of Object.entries(headers)) {
    response.headers.set(name, value);
  }
  return response;
}

/**
 * Matcher — run on everything except Next's own static build output and
 * common static-file requests, which never reach a page, a route handler, or a
 * server action and gain nothing from being counted.
 *
 * Erring toward inclusion is the safe failure mode here: rate-limiting a
 * request that turns out to be static costs nothing but a Map lookup, while
 * skipping a request that turns out to be a page load or a mutation defeats
 * the point of this file. There is currently no `public/` directory in this
 * app, so the extension list below is precautionary for whatever gets added to
 * one later, not a response to anything that exists today.
 */
export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon\\.ico|.*\\.(?:png|jpg|jpeg|svg|gif|webp|ico|css|js|map|woff2?|ttf)$).*)',
  ],
};
