/**
 * Postgres repository.
 *
 * Every operation runs inside a transaction that has already set the identity
 * GUC and dropped to the non-privileged `crm_app` role, so row-level security is
 * in force for all of it. There is no code path that reaches the database
 * without that, because the only way to obtain a repository is `withActor`.
 *
 * This adapter deliberately does NOT re-check authorisation in JavaScript. The
 * database is the authority — duplicating the rules here would create two places
 * to get them wrong, and the one that matters is the one an attacker cannot skip.
 * What this file does instead is translate Postgres' refusals into the domain
 * errors the in-memory implementation also raises, so both satisfy one contract.
 */

import { formatTicketRef } from '../domain/ticket-ref';
import { computeRowHash, verifyChain } from '../domain/hash-chain';
import type { IsoDate } from '../domain/calendar';
import type { Priority, TicketStatus, Role } from '../domain/tickets';
import {
  AuthorizationError,
  ValidationError,
  type AccessEventKind,
  type AccessEventRecord,
  type AccessLog,
  type Actor,
  type AuditRecord,
  type AuditStore,
  type CalendarStore,
  type Category,
  type DeadlineChange,
  type Employee,
  type EmployeeStore,
  type NewEmployee,
  type NewPunch,
  type NewTicket,
  type Punch,
  type ReferenceStore,
  type Repository,
  type RepositoryFactory,
  type Ticket,
  type TicketFilter,
  type TicketStore,
  type Uuid,
} from './types';

/**
 * An UPDATE that matched no row.
 *
 * Under RLS this means one of: the row does not exist, it is not visible to this
 * actor, or the policy forbids the write. All three are refusals and none of them
 * should tell the caller which — distinguishing them turns an update endpoint
 * into an existence oracle.
 */
function requireRow<R, T>(row: R | undefined, id: string, map: (r: R) => T): T {
  if (!row) throw new AuthorizationError(`not visible or not permitted: ${id}`);
  return map(row);
}

export interface SqlRunner {
  query<T = Record<string, unknown>>(sql: string, params?: unknown[]): Promise<{ rows: T[] }>;
  exec(sql: string): Promise<unknown>;
}

/** The runtime role every request must be running as. Owns nothing; see 0001. */
export const RUNTIME_ROLE = 'crm_app';

export class SessionIdentityError extends Error {
  override readonly name = 'SessionIdentityError';
}

/**
 * Prove the role switch and the identity actually took effect.
 *
 * THE FAILURE THIS EXISTS TO CATCH is the worst one available in this system, and
 * it is silent. If `SET LOCAL ROLE crm_app` does not stick — a connection pooler
 * in transaction mode splitting statements across backends, a driver path that
 * never emitted a real `BEGIN`, a future refactor reordering these lines — then
 * queries execute as the CONNECTING role with `app.employee_id` unset.
 *
 * And if that role happens to own the tables or be a superuser, Postgres exempts
 * it from row-level security altogether. Nothing errors. Every query succeeds.
 * Every employee sees every other employee's tickets. A smoke test passes
 * cleanly, and the only symptom is that authorisation no longer exists.
 *
 * One extra round trip per request buys certainty about that. For a fifty-person
 * internal tool that is not a close call.
 */
export async function assertSessionIdentity(tx: SqlRunner, actor: Actor): Promise<void> {
  const r = await tx.query<{ who: string; emp: string | null }>(
    `select current_user as who, current_setting('app.employee_id', true) as emp`,
  );
  const row = r.rows[0];
  if (row === undefined) {
    throw new SessionIdentityError('could not read the session identity back');
  }
  if (row.who !== RUNTIME_ROLE) {
    throw new SessionIdentityError(
      `refusing to run: session role is "${row.who}", expected "${RUNTIME_ROLE}". ` +
        'Row-level security may not be in force — a connection pooler in transaction mode is the ' +
        'usual cause. Check that CRM_DATABASE_URL points at the SESSION-mode pooler (port 5432).',
    );
  }
  if (row.emp !== actor.employeeId) {
    throw new SessionIdentityError(
      'refusing to run: the session identity does not match the requesting actor. ' +
        'Every row-level-security policy keys off this value, so proceeding could expose ' +
        "another employee's data.",
    );
  }
}

export interface SqlClient {
  transaction<T>(fn: (tx: SqlRunner) => Promise<T>): Promise<T>;
  close?(): Promise<void>;
}

// -----------------------------------------------------------------------------
// Error translation
//
// The mapping matters for a specific reason: an RLS refusal on INSERT and a
// missing grant arrive as different SQLSTATEs but mean the same thing to a
// caller — you may not do that. Collapsing them into AuthorizationError is what
// lets one contract test cover both implementations.
// -----------------------------------------------------------------------------
const AUTH_CODES = new Set([
  '42501', // insufficient_privilege — a revoked grant, or our append-only triggers
]);

const VALIDATION_CODES = new Set([
  '23514', // check_violation
  '23503', // foreign_key_violation
  '23505', // unique_violation
  '23502', // not_null_violation
]);

function mapError(err: unknown): never {
  const e = err as { code?: string; message?: string };
  const msg = e.message ?? String(err);

  if (e.code && AUTH_CODES.has(e.code)) throw new AuthorizationError(msg);
  if (/row-level security/i.test(msg)) throw new AuthorizationError(msg);
  if (/append-only/i.test(msg)) throw new AuthorizationError(msg);
  if (e.code && VALIDATION_CODES.has(e.code)) throw new ValidationError(msg);
  if (/is immutable/i.test(msg)) throw new ValidationError(msg);

  throw err;
}

async function guarded<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (err) {
    return mapError(err);
  }
}

// -----------------------------------------------------------------------------
// Row mapping
// -----------------------------------------------------------------------------

/**
 * A Postgres `date` has no timezone. Drivers hand it back either as a string or
 * as a Date pinned to UTC midnight, so read UTC fields — using local getters
 * would shift the date by a day for anyone west of Greenwich.
 */
function toIsoDate(v: unknown): IsoDate {
  if (v instanceof Date) {
    const y = String(v.getUTCFullYear()).padStart(4, '0');
    const m = String(v.getUTCMonth() + 1).padStart(2, '0');
    const d = String(v.getUTCDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }
  if (typeof v === 'string') return v.slice(0, 10);
  throw new Error(`cannot read a date from ${typeof v}`);
}

function toIsoDateOrNull(v: unknown): IsoDate | null {
  return v === null || v === undefined ? null : toIsoDate(v);
}

function toInstant(v: unknown): string {
  if (v instanceof Date) return v.toISOString();
  if (typeof v === 'string') return new Date(v).toISOString();
  throw new Error(`cannot read a timestamp from ${typeof v}`);
}

interface EmployeeRow {
  id: string;
  work_email: string;
  display_name: string;
  role: string;
  manager_id: string | null;
  status: string;
}

const EMPLOYEE_COLUMNS = 'id, work_email, display_name, role, manager_id, status';

const mapEmployee = (r: EmployeeRow): Employee => ({
  id: r.id,
  workEmail: r.work_email,
  displayName: r.display_name,
  role: r.role as Role,
  managerId: r.manager_id,
  status: r.status as 'ACTIVE' | 'DEACTIVATED',
});

interface TicketRow {
  id: string;
  ref: string;
  title: string;
  description: string;
  category_id: string | null;
  priority: string;
  assignee_id: string;
  raiser_id: string;
  status: string;
  deadline: unknown;
  original_deadline: unknown;
  created_at: unknown;
  closed_date: unknown;
  cancel_reason: string | null;
}

const mapTicket = (r: TicketRow): Ticket => ({
  id: r.id,
  ref: r.ref,
  title: r.title,
  description: r.description,
  categoryId: r.category_id,
  priority: r.priority as Priority,
  assigneeId: r.assignee_id,
  raiserId: r.raiser_id,
  status: r.status as TicketStatus,
  deadline: toIsoDate(r.deadline),
  originalDeadline: toIsoDate(r.original_deadline),
  createdAt: toInstant(r.created_at),
  closedDate: toIsoDateOrNull(r.closed_date),
  cancelReason: r.cancel_reason,
});

interface PunchRow {
  id: string;
  seq: string | number;
  ticket_id: string;
  actor_id: string;
  created_at: unknown;
  punch_date: unknown;
  status: string;
  note: string;
  blocked_reason: string | null;
  minutes_spent: number | null;
  next_action: string | null;
  next_action_by: unknown;
  corrects_update_id: string | null;
}

const mapPunch = (r: PunchRow): Punch => ({
  id: r.id,
  seq: Number(r.seq),
  ticketId: r.ticket_id,
  actorId: r.actor_id,
  createdAt: toInstant(r.created_at),
  punchDate: toIsoDate(r.punch_date),
  status: r.status as TicketStatus,
  note: r.note,
  blockedReason: r.blocked_reason,
  minutesSpent: r.minutes_spent,
  nextAction: r.next_action,
  nextActionBy: toIsoDateOrNull(r.next_action_by),
  correctsUpdateId: r.corrects_update_id,
});

const TICKET_COLUMNS = `
  id, ref, title, description, category_id, priority, assignee_id, raiser_id,
  status, deadline, original_deadline, created_at, closed_date, cancel_reason
`;

const PUNCH_COLUMNS = `
  id, seq, ticket_id, actor_id, created_at, punch_date, status, note,
  blocked_reason, minutes_spent, next_action, next_action_by, corrects_update_id
`;

interface SummaryExtras {
  last_punch_date: unknown;
  last_punch_by: string | null;
  punch_count: string | number;
}

/**
 * Build the WHERE clause for a ticket filter.
 *
 * Shared by `list` and `listSummaries` so the two can never disagree about what
 * "open only" means. `prefix` lets the same predicates work against an aliased
 * table in the join query.
 */
function ticketFilterSql(
  filter: TicketFilter | undefined,
  prefix = '',
): { clause: string; params: unknown[] } {
  const where: string[] = [];
  const params: unknown[] = [];
  if (filter?.assigneeId) {
    params.push(filter.assigneeId);
    where.push(`${prefix}assignee_id = $${params.length}`);
  }
  if (filter?.status && filter.status.length > 0) {
    params.push(filter.status);
    where.push(`${prefix}status = any($${params.length}::text[])`);
  }
  if (filter?.openOnly) {
    where.push(`${prefix}status not in ('DONE', 'CANCELLED')`);
  }
  return { clause: where.length > 0 ? `where ${where.join(' and ')}` : '', params };
}

interface DeadlineChangeRow {
  id: string;
  ticket_id: string;
  from_date: unknown;
  to_date: unknown;
  reason: string;
  requested_by: string;
  requested_at: unknown;
  decision: string;
  approved_by: string | null;
  decided_at: unknown;
}

const DEADLINE_CHANGE_COLUMNS = `
  id, ticket_id, from_date, to_date, reason, requested_by, requested_at,
  decision, approved_by, decided_at
`;

const mapDeadlineChange = (r: DeadlineChangeRow): DeadlineChange => ({
  id: r.id,
  ticketId: r.ticket_id,
  fromDate: toIsoDate(r.from_date),
  toDate: toIsoDate(r.to_date),
  reason: r.reason,
  requestedBy: r.requested_by,
  requestedAt: toInstant(r.requested_at),
  decision: r.decision as DeadlineChange['decision'],
  approvedBy: r.approved_by,
  decidedAt: r.decided_at === null || r.decided_at === undefined ? null : toInstant(r.decided_at),
});

interface AuditRow2 {
  seq: string | number;
  /** Already canonical — see AUDIT_COLUMNS. */
  occurred_at: string;
  actor_id: string | null;
  action: string;
  entity: string;
  entity_id: string | null;
  payload: Record<string, unknown>;
  prev_hash: Uint8Array;
  row_hash: Uint8Array;
}

/**
 * `occurred_at` is rendered as an exact canonical string, not returned as a
 * timestamp. It is inside the hash, and a driver that hands back a JS `Date`
 * silently truncates Postgres' microseconds to milliseconds — which would make
 * every verification fail with no visible cause.
 */
const AUDIT_COLUMNS = `
  seq,
  to_char(occurred_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') as occurred_at,
  actor_id, action, entity, entity_id, payload, prev_hash, row_hash
`;

interface CategoryRow {
  id: string;
  name: string;
  active: boolean;
}

const mapCategory = (r: CategoryRow): Category => ({
  id: r.id,
  name: r.name,
  active: r.active,
});

interface AccessEventRow {
  seq: string | number;
  occurred_at: unknown;
  employee_id: string | null;
  event: string;
  entity: string | null;
  entity_id: string | null;
}

const mapAccessEvent = (r: AccessEventRow): AccessEventRecord => ({
  seq: Number(r.seq),
  occurredAt: toInstant(r.occurred_at),
  employeeId: r.employee_id,
  event: r.event as AccessEventKind,
  entity: r.entity,
  entityId: r.entity_id,
});

const mapAudit = (r: AuditRow2): AuditRecord => ({
  seq: Number(r.seq),
  occurredAt: r.occurred_at,
  actorId: r.actor_id,
  action: r.action,
  entity: r.entity,
  entityId: r.entity_id,
  payload: r.payload,
  prevHashHex: Buffer.from(r.prev_hash).toString('hex'),
  rowHashHex: Buffer.from(r.row_hash).toString('hex'),
});

// -----------------------------------------------------------------------------
// Factory
// -----------------------------------------------------------------------------

export function createPostgresRepository(client: SqlClient): RepositoryFactory {
  return {
    async withActor(actor: Actor, fn) {
      return client.transaction(async (tx) => {
        // Identity first, then drop privilege. `true` scopes both to this
        // transaction, so nothing can leak into the next request on a pooled
        // connection — which would be a cross-user data leak, not a bug.
        await tx.query('select set_config($1, $2, true)', ['app.employee_id', actor.employeeId]);
        await tx.exec('set local role crm_app');
        await assertSessionIdentity(tx, actor);
        return fn(buildRepository(tx, actor));
      });
    },
    async resolveIdentity(email: string) {
      return client.transaction(async (tx) => {
        // No identity GUC is set here — by definition there is no identity yet.
        // Safe because app.resolve_identity() is SECURITY DEFINER and does not
        // consult the GUC, and because it can only ever return one row.
        await tx.exec('set local role crm_app');
        return guarded(async () => {
          const r = await tx.query<EmployeeRow>(
            `select id, work_email, display_name, role, manager_id, status
             from app.resolve_identity($1)`,
            [email],
          );
          const row = r.rows[0];
          return row ? mapEmployee(row) : null;
        });
      });
    },

    async close() {
      await client.close?.();
    },
  };
}

function buildRepository(tx: SqlRunner, actor: Actor): Repository {
  const employees: EmployeeStore = {
    findByEmail: (email) =>
      guarded(async () => {
        const r = await tx.query<EmployeeRow>(
          `select ${EMPLOYEE_COLUMNS} from employees where work_email = $1`,
          [email.trim().toLowerCase()],
        );
        const row = r.rows[0];
        return row ? mapEmployee(row) : null;
      }),

    findById: (id) =>
      guarded(async () => {
        const r = await tx.query<EmployeeRow>(
          `select ${EMPLOYEE_COLUMNS} from employees where id = $1`,
          [id],
        );
        const row = r.rows[0];
        return row ? mapEmployee(row) : null;
      }),

    listActive: () =>
      guarded(async () => {
        const r = await tx.query<EmployeeRow>(
          `select ${EMPLOYEE_COLUMNS}
           from employees where status = 'ACTIVE' order by display_name`,
        );
        return r.rows.map(mapEmployee);
      }),

    listAll: () =>
      guarded(async () => {
        const r = await tx.query<EmployeeRow>(
          `select ${EMPLOYEE_COLUMNS} from employees order by display_name`,
        );
        return r.rows.map(mapEmployee);
      }),

    create: (input: NewEmployee) =>
      guarded(async () => {
        // Lowercased here rather than in SQL because the column has a CHECK that
        // it equals its own lower(), so the unique index is case-insensitive only
        // if the value going in is already folded. This is the line that makes
        // "Alice@Ionic.in" collide with "alice@ionic.in".
        const r = await tx.query<EmployeeRow>(
          `insert into employees (work_email, display_name, role, manager_id)
           values ($1, $2, $3, $4)
           returning ${EMPLOYEE_COLUMNS}`,
          [
            input.workEmail.trim().toLowerCase(),
            input.displayName.trim(),
            input.role,
            input.managerId,
          ],
        );
        return mapEmployee(r.rows[0]!);
      }),

    setRole: (id, role) =>
      guarded(async () => {
        // No self-check here. employees_guard_self_role (0005) refuses it with
        // errcode 42501, which mapError turns into AuthorizationError — the same
        // error the in-memory store raises. Re-checking in JS would create a
        // second place for the rule to be wrong, and only the database's copy is
        // one an attacker cannot route around.
        const r = await tx.query<EmployeeRow>(
          `update employees set role = $2 where id = $1 returning ${EMPLOYEE_COLUMNS}`,
          [id, role],
        );
        return requireRow(r.rows[0], id, mapEmployee);
      }),

    setManager: (id, managerId) =>
      guarded(async () => {
        const r = await tx.query<EmployeeRow>(
          `update employees set manager_id = $2 where id = $1 returning ${EMPLOYEE_COLUMNS}`,
          [id, managerId],
        );
        return requireRow(r.rows[0], id, mapEmployee);
      }),

    deactivate: (id, reason) =>
      guarded(async () => {
        // `deactivated_at` and the reason are set in the same statement because
        // employees_deactivation_complete (0001) is a table-level CHECK: any
        // intermediate state with a status and no reason is rejected outright,
        // which is what makes an unexplained offboarding impossible rather than
        // merely discouraged.
        const r = await tx.query<EmployeeRow>(
          `update employees
              set status = 'DEACTIVATED',
                  deactivated_at = now(),
                  deactivated_reason = $2
            where id = $1
          returning ${EMPLOYEE_COLUMNS}`,
          [id, reason.trim().length > 0 ? reason.trim() : null],
        );
        return requireRow(r.rows[0], id, mapEmployee);
      }),
  };

  const tickets: TicketStore = {
    create: (input: NewTicket) =>
      guarded(async () => {
        const year = Number(input.deadline.slice(0, 4));
        // Allocated inside this transaction, so a rollback does not burn a
        // reference — and the definer function keeps ticket_counters unreadable.
        const seq = await tx.query<{ s: number }>('select app.next_ticket_seq($1) as s', [year]);
        const ref = formatTicketRef(year, Number(seq.rows[0]!.s));

        const r = await tx.query<TicketRow>(
          `insert into tickets
             (ref, title, description, category_id, priority, assignee_id, raiser_id,
              deadline, original_deadline)
           values ($1, $2, $3, $4, $5, $6, $7, $8, $8)
           returning ${TICKET_COLUMNS}`,
          [
            ref,
            input.title,
            input.description ?? '',
            input.categoryId ?? null,
            input.priority,
            input.assigneeId,
            input.raiserId,
            input.deadline,
          ],
        );
        return mapTicket(r.rows[0]!);
      }),

    findById: (id) =>
      guarded(async () => {
        const r = await tx.query<TicketRow>(
          `select ${TICKET_COLUMNS} from tickets where id = $1`,
          [id],
        );
        const row = r.rows[0];
        return row ? mapTicket(row) : null;
      }),

    findByRef: (ref) =>
      guarded(async () => {
        const r = await tx.query<TicketRow>(
          `select ${TICKET_COLUMNS} from tickets where ref = $1`,
          [ref],
        );
        const row = r.rows[0];
        return row ? mapTicket(row) : null;
      }),

    list: (filter?: TicketFilter) =>
      guarded(async () => {
        const { clause, params } = ticketFilterSql(filter);
        const r = await tx.query<TicketRow>(
          `select ${TICKET_COLUMNS} from tickets ${clause} order by deadline, ref`,
          params,
        );
        return r.rows.map(mapTicket);
      }),

    listSummaries: (filter?: TicketFilter) =>
      guarded(async () => {
        const { clause, params } = ticketFilterSql(filter, 't.');
        // One grouped subquery rather than a query per ticket. RLS applies to
        // status_updates as well, so a ticket you can see but whose punches you
        // cannot would aggregate to nulls rather than leaking anything.
        const r = await tx.query<TicketRow & SummaryExtras>(
          `select ${TICKET_COLUMNS.trim()
            .split(/,\s*/)
            .map((c) => `t.${c}`)
            .join(', ')},
                  s.last_punch_date, s.last_punch_by, coalesce(s.punch_count, 0) as punch_count
             from tickets t
             left join (
               select ticket_id,
                      max(punch_date)                          as last_punch_date,
                      (array_agg(actor_id order by seq desc))[1] as last_punch_by,
                      count(*)::int                            as punch_count
                 from status_updates
                group by ticket_id
             ) s on s.ticket_id = t.id
             ${clause}
            order by t.deadline, t.ref`,
          params,
        );
        return r.rows.map((row) => ({
          ticket: mapTicket(row),
          lastPunchDate: toIsoDateOrNull(row.last_punch_date),
          lastPunchBy: row.last_punch_by,
          punchCount: Number(row.punch_count),
        }));
      }),

    addPunch: (input: NewPunch) =>
      guarded(async () => {
        const r = await tx.query<PunchRow>(
          `insert into status_updates
             (ticket_id, actor_id, punch_date, status, note, blocked_reason,
              minutes_spent, next_action, next_action_by, corrects_update_id)
           values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
           returning ${PUNCH_COLUMNS}`,
          [
            input.ticketId,
            input.actorId,
            input.punchDate,
            input.status,
            input.note ?? '',
            input.blockedReason ?? null,
            input.minutesSpent ?? null,
            input.nextAction ?? null,
            input.nextActionBy ?? null,
            input.correctsUpdateId ?? null,
          ],
        );
        return mapPunch(r.rows[0]!);
      }),

    listPunches: (ticketId) =>
      guarded(async () => {
        const r = await tx.query<PunchRow>(
          `select ${PUNCH_COLUMNS} from status_updates where ticket_id = $1 order by seq`,
          [ticketId],
        );
        return r.rows.map(mapPunch);
      }),

    setStatus: (change) =>
      guarded(async () => {
        const r = await tx.query<TicketRow>(
          `update tickets
              set status        = $2,
                  closed_at     = case when $2 in ('DONE','CANCELLED') then now() else null end,
                  closed_date   = $3,
                  cancel_reason = case when $2 = 'CANCELLED' then $4 else cancel_reason end
            where id = $1
          returning ${TICKET_COLUMNS}`,
          [change.ticketId, change.status, change.closedDate ?? null, change.cancelReason ?? null],
        );
        return requireRow(r.rows[0], change.ticketId, mapTicket);
      }),

    setAssignee: (ticketId, assigneeId) =>
      guarded(async () => {
        const r = await tx.query<TicketRow>(
          `update tickets set assignee_id = $2 where id = $1 returning ${TICKET_COLUMNS}`,
          [ticketId, assigneeId],
        );
        return requireRow(r.rows[0], ticketId, mapTicket);
      }),

    setDeadline: (ticketId, deadline) =>
      guarded(async () => {
        const r = await tx.query<TicketRow>(
          `update tickets set deadline = $2 where id = $1 returning ${TICKET_COLUMNS}`,
          [ticketId, deadline],
        );
        return requireRow(r.rows[0], ticketId, mapTicket);
      }),

    requestDeadlineChange: (input) =>
      guarded(async () => {
        const r = await tx.query<DeadlineChangeRow>(
          `insert into deadline_changes (ticket_id, from_date, to_date, reason, requested_by)
           select t.id, t.deadline, $2, $3, app.current_employee()
             from tickets t where t.id = $1
           returning ${DEADLINE_CHANGE_COLUMNS}`,
          [input.ticketId, input.toDate, input.reason],
        );
        return requireRow(r.rows[0], input.ticketId, mapDeadlineChange);
      }),

    listDeadlineChanges: (ticketId) =>
      guarded(async () => {
        const r = await tx.query<DeadlineChangeRow>(
          `select ${DEADLINE_CHANGE_COLUMNS} from deadline_changes
            where ticket_id = $1 order by requested_at`,
          [ticketId],
        );
        return r.rows.map(mapDeadlineChange);
      }),

    decideDeadlineChange: (id, decision) =>
      guarded(async () => {
        const r = await tx.query<DeadlineChangeRow>(
          `update deadline_changes
              set decision = $2, approved_by = app.current_employee(), decided_at = now()
            where id = $1 and decision = 'PENDING'
          returning ${DEADLINE_CHANGE_COLUMNS}`,
          [id, decision],
        );
        // No row means either invisible, already decided, or not yours to decide.
        // All three are refusals, and none should say which.
        return requireRow(r.rows[0], id, mapDeadlineChange);
      }),
  };

  const audit: AuditStore = {
    append: (entry) =>
      guarded(async () => {
        // One round trip for all three, so the timestamp is the database's, the
        // head is read under the same transaction, and the seq matches what
        // append_audit will check. The timestamp comes back as an exact canonical
        // STRING rather than a Date: a Date carries milliseconds, Postgres stores
        // microseconds, and occurred_at is inside the hash — so a round trip
        // through Date would make every later verification fail.
        const pre = await tx.query<{ t: string; h: Uint8Array; s: string }>(
          `select to_char(now() at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') as t,
                  app.audit_chain_head() as h,
                  app.audit_next_seq()   as s`,
        );
        const row = pre.rows[0]!;
        const occurredAt = row.t;
        const prevHash = Buffer.from(row.h);
        const seq = Number(row.s);
        const actorId = actor.employeeId;

        const rowHash = computeRowHash(prevHash, {
          seq,
          occurredAt,
          actorId,
          action: entry.action,
          entity: entry.entity,
          entityId: entry.entityId,
          payload: entry.payload as never,
        });

        await tx.query(
          `select app.append_audit($1::bigint, $2::timestamptz, $3::uuid, $4, $5, $6,
                                   $7::jsonb, $8::bytea, $9::bytea)`,
          [
            seq,
            occurredAt,
            actorId,
            entry.action,
            entry.entity,
            entry.entityId,
            JSON.stringify(entry.payload),
            prevHash,
            rowHash,
          ],
        );

        return {
          ...entry,
          seq,
          occurredAt,
          actorId,
          prevHashHex: prevHash.toString('hex'),
          rowHashHex: rowHash.toString('hex'),
        };
      }),

    list: (limit = 200) =>
      guarded(async () => {
        const r = await tx.query<AuditRow2>(
          `select ${AUDIT_COLUMNS} from audit_log order by seq desc limit $1`,
          [limit],
        );
        return r.rows.map(mapAudit);
      }),

    verify: () =>
      guarded(async () => {
        const r = await tx.query<AuditRow2>(`select ${AUDIT_COLUMNS} from audit_log order by seq`);
        const chain = r.rows.map((x) => ({
          seq: Number(x.seq),
          occurredAt: x.occurred_at,
          actorId: x.actor_id,
          action: x.action,
          entity: x.entity,
          entityId: x.entity_id,
          payload: x.payload as never,
          prevHash: Buffer.from(x.prev_hash),
          rowHash: Buffer.from(x.row_hash),
        }));
        const result = verifyChain(chain);
        return {
          ok: result.ok,
          checked: result.checked,
          headHashHex: result.headHash,
          failures: result.failures.map((f) => JSON.stringify(f)),
        };
      }),
  };

  const reference: ReferenceStore = {
    categories: () =>
      guarded(async () => {
        const r = await tx.query<CategoryRow>(
          `select id, name, active from categories where active order by name`,
        );
        return r.rows.map(mapCategory);
      }),

    allCategories: () =>
      guarded(async () => {
        const r = await tx.query<CategoryRow>(`select id, name, active from categories order by name`);
        return r.rows.map(mapCategory);
      }),

    createCategory: (name) =>
      guarded(async () => {
        const r = await tx.query<CategoryRow>(
          `insert into categories (name) values ($1) returning id, name, active`,
          [name.trim()],
        );
        return mapCategory(r.rows[0]!);
      }),

    setCategoryActive: (id, active) =>
      guarded(async () => {
        const r = await tx.query<CategoryRow>(
          `update categories set active = $2 where id = $1 returning id, name, active`,
          [id, active],
        );
        return requireRow(r.rows[0], id, mapCategory);
      }),
  };

  const accessLog: AccessLog = {
    record: (e) =>
      guarded(async () => {
        await tx.query(
          `insert into access_events (employee_id, event, entity, entity_id, ip, user_agent)
           values ($1, $2, $3, $4, $5::inet, $6)`,
          [
            actor.employeeId,
            e.event,
            e.entity ?? null,
            e.entityId ?? null,
            e.ip ?? null,
            e.userAgent ?? null,
          ],
        );
      }),

    recentFor: (employeeId, limit = 20) =>
      guarded(async () => {
        // No role check: access_events_admin_select returns nothing to a
        // non-admin, so an empty list here IS the refusal.
        const r = await tx.query<AccessEventRow>(
          `select seq, occurred_at, employee_id, event, entity, entity_id
             from access_events
            where employee_id = $1
            order by seq desc
            limit $2`,
          [employeeId, limit],
        );
        return r.rows.map(mapAccessEvent);
      }),

    lastLoginAt: (employeeId) =>
      guarded(async () => {
        const r = await tx.query<{ occurred_at: unknown }>(
          `select max(occurred_at) as occurred_at
             from access_events
            where employee_id = $1 and event = 'LOGIN'`,
          [employeeId],
        );
        const v = r.rows[0]?.occurred_at;
        // max() over zero visible rows is NULL, which is also the honest answer
        // for a non-admin caller: they are told nothing either way.
        return v === null || v === undefined ? null : toInstant(v);
      }),
  };

  const calendar: CalendarStore = {
    holidays: () =>
      guarded(async () => {
        const r = await tx.query<{ holiday_date: unknown }>('select holiday_date from holidays');
        return new Set(r.rows.map((x) => toIsoDate(x.holiday_date)));
      }),

    listHolidays: () =>
      guarded(async () => {
        const r = await tx.query<{ holiday_date: unknown; name: string }>(
          'select holiday_date, name from holidays order by holiday_date',
        );
        return r.rows.map((x) => ({ date: toIsoDate(x.holiday_date), name: x.name }));
      }),

    addHoliday: (date, name) =>
      guarded(async () => {
        const r = await tx.query<{ holiday_date: unknown; name: string }>(
          `insert into holidays (holiday_date, name) values ($1, $2)
           returning holiday_date, name`,
          [date, name.trim()],
        );
        const row = r.rows[0]!;
        return { date: toIsoDate(row.holiday_date), name: row.name };
      }),

    removeHoliday: (date) =>
      guarded(async () => {
        // `returning` is what makes a no-match distinguishable from a delete, and
        // requireRow then makes it indistinguishable to the CALLER — a holiday
        // that is not there and a delete you are not allowed to do give one error.
        const r = await tx.query<{ holiday_date: unknown }>(
          'delete from holidays where holiday_date = $1 returning holiday_date',
          [date],
        );
        requireRow(r.rows[0], date, () => undefined);
      }),
  };

  return { actor, employees, tickets, calendar, reference, audit, accessLog };
}
