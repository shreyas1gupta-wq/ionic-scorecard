/**
 * Cloudflare Access identity — verification, fail-closed.
 *
 * Access sits in front of the app and sends a one-time PIN to allow-listed
 * company addresses, so we store no passwords and write no OTP code. What we DO
 * have to get right is trusting the assertion it forwards, and only that.
 *
 * THE THREAT THIS FILE EXISTS FOR: the `Cf-Access-Jwt-Assertion` header is just a
 * header. Anything that can reach the origin can set it. It is trustworthy only
 * because (a) the signature is checked against Cloudflare's published keys, and
 * (b) nothing can reach the origin except through Access. Both halves are
 * required. (b) is why `workers_dev = false` and the bypass test in
 * DESIGN.md §2.2 are not optional extras — without them this verification is
 * guarding a door that has a second, unlocked one beside it.
 *
 * Verification is delegated to `jose` rather than hand-rolled. Algorithm
 * confusion, a skipped audience check, and unverified `alg: none` are the classic
 * ways to write a JWT check that looks right and accepts forgeries.
 */

import { createRemoteJWKSet, jwtVerify, type JWTPayload, type JWTVerifyGetKey } from 'jose';

export interface AccessConfig {
  /** e.g. `ionic.cloudflareaccess.com` — no scheme, no trailing slash. */
  readonly teamDomain: string;
  /** The Access application's AUD tag. Application-specific, not team-wide. */
  readonly audience: string;
}

export interface AccessIdentity {
  /** The verified company email. Lower-cased; the join key to `employees`. */
  readonly email: string;
  /** Cloudflare's subject identifier. */
  readonly subject: string;
}

export class AccessDeniedError extends Error {
  override readonly name = 'AccessDeniedError';
  constructor(
    message: string,
    /** Safe to log. Never returned to the caller — see `denyResponse()`. */
    readonly detail?: string,
  ) {
    super(message);
  }
}

export const ACCESS_JWT_HEADER = 'cf-access-jwt-assertion';
export const ACCESS_JWT_COOKIE = 'CF_Authorization';

function issuerFor(teamDomain: string): string {
  const host = teamDomain.replace(/^https?:\/\//, '').replace(/\/+$/, '');
  if (host.length === 0) throw new Error('teamDomain is required');
  return `https://${host}`;
}

export function jwksUrlFor(teamDomain: string): URL {
  return new URL(`${issuerFor(teamDomain)}/cdn-cgi/access/certs`);
}

/**
 * Cache the key set per team domain.
 *
 * `createRemoteJWKSet` handles fetching, caching and rotation. Building a new one
 * per request would fetch Cloudflare's keys on every page load — slow, and a
 * self-inflicted rate limit.
 */
const jwksCache = new Map<string, JWTVerifyGetKey>();

function jwksFor(teamDomain: string): JWTVerifyGetKey {
  const url = jwksUrlFor(teamDomain).toString();
  let set = jwksCache.get(url);
  if (!set) {
    set = createRemoteJWKSet(new URL(url));
    jwksCache.set(url, set);
  }
  return set;
}

/** Injectable key resolver, so tests can verify against a local key pair. */
export interface VerifyOptions {
  readonly getKey?: JWTVerifyGetKey;
  /** Clock skew tolerance. Kept small deliberately. */
  readonly clockToleranceSeconds?: number;
}

/**
 * Verify an Access assertion and return the identity it carries.
 *
 * Throws `AccessDeniedError` for every failure mode — an absent token, a bad
 * signature, the wrong audience, the wrong issuer, expiry, or a payload with no
 * email. There is no path that returns a partial or unverified identity.
 */
export async function verifyAccessJwt(
  token: string | null | undefined,
  cfg: AccessConfig,
  opts: VerifyOptions = {},
): Promise<AccessIdentity> {
  if (!token || token.trim().length === 0) {
    throw new AccessDeniedError('no Access assertion present');
  }
  if (!cfg.audience || cfg.audience.trim().length === 0) {
    // A missing AUD would make `jwtVerify` skip the audience check, which would
    // accept a valid token minted for a DIFFERENT application in the same team.
    // Refusing to start is better than silently widening the door.
    throw new AccessDeniedError('Access audience is not configured');
  }

  const issuer = issuerFor(cfg.teamDomain);
  const getKey = opts.getKey ?? jwksFor(cfg.teamDomain);

  let payload: JWTPayload;
  try {
    const result = await jwtVerify(token, getKey, {
      issuer,
      audience: cfg.audience,
      // Cloudflare Access signs with RS256. Pinning it closes algorithm
      // confusion, including a token that claims `alg: none`.
      algorithms: ['RS256'],
      clockTolerance: opts.clockToleranceSeconds ?? 5,
    });
    payload = result.payload;
  } catch (err) {
    throw new AccessDeniedError('Access assertion failed verification', (err as Error).message);
  }

  const email = typeof payload.email === 'string' ? payload.email.trim().toLowerCase() : '';
  if (email.length === 0) {
    throw new AccessDeniedError('Access assertion carries no email claim');
  }
  const subject = typeof payload.sub === 'string' ? payload.sub : '';

  return { email, subject };
}

/** Read the assertion from a request: header first, then the Access cookie. */
export function extractAccessToken(headers: Headers): string | null {
  const fromHeader = headers.get(ACCESS_JWT_HEADER);
  if (fromHeader && fromHeader.trim().length > 0) return fromHeader.trim();

  const cookie = headers.get('cookie');
  if (!cookie) return null;
  for (const part of cookie.split(';')) {
    const [rawName, ...rest] = part.split('=');
    if (rawName?.trim() === ACCESS_JWT_COOKIE) {
      const value = rest.join('=').trim();
      return value.length > 0 ? value : null;
    }
  }
  return null;
}

/**
 * The response for any unauthenticated request: 403, no body.
 *
 * No detail, because the only audience for a reason here is someone probing. The
 * reason is logged server-side instead.
 */
export function denyResponse(): Response {
  return new Response(null, {
    status: 403,
    headers: { 'cache-control': 'no-store' },
  });
}
