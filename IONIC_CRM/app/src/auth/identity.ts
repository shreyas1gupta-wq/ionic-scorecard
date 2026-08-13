/**
 * From an HTTP request to an authorised actor.
 *
 * The full chain, and every link fails closed:
 *
 *   headers → Access assertion → verified email → ACTIVE employee → Actor
 *
 * A verified email is NOT sufficient. Cloudflare Access proves someone controls a
 * mailbox; it does not prove they should be in this application. The allow-list
 * lives in the `employees` table, and a deactivated row stops working the moment
 * it is deactivated — no session to expire, no cache to bust.
 */

import {
  AccessDeniedError,
  extractAccessToken,
  verifyAccessJwt,
  type VerifyOptions,
} from './access';
import type { AppConfig } from './config';
import type { Actor, Employee, RepositoryFactory } from '../repo/types';

export interface AuthenticatedUser {
  readonly actor: Actor;
  readonly employee: Employee;
  /** True when identity came from the development shim rather than Access. */
  readonly viaDevShim: boolean;
}

export interface AuthenticateOptions extends VerifyOptions {
  /** Overrides the request entirely. Development only; see config.ts. */
  readonly config: AppConfig;
  readonly repositories: RepositoryFactory;
}

/**
 * Authenticate a request, or throw `AccessDeniedError`.
 *
 * Callers should map the error to `denyResponse()` — a bare 403 — and log the
 * `detail` server-side. Distinguishing "no such employee" from "bad signature" in
 * a response body only helps someone probing.
 */
export async function authenticate(
  headers: Headers,
  opts: AuthenticateOptions,
): Promise<AuthenticatedUser> {
  const { config, repositories } = opts;

  let email: string;
  let viaDevShim = false;

  if (config.devIdentityEmail !== null) {
    // Reachable only outside production, and only with the explicit second
    // opt-in. loadConfig() refuses to build a production config that gets here.
    email = config.devIdentityEmail;
    viaDevShim = true;
  } else {
    const token = extractAccessToken(headers);
    const identity = await verifyAccessJwt(token, config.access, opts);
    email = identity.email;
  }

  const employee = await repositories.resolveIdentity(email);
  if (employee === null) {
    // Covers both "never was a colleague" and "no longer active". Deliberately
    // one branch: the caller learns nothing about which.
    throw new AccessDeniedError('email is not an active employee', email);
  }

  return {
    actor: { employeeId: employee.id },
    employee,
    viaDevShim,
  };
}
