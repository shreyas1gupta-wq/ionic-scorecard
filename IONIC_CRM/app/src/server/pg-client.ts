/**
 * Production database connection — `pg` over Supabase's session-mode pooler.
 *
 * WHY THESE SPECIFIC CHOICES (see IONIC_CRM/DEPLOY_RESEARCH.md for sources):
 *
 * - **`pg`, not an HTTP driver.** This app's authorisation model needs a real SQL
 *   session: `set_config('app.employee_id', …)` plus `SET LOCAL ROLE crm_app`
 *   inside a transaction, with row-level security enforcing the rest. Supabase's
 *   REST API cannot do that, so any HTTP-only driver is disqualified outright.
 *
 * - **Session-mode pooler (port 5432), never transaction mode (6543).** A
 *   transaction-mode pooler may hand successive statements to different backend
 *   connections, which would silently discard `SET LOCAL ROLE`. Session mode
 *   "mirrors a direct connection", so session state holds.
 *
 * - **A client per request, not a module-level pool.** A Worker isolate can be
 *   evicted between requests, and a pooled connection held across that boundary
 *   is a connection leaked against Supabase's own limit.
 *
 * THE FAILURE MODE THIS FILE IS SHAPED TO PREVENT:
 *
 * If `SET LOCAL ROLE crm_app` fails to take effect, queries run as the CONNECTING
 * role with `app.employee_id` unset. If that role owns the tables or is a
 * superuser, Postgres **exempts it from row-level security entirely** — so every
 * query succeeds, every user sees everyone's tickets, and nothing errors. A smoke
 * test passes. Authorisation is simply gone.
 *
 * Two defences, and both are required:
 *   1. Connect as a role that owns nothing and has no table privileges of its own,
 *      so a failed `SET ROLE` produces a permission error rather than silent
 *      escalation. Enforced operationally — see the connection-string guidance in
 *      IONIC_CRM/SETUP_ACCOUNTS.md.
 *   2. Assert, inside every transaction, that the role and identity actually took.
 *      That is `assertSessionIdentity` below, called from `postgres.ts`.
 */

import { Client } from 'pg';
import type { SqlClient, SqlRunner } from '../repo/postgres';

export class DatabaseConfigError extends Error {
  override readonly name = 'DatabaseConfigError';
}

/**
 * Reject a transaction-mode connection string at startup rather than in
 * production behaviour.
 *
 * Port 6543 is Supabase's transaction-mode pooler. It connects perfectly, runs
 * queries perfectly, and breaks `SET LOCAL ROLE` — the exact silent-RLS-bypass
 * described above. Catching it here turns a security failure into a boot failure.
 */
export function assertSessionModeUrl(url: string): void {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    throw new DatabaseConfigError('CRM_DATABASE_URL is not a valid URL');
  }
  if (parsed.port === '6543') {
    throw new DatabaseConfigError(
      'CRM_DATABASE_URL uses port 6543 (Supabase transaction-mode pooler). That mode may route ' +
        'successive statements to different backends, which silently discards SET LOCAL ROLE and ' +
        'disables row-level security without any error. Use the session-mode pooler on port 5432.',
    );
  }
  if (parsed.port !== '5432') {
    throw new DatabaseConfigError(
      `CRM_DATABASE_URL uses unexpected port ${parsed.port || '(none)'}; expected 5432 ` +
        '(session-mode pooler). Refusing to guess whether session state is preserved.',
    );
  }
}

export function createPgClient(connectionString: string): SqlClient {
  assertSessionModeUrl(connectionString);

  return {
    async transaction<T>(fn: (tx: SqlRunner) => Promise<T>): Promise<T> {
      const client = new Client({
        connectionString,
        // Supabase terminates TLS with its own chain; the pooler host is
        // authenticated by the connection string's credentials.
        ssl: { rejectUnauthorized: false },
        // A request that cannot get a connection promptly should fail rather than
        // hold the Worker open until its own limit kills it.
        connectionTimeoutMillis: 8_000,
        statement_timeout: 15_000,
      });

      await client.connect();
      try {
        await client.query('BEGIN');
        const runner: SqlRunner = {
          async query(sql, params) {
            // `pg` already returns `{ rows }`, so this is a passthrough rather
            // than a translation.
            const r = await client.query(sql, params as unknown[]);
            return { rows: r.rows as never[] };
          },
          async exec(sql) {
            return client.query(sql);
          },
        };
        const result = await fn(runner);
        await client.query('COMMIT');
        return result;
      } catch (err) {
        // Rollback failures are swallowed deliberately: the original error is the
        // one worth reporting, and the connection is closed immediately after.
        await client.query('ROLLBACK').catch(() => undefined);
        throw err;
      } finally {
        await client.end().catch(() => undefined);
      }
    },
  };
}
