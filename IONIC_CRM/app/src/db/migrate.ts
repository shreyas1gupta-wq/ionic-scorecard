/**
 * Migration runner.
 *
 * Applies `db/migrations/*.sql` in filename order and records what it applied.
 * Deliberately tiny: an ORM's migration engine would be more machinery than a
 * ten-table schema justifies, and the SQL files are the thing we actually want
 * to be able to read and review.
 */

import { readdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';

/** The narrow slice of a Postgres client this runner needs. */
export interface SqlRunner {
  exec(sql: string): Promise<unknown>;
  query<T = Record<string, unknown>>(sql: string, params?: unknown[]): Promise<{ rows: T[] }>;
}

export interface AppliedMigration {
  readonly name: string;
  readonly skipped: boolean;
}

const MIGRATIONS_TABLE = `
  create table if not exists schema_migrations (
    name        text primary key,
    applied_at  timestamptz not null default now()
  );
`;

export async function migrationFiles(dir: string): Promise<string[]> {
  const entries = await readdir(dir);
  return entries.filter((f) => f.endsWith('.sql')).sort();
}

/**
 * Apply every pending migration in order.
 *
 * Each file runs inside its own transaction, so a failure leaves the database at
 * the last complete migration rather than half-way through one.
 */
export async function migrate(db: SqlRunner, migrationsDir: string): Promise<AppliedMigration[]> {
  await db.exec(MIGRATIONS_TABLE);

  const applied = await db.query<{ name: string }>('select name from schema_migrations');
  const done = new Set(applied.rows.map((r) => r.name));

  const results: AppliedMigration[] = [];
  for (const name of await migrationFiles(migrationsDir)) {
    if (done.has(name)) {
      results.push({ name, skipped: true });
      continue;
    }
    const sql = await readFile(join(migrationsDir, name), 'utf8');
    try {
      await db.exec('begin');
      await db.exec(sql);
      await db.query('insert into schema_migrations (name) values ($1)', [name]);
      await db.exec('commit');
    } catch (err) {
      await db.exec('rollback').catch(() => undefined);
      throw new Error(`migration ${name} failed: ${(err as Error).message}`, { cause: err });
    }
    results.push({ name, skipped: false });
  }
  return results;
}
