/**
 * Administration — user lifecycle, reference data, and the two compliance reports.
 *
 * Three things every operation in this file does, and the reasons they are here
 * rather than anywhere else:
 *
 *  1. IT READS THE ACTOR'S ROLE FROM THE STORE. Never from a parameter, never
 *     from a session object handed in by a caller. `Actor` carries an id and no
 *     role precisely so that "I am an admin" is not something the application
 *     layer can assert. If it could, one day it would.
 *
 *  2. IT APPENDS TO THE HASH CHAIN. An admin action with no audit row is the one
 *     kind of change this system must never permit — REQUIREMENTS §2 ("role
 *     changes are themselves audited") and §9. The append is inside the caller's
 *     transaction, so an action cannot commit without its audit row.
 *
 *  3. IT LEAVES THE INVARIANTS WHERE THEY ARE ENFORCED. No self-role-change, no
 *     hard delete, no deactivation over open work, no management cycle: those
 *     live in 0005_admin_guards.sql, with a hand translation in the in-memory
 *     store, and the contract suite asserts the two agree. Re-checking them here
 *     would add a third copy — in the one layer an attacker never has to go
 *     through. What this file adds instead are the rules that need a *read
 *     before the write*, which is not something a constraint can express.
 */

import { addDays, istDateOf, type IsoDate } from '../domain/calendar';
import type { Role } from '../domain/tickets';
import {
  AuthorizationError,
  ValidationError,
  type AuditRecord,
  type Category,
  type ChainVerification,
  type Employee,
  type Holiday,
  type Instant,
  type Repository,
  type Uuid,
} from '../repo/types';

/**
 * The acting employee, if they are an active administrator.
 *
 * Throws rather than returning a boolean: a predicate invites `if (!isAdmin())
 * return` at each call site, and the one place it is forgotten is the hole.
 */
async function requireAdmin(repo: Repository): Promise<Employee> {
  const me = await repo.employees.findById(repo.actor.employeeId);
  if (me === null || me.status !== 'ACTIVE' || me.role !== 'ADMIN') {
    throw new AuthorizationError('administration is restricted to administrators');
  }
  return me;
}

function required(value: string, what: string): string {
  const trimmed = value.trim();
  if (trimmed.length === 0) throw new ValidationError(what);
  return trimmed;
}

function today(): IsoDate {
  return istDateOf(new Date());
}

// -----------------------------------------------------------------------------
// People
// -----------------------------------------------------------------------------

export interface AddEmployeeInput {
  readonly workEmail: string;
  readonly displayName: string;
  readonly role: Role;
  readonly managerId: Uuid | null;
}

/**
 * Add someone to the allow-list. REQUIREMENTS §9.
 *
 * There is no password to issue, so this single row *is* the account: once the
 * address is here, Cloudflare Access will send them a one-time PIN and
 * `resolveIdentity` will find them. That is why the audit payload records the
 * role — adding a colleague and granting them a role are the same action, and the
 * trail should say so in one entry rather than leave it to be inferred.
 */
export async function addEmployee(
  repo: Repository,
  input: AddEmployeeInput,
): Promise<Employee> {
  await requireAdmin(repo);

  const created = await repo.employees.create({
    workEmail: required(input.workEmail, 'a work email address is required'),
    displayName: required(input.displayName, 'a display name is required'),
    role: input.role,
    managerId: input.managerId,
  });

  await repo.audit.append({
    action: 'EMPLOYEE_CREATED',
    entity: 'employees',
    entityId: created.id,
    payload: {
      workEmail: created.workEmail,
      displayName: created.displayName,
      role: created.role,
      managerId: created.managerId,
    },
  });

  return created;
}

export async function setEmployeeRole(
  repo: Repository,
  employeeId: Uuid,
  role: Role,
): Promise<Employee> {
  await requireAdmin(repo);

  // Read first so the audit entry can say what the role WAS. "Alice is now an
  // admin" is a fact; "Alice went from employee to admin" is the finding.
  const before = await repo.employees.findById(employeeId);
  const updated = await repo.employees.setRole(employeeId, role);

  await repo.audit.append({
    action: 'EMPLOYEE_ROLE_CHANGED',
    entity: 'employees',
    entityId: updated.id,
    payload: {
      workEmail: updated.workEmail,
      from: before?.role ?? null,
      to: updated.role,
    },
  });

  return updated;
}

export async function setEmployeeManager(
  repo: Repository,
  employeeId: Uuid,
  managerId: Uuid | null,
): Promise<Employee> {
  await requireAdmin(repo);

  const before = await repo.employees.findById(employeeId);
  const updated = await repo.employees.setManager(employeeId, managerId);

  await repo.audit.append({
    action: 'EMPLOYEE_MANAGER_CHANGED',
    entity: 'employees',
    entityId: updated.id,
    payload: {
      workEmail: updated.workEmail,
      from: before?.managerId ?? null,
      to: updated.managerId,
    },
  });

  return updated;
}

/**
 * Offboard someone. Never a delete — REQUIREMENTS §9.
 *
 * The reason is mandatory and it is recorded in the chain, not only in the row:
 * `employees.deactivated_reason` is a column an admin could later overwrite,
 * whereas the audit entry cannot be changed without breaking the chain. So the
 * durable answer to "why was this account closed" is the one here.
 */
export async function deactivateEmployee(
  repo: Repository,
  employeeId: Uuid,
  reason: string,
): Promise<Employee> {
  await requireAdmin(repo);
  const trimmed = required(reason, 'a reason is required to deactivate someone');

  // Refused here rather than in the store because it needs the current row, and
  // because a second EMPLOYEE_DEACTIVATED entry for an account that was already
  // closed would make the chain read as though it happened twice.
  const before = await repo.employees.findById(employeeId);
  if (before !== null && before.status === 'DEACTIVATED') {
    throw new ValidationError(`${before.workEmail} is already deactivated`);
  }

  const updated = await repo.employees.deactivate(employeeId, trimmed);

  await repo.audit.append({
    action: 'EMPLOYEE_DEACTIVATED',
    entity: 'employees',
    entityId: updated.id,
    payload: { workEmail: updated.workEmail, reason: trimmed },
  });

  return updated;
}

// -----------------------------------------------------------------------------
// Holiday calendar
//
// Audited like everything else, and for a concrete reason: the holiday list is an
// input to every deadline and staleness calculation in the system. Adding a day
// retrospectively changes whether work was late. That must be traceable to a
// person.
// -----------------------------------------------------------------------------

export async function addHoliday(
  repo: Repository,
  date: IsoDate,
  name: string,
): Promise<Holiday> {
  await requireAdmin(repo);
  const created = await repo.calendar.addHoliday(
    date,
    required(name, 'a holiday needs a name'),
  );

  await repo.audit.append({
    action: 'HOLIDAY_ADDED',
    entity: 'holidays',
    entityId: created.date,
    payload: { date: created.date, name: created.name },
  });

  return created;
}

export async function removeHoliday(repo: Repository, date: IsoDate): Promise<void> {
  await requireAdmin(repo);
  await repo.calendar.removeHoliday(date);

  await repo.audit.append({
    action: 'HOLIDAY_REMOVED',
    entity: 'holidays',
    entityId: date,
    payload: { date },
  });
}

// -----------------------------------------------------------------------------
// Categories
// -----------------------------------------------------------------------------

export async function addCategory(repo: Repository, name: string): Promise<Category> {
  await requireAdmin(repo);
  const created = await repo.reference.createCategory(
    required(name, 'a category name is required'),
  );

  await repo.audit.append({
    action: 'CATEGORY_CREATED',
    entity: 'categories',
    entityId: created.id,
    payload: { name: created.name },
  });

  return created;
}

export async function setCategoryActive(
  repo: Repository,
  categoryId: Uuid,
  active: boolean,
): Promise<Category> {
  await requireAdmin(repo);
  const updated = await repo.reference.setCategoryActive(categoryId, active);

  await repo.audit.append({
    action: 'CATEGORY_ACTIVE_CHANGED',
    entity: 'categories',
    entityId: updated.id,
    payload: { name: updated.name, active: updated.active },
  });

  return updated;
}

// -----------------------------------------------------------------------------
// The half-yearly access-rights and privileged-user review
//
// CSCRF PR.AA, all regulated entities, not exempted (DESIGN §8). Two findings are
// asked for by name: accounts that are not being used, and accounts that hold
// privilege. Everything else on the page is context for those two.
// -----------------------------------------------------------------------------

/** DESIGN §8. Calendar days, not working days: dormancy is not a workload measure. */
export const DORMANT_AFTER_DAYS = 90;

export interface AccountReview {
  readonly employee: Employee;
  readonly managerName: string | null;
  /** Last authentication, or null if this account has never signed in. */
  readonly lastLoginAt: Instant | null;
  /** Last access event of any kind — see the note on `buildAccessReview`. */
  readonly lastSeenAt: Instant | null;
  /** No login in over DORMANT_AFTER_DAYS days, or never. */
  readonly dormant: boolean;
  /** ADMIN. Listed whether dormant or not: privilege itself is the finding. */
  readonly privileged: boolean;
}

export interface AccessReview {
  readonly reviewDate: IsoDate;
  readonly accounts: readonly AccountReview[];
  readonly dormantCount: number;
  readonly privilegedCount: number;
  readonly activeCount: number;
  readonly deactivatedCount: number;
}

/**
 * Is this account dormant as at `todayIst`?
 *
 * Exported because it is the one piece of judgement on the page, and a rule
 * embedded in a render function is a rule nobody can test.
 *
 * `istDateOf(new Date(instant))`, never `instant.slice(0, 10)` — the latter is the
 * UTC date, a day early for anything after 18:30 UTC, which would silently shift
 * every boundary case by one day.
 */
export function isDormant(lastLoginAt: Instant | null, todayIst: IsoDate): boolean {
  // Never signed in is the most reviewable state there is: an allow-listed
  // address nobody has ever used is either a mistake or a dormant account.
  if (lastLoginAt === null) return true;
  return istDateOf(new Date(lastLoginAt)) < addDays(todayIst, -DORMANT_AFTER_DAYS);
}

/**
 * Every account, with the facts the reviewer has to sign off on.
 *
 * `lastSeenAt` is here alongside `lastLoginAt` for an honest reason: the
 * authentication path does not yet write a LOGIN access event, so `lastLoginAt`
 * is null for everyone until it does, and a review page that showed only "never"
 * for every row would be worse than useless — it would look like a finding. The
 * last event of any kind is the best available evidence of use meanwhile, and the
 * page labels the two differently so nobody mistakes one for the other.
 *
 * Two queries per account. That is an N+1, and it is deliberate: this page is run
 * twice a year over at most 50 accounts, and a batched port would be a third
 * query shape to keep in step with the other two for no measurable gain.
 */
export async function buildAccessReview(repo: Repository): Promise<AccessReview> {
  await requireAdmin(repo);
  const reviewDate = today();

  const everyone = await repo.employees.listAll();
  const nameById = new Map(everyone.map((e) => [e.id, e.displayName]));

  const accounts: AccountReview[] = [];
  for (const employee of everyone) {
    // Sequential, not Promise.all. Everything in this file runs on ONE database
    // transaction, and issuing two statements on it concurrently depends on the
    // driver queueing them rather than interleaving. Two round trips saved is not
    // worth resting on that.
    const lastLoginAt = await repo.accessLog.lastLoginAt(employee.id);
    const recent = await repo.accessLog.recentFor(employee.id, 1);
    accounts.push({
      employee,
      managerName: employee.managerId === null ? null : (nameById.get(employee.managerId) ?? null),
      lastLoginAt,
      lastSeenAt: recent[0]?.occurredAt ?? null,
      dormant: isDormant(lastLoginAt, reviewDate),
      privileged: employee.role === 'ADMIN',
    });
  }

  // Findings first: privileged accounts, then dormant ones, then the rest.
  const ordered = [...accounts].sort(
    (a, b) =>
      Number(b.privileged) - Number(a.privileged) ||
      Number(b.dormant) - Number(a.dormant) ||
      a.employee.displayName.localeCompare(b.employee.displayName),
  );

  return {
    reviewDate,
    accounts: ordered,
    dormantCount: accounts.filter((a) => a.dormant).length,
    privilegedCount: accounts.filter((a) => a.privileged).length,
    activeCount: accounts.filter((a) => a.employee.status === 'ACTIVE').length,
    deactivatedCount: accounts.filter((a) => a.employee.status === 'DEACTIVATED').length,
  };
}

/**
 * Record that the review was performed, and by whom.
 *
 * DESIGN §8: *"the half-yearly access review is the obligation people forget.
 * Making the tool record that it happened is worth more than the report itself."*
 * This is that entry, and it is in the hash chain rather than a `reviews` table
 * so that it cannot be back-dated or quietly removed.
 *
 * The figures are recomputed here rather than taken from the submitted form. A
 * form value could claim a clean review of numbers nobody looked at; recomputing
 * means the entry states what was true at the moment it was signed.
 */
export async function recordAccessReview(
  repo: Repository,
  note?: string,
): Promise<AuditRecord> {
  const me = await requireAdmin(repo);
  const review = await buildAccessReview(repo);

  return repo.audit.append({
    action: 'ACCESS_REVIEW_PERFORMED',
    entity: 'employees',
    entityId: null,
    payload: {
      reviewDate: review.reviewDate,
      reviewedBy: me.workEmail,
      accounts: review.accounts.length,
      active: review.activeCount,
      deactivated: review.deactivatedCount,
      dormantThresholdDays: DORMANT_AFTER_DAYS,
      // The named lists are the evidence. At 10–50 accounts they fit, and a count
      // alone would not let anyone check the review later.
      privileged: review.accounts.filter((a) => a.privileged).map((a) => a.employee.workEmail),
      dormant: review.accounts.filter((a) => a.dormant).map((a) => a.employee.workEmail),
      ...(note !== undefined && note.trim().length > 0 ? { note: note.trim() } : {}),
    },
  });
}

// -----------------------------------------------------------------------------
// Audit log viewer
// -----------------------------------------------------------------------------

export interface AuditView {
  readonly entries: readonly AuditRecord[];
  readonly verification: ChainVerification;
}

/**
 * The audit log, newest first, with the chain checked.
 *
 * The read is itself audited — REQUIREMENTS §10, "every write audited, including
 * reads of the audit log itself" — and the entry is appended BEFORE verifying.
 * That ordering is deliberate: appending afterwards would display a head hash
 * that was already one entry out of date, and the head hash is the value
 * published as the day's external anchor. Here, what is on screen is the chain as
 * it stands including the act of looking at it.
 *
 * The cost is real and accepted: an admin refreshing this page lengthens the
 * chain. The alternative is a log that does not record who read it, which
 * REQUIREMENTS §10 asks for by name and which is the more valuable of the two for
 * a system whose whole claim is that history cannot be quietly rewritten.
 */
export async function readAuditLog(repo: Repository, limit = 200): Promise<AuditView> {
  await requireAdmin(repo);

  await repo.audit.append({
    action: 'AUDIT_LOG_VIEWED',
    entity: 'audit_log',
    entityId: null,
    payload: { limit },
  });

  const verification = await repo.audit.verify();
  const entries = await repo.audit.list(limit);

  return { entries, verification };
}
