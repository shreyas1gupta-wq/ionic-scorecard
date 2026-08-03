# Why there is no `middleware.ts` / `proxy.ts` in this app

Short version: **Next 16 and the Cloudflare adapter make it impossible, and removing it turned out to be the better architecture anyway.**

## The wall

There used to be a `middleware.ts` (later renamed `proxy.ts`) doing coarse IP-keyed
rate limiting. It cannot be deployed. Two requirements are mutually exclusive, and
both are stated by the tools themselves:

| Tool | What it says |
|---|---|
| `@opennextjs/cloudflare` | `Node.js middleware is not currently supported. Consider switching to Edge Middleware.` |
| Next.js 16 | `Route segment config is not allowed in Proxy file at "./proxy.ts". Proxy always runs on Node.js runtime.` |

So the adapter demands Edge; Next refuses to let Proxy be anything but Node. There
is no configuration that satisfies both. `export const runtime = 'edge'` is
rejected outright, and `runtime` inside the `config` object is rejected as an
unparseable property before that.

This was found empirically, by building. It is not a guess.

## What was lost, and why it does not matter much

The removed file provided **one** thing: a fixed-window request counter keyed by
`CF-Connecting-IP`, held in memory inside the Worker.

That counter was already the weakest layer in the design, for reasons documented at
the time:

- **Per-isolate, not global.** Cloudflare may run many isolates; each had its own
  counter, so the real ceiling was the budget multiplied by however many were warm.
- **Per-firm, not per-person.** A corporate network egresses through one NAT
  address, so it could never be a per-user control — which is why its budgets were
  deliberately widened to flood-guard levels (2,000 reads / 400 mutations a minute).

## What actually protects the app now

1. **Cloudflare Access sits in front of everything.** Unauthenticated traffic never
   reaches the Worker at all, so there is nothing for an in-app limiter to filter
   in the case that matters most.
2. **The per-employee limiter is untouched** — `src/security/employee-limit.ts`,
   wired into all 14 mutating server actions. This was always the meaningful
   control: it keys off a *verified* employee id, which middleware could never do
   because identity is not known that early. 60 mutations and 12 creations per
   person per minute.
3. **A Cloudflare WAF rate-limiting rule replaces the coarse layer** — and is
   strictly better than what it replaces: it runs at the network edge, before the
   request reaches the Worker, and it is genuinely global rather than per-isolate.

> ⚠ **Point 3 is a dashboard action nobody has performed yet.** It is not code and
> it is not in this repo. Until someone creates it, the app has no coarse flood
> guard — only Access in front and the per-employee budget behind. See
> `wrangler.toml` for the specific rules to create.

## `rate-limit.ts` is still used

The module stays: `employee-limit.ts` is built on its `checkRateLimit`,
`RateLimitStore` and `InMemoryRateLimitStore`. Only the middleware entry point is
gone. Its 26 tests still run and still pass.

`DEFAULT_BUDGETS` in that file no longer has a caller — it was the IP layer's
budget. It is kept because a WAF rule needs numbers to be set to, and these are the
reasoned ones (including the NAT correction).
