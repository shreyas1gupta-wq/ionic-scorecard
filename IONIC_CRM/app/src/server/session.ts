/**
 * Per-request identity for server components and route handlers.
 *
 * One entry point, `requireUser()`, and it throws rather than returning null.
 * A function that can return "no user" invites a caller to forget to check —
 * `const user = await getUser(); render(user.name)` typechecks happily against
 * an optional and then fails at runtime for whoever is not logged in. Throwing
 * makes the unauthenticated path impossible to fall through.
 */

import { headers } from 'next/headers';
import { AccessDeniedError } from '../auth/access';
import { loadConfig, type AppConfig } from '../auth/config';
import { authenticate, type AuthenticatedUser } from '../auth/identity';
import { getRepositories } from './db';
import type { Repository } from '../repo/types';

let configCache: AppConfig | undefined;

function config(): AppConfig {
  // loadConfig throws on a dangerous combination (see auth/config.ts), so a
  // misconfigured deployment fails on the first request rather than serving
  // anything. Cached because it cannot change within a process.
  configCache ??= loadConfig(process.env as Record<string, string | undefined>);
  return configCache;
}

export async function requireUser(): Promise<AuthenticatedUser> {
  const h = await headers();
  const repositories = await getRepositories();
  return authenticate(h, { config: config(), repositories });
}

/**
 * Run `fn` as the authenticated user, inside a transaction with RLS in force.
 *
 * The normal way to read or write anything. Note the shape: there is no way to
 * obtain a `Repository` without having first authenticated, because the only
 * thing handed to `fn` is one already bound to a verified actor.
 */
export async function withUser<T>(
  fn: (repo: Repository, user: AuthenticatedUser) => Promise<T>,
): Promise<T> {
  const user = await requireUser();
  const repositories = await getRepositories();
  return repositories.withActor(user.actor, (repo) => fn(repo, user));
}

export { AccessDeniedError };
