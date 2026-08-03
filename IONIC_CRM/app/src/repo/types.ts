/**
 * The repository seam.
 *
 * Nothing above this layer knows Postgres exists. That is what makes DESIGN.md
 * D6 real: if the store has to move — into the M365 tenant, or onto a
 * self-hosted Postgres because SEBI lifts the localisation abeyance — the work
 * is one new implementation of these interfaces, not a rewrite.
 *
 * Two rules make the seam worth having rather than just ceremonial:
 *
 *  1. IDENTITY IS BOUND AT CONSTRUCTION, not passed per call. A repository is
 *     obtained through `withActor`, so there is no method a caller could forget
 *     to pass an actor to. Under Postgres that also opens the transaction and
 *     sets the GUC that RLS reads, meaning "authorised" is not something the
 *     application layer can accidentally skip.
 *
 *  2. THE ACTOR CARRIES NO ROLE. Only an employee id. If the caller could say
 *     "I am an admin", that claim would eventually be believed. Role is always
 *     read from the store.
 */

import type { IsoDate } from '../domain/calendar';
import type { Priority, Role, TicketStatus } from '../domain/tickets';

export type Uuid = string;

/** An ISO-8601 instant, UTC. */
export type Instant = string;

// -----------------------------------------------------------------------------
// Entities
// -----------------------------------------------------------------------------

export interface Employee {
  readonly id: Uuid;
  readonly workEmail: string;
  readonly displayName: string;
  readonly role: Role;
  readonly managerId: Uuid | null;
  readonly status: 'ACTIVE' | 'DEACTIVATED';
}

export interface Ticket {
  readonly id: Uuid;
  readonly ref: string;
  readonly title: string;
  readonly description: string;
  readonly categoryId: Uuid | null;
  readonly priority: Priority;
  readonly assigneeId: Uuid;
  readonly raiserId: Uuid;
  readonly status: TicketStatus;
  readonly deadline: IsoDate;
  readonly originalDeadline: IsoDate;
  readonly createdAt: Instant;
  readonly closedDate: IsoDate | null;
  readonly cancelReason: string | null;
}

/** One immutable progress record. Never updated, never deleted. */
export interface Punch {
  readonly id: Uuid;
  readonly seq: number;
  readonly ticketId: Uuid;
  readonly actorId: Uuid;
  readonly createdAt: Instant;
  readonly punchDate: IsoDate;
  readonly status: TicketStatus;
  readonly note: string;
  readonly blockedReason: string | null;
  readonly minutesSpent: number | null;
  readonly nextAction: string | null;
  readonly nextActionBy: IsoDate | null;
  readonly correctsUpdateId: Uuid | null;
}

// -----------------------------------------------------------------------------
// Inputs
// -----------------------------------------------------------------------------

export interface NewTicket {
  readonly title: string;
  readonly description?: string;
  readonly categoryId?: Uuid | null;
  readonly priority: Priority;
  readonly assigneeId: Uuid;
  /** Must be the acting employee. Present so the rule is explicit and testable. */
  readonly raiserId: Uuid;
  readonly deadline: IsoDate;
}

export interface NewPunch {
  readonly ticketId: Uuid;
  /** Must be the acting employee. */
  readonly actorId: Uuid;
  readonly punchDate: IsoDate;
  readonly status: TicketStatus;
  readonly note?: string;
  readonly blockedReason?: string | null;
  readonly minutesSpent?: number | null;
  readonly nextAction?: string | null;
  readonly nextActionBy?: IsoDate | null;
  readonly correctsUpdateId?: Uuid | null;
}

export interface TicketFilter {
  readonly assigneeId?: Uuid;
  readonly status?: readonly TicketStatus[];
  /** Exclude DONE and CANCELLED. */
  readonly openOnly?: boolean;
}

export interface Category {
  readonly id: Uuid;
  readonly name: string;
  readonly active: boolean;
}

export interface Holiday {
  readonly date: IsoDate;
  readonly name: string;
}

export interface NewEmployee {
  readonly workEmail: string;
  readonly displayName: string;
  readonly role: Role;
  readonly managerId: Uuid | null;
}

/**
 * A ticket plus the aggregate facts a list view needs.
 *
 * Exists so staleness can be shown without asking for each ticket's history in
 * turn. Fetching N histories to render one page is the classic way a dashboard
 * becomes unusable at exactly the moment it starts being used.
 */
export interface TicketSummary {
  readonly ticket: Ticket;
  /** Date of the most recent punch, or null if never punched. */
  readonly lastPunchDate: IsoDate | null;
  readonly lastPunchBy: Uuid | null;
  readonly punchCount: number;
}

// -----------------------------------------------------------------------------
// Errors
//
// Both implementations must fail the same way, or the fake is a lie. The
// Postgres adapter maps privilege and RLS failures onto these; the in-memory
// one enforces the same rules in code. The contract test asserts they agree.
// -----------------------------------------------------------------------------

export class AuthorizationError extends Error {
  override readonly name = 'AuthorizationError';
  constructor(message: string) {
    super(message);
  }
}

export class ValidationError extends Error {
  override readonly name = 'ValidationError';
  constructor(message: string) {
    super(message);
  }
}

// -----------------------------------------------------------------------------
// Ports
// -----------------------------------------------------------------------------

export interface EmployeeStore {
  /** Identity lookup from the authenticated email. Null when not allow-listed. */
  findByEmail(email: string): Promise<Employee | null>;
  findById(id: Uuid): Promise<Employee | null>;
  /** The internal staff directory: active employees only. */
  listActive(): Promise<Employee[]>;

  /**
   * Everyone, deactivated included, for the admin console and the access review.
   *
   * Not admin-gated, and deliberately so: the `employees_select` policy already
   * lets any signed-in colleague read the directory, and a deactivated person's
   * name is on ticket history everyone can see anyway. Gating this method while
   * `listActive` stays open would be a rule that protects nothing and can drift
   * out of step with the policy. What is admin-only is the console, and the
   * WRITES below.
   */
  listAll(): Promise<Employee[]>;

  /** Admin only. `workEmail` is matched case-insensitively against the existing set. */
  create(input: NewEmployee): Promise<Employee>;
  /** Admin only, and never on yourself — see 0005_admin_guards.sql rule 1. */
  setRole(id: Uuid, role: Role): Promise<Employee>;
  /** Admin only. Refuses self-management and any cycle in the reporting chain. */
  setManager(id: Uuid, managerId: Uuid | null): Promise<Employee>;
  /**
   * Admin only. Offboarding, never deletion.
   *
   * Refuses without a reason, and refuses while the person still holds
   * non-terminal tickets — those must be reassigned first (REQUIREMENTS §9).
   * There is no `delete`: the row outlives the employment, because the punches
   * it authored must keep naming their author.
   */
  deactivate(id: Uuid, reason: string): Promise<Employee>;
}

export interface TicketStore {
  create(input: NewTicket): Promise<Ticket>;
  /** Null when the ticket does not exist OR is not visible — deliberately indistinguishable. */
  findById(id: Uuid): Promise<Ticket | null>;
  findByRef(ref: string): Promise<Ticket | null>;
  list(filter?: TicketFilter): Promise<Ticket[]>;
  /** Same visibility and ordering as `list`, plus last-punch aggregates. */
  listSummaries(filter?: TicketFilter): Promise<TicketSummary[]>;
  addPunch(input: NewPunch): Promise<Punch>;
  /** Chronological. Empty when the ticket is not visible. */
  listPunches(ticketId: Uuid): Promise<Punch[]>;

  /** Apply a status transition. Legality is checked by the service layer. */
  setStatus(change: StatusChange): Promise<Ticket>;
  /** Reassign. The handover note is recorded as a punch by the service layer. */
  setAssignee(ticketId: Uuid, assigneeId: Uuid): Promise<Ticket>;
  /** Move the CURRENT deadline. `original_deadline` is immutable in the database. */
  setDeadline(ticketId: Uuid, deadline: IsoDate): Promise<Ticket>;

  requestDeadlineChange(input: {
    readonly ticketId: Uuid;
    readonly toDate: IsoDate;
    readonly reason: string;
  }): Promise<DeadlineChange>;
  listDeadlineChanges(ticketId: Uuid): Promise<DeadlineChange[]>;
  decideDeadlineChange(id: Uuid, decision: 'APPROVED' | 'REJECTED'): Promise<DeadlineChange>;
}

export interface CalendarStore {
  /** Injected into every date calculation; never read from a global. */
  holidays(): Promise<ReadonlySet<IsoDate>>;
  /** The same days with their names, for the admin calendar. Date ascending. */
  listHolidays(): Promise<Holiday[]>;
  /** Admin only. A date already present is a ValidationError, not a silent overwrite. */
  addHoliday(date: IsoDate, name: string): Promise<Holiday>;
  /** Admin only. Removing a date that is not a holiday is refused, not ignored. */
  removeHoliday(date: IsoDate): Promise<void>;
}

export interface ReferenceStore {
  /** Active categories, for pickers. Admin maintains the list. */
  categories(): Promise<Category[]>;
  /**
   * Active AND inactive, for the admin console.
   *
   * Separate from `categories()` because a picker must never offer a retired
   * category, while the console must be able to see one in order to bring it
   * back. Without this, `setCategoryActive(id, false)` would be one-way: the row
   * would vanish from every list that could supply its id.
   */
  allCategories(): Promise<Category[]>;
  /** Admin only. Names are unique; a duplicate is a ValidationError. */
  createCategory(name: string): Promise<Category>;
  /** Admin only. Retire or restore. Categories are never deleted — tickets reference them. */
  setCategoryActive(id: Uuid, active: boolean): Promise<Category>;
}

// -----------------------------------------------------------------------------
// Mutations beyond insert
//
// Note what is NOT here: no `updatePunch`, no `deletePunch`, no `setOriginalDeadline`.
// The absence is the design. A method that does not exist cannot be called by
// mistake, and the database refuses those operations anyway (0002_append_only.sql),
// so offering them would only produce runtime errors instead of compile errors.
// -----------------------------------------------------------------------------

export interface DeadlineChange {
  readonly id: Uuid;
  readonly ticketId: Uuid;
  readonly fromDate: IsoDate;
  readonly toDate: IsoDate;
  readonly reason: string;
  readonly requestedBy: Uuid;
  readonly requestedAt: Instant;
  readonly decision: 'PENDING' | 'APPROVED' | 'REJECTED';
  readonly approvedBy: Uuid | null;
  readonly decidedAt: Instant | null;
}

export interface StatusChange {
  readonly ticketId: Uuid;
  readonly status: TicketStatus;
  /** Required when moving to a terminal state. */
  readonly closedDate?: IsoDate | null;
  readonly cancelReason?: string | null;
}

// -----------------------------------------------------------------------------
// Audit chain
// -----------------------------------------------------------------------------

export type AuditPayload = Readonly<Record<string, unknown>>;

export interface AuditEntryInput {
  readonly action: string;
  readonly entity: string;
  readonly entityId: string | null;
  readonly payload: AuditPayload;
}

export interface AuditRecord extends AuditEntryInput {
  readonly seq: number;
  readonly occurredAt: string;
  readonly actorId: Uuid | null;
  readonly prevHashHex: string;
  readonly rowHashHex: string;
}

export interface ChainVerification {
  readonly ok: boolean;
  readonly checked: number;
  /** The value to publish as the day's external anchor. */
  readonly headHashHex: string | null;
  readonly failures: readonly string[];
}

export interface AuditStore {
  /**
   * Append one entry. The actor is taken from the bound repository, never from
   * the caller — an audit trail whose author is a parameter is not an audit trail.
   */
  append(entry: AuditEntryInput): Promise<AuditRecord>;
  /** Admin-only; empty for anyone else. Newest first. */
  list(limit?: number): Promise<AuditRecord[]>;
  /** Recompute the whole chain. Admin-only. */
  verify(): Promise<ChainVerification>;
}

// -----------------------------------------------------------------------------
// Access events — CSCRF PR.AA 1(e), two-year retention
// -----------------------------------------------------------------------------

export type AccessEventKind = 'LOGIN' | 'VIEW' | 'LIST' | 'EXPORT' | 'ADMIN_ACTION' | 'DENIED';

export interface AccessEventInput {
  readonly event: AccessEventKind;
  readonly entity?: string | null;
  readonly entityId?: string | null;
  readonly ip?: string | null;
  readonly userAgent?: string | null;
}

export interface AccessEventRecord {
  readonly seq: number;
  readonly occurredAt: Instant;
  readonly employeeId: Uuid | null;
  readonly event: AccessEventKind;
  readonly entity: string | null;
  readonly entityId: string | null;
}

export interface AccessLog {
  record(e: AccessEventInput): Promise<void>;
  /**
   * One person's most recent access events, newest first.
   *
   * Admin-only — the `access_events_admin_select` policy returns nothing to
   * anyone else, and the in-memory store mirrors that. `ip` and `user_agent` are
   * deliberately not returned: the access review needs to know *when* an account
   * was last used, and a screen that renders client fingerprints for every
   * colleague is a privacy cost with no reviewer benefit.
   */
  recentFor(employeeId: Uuid, limit?: number): Promise<AccessEventRecord[]>;
  /**
   * When this account last authenticated, or null if never — the number the
   * half-yearly access review is actually about (DESIGN §8).
   *
   * LOGIN specifically, not "last activity". A dormant account with a live
   * session would otherwise look current, which inverts the finding.
   */
  lastLoginAt(employeeId: Uuid): Promise<Instant | null>;
}

export interface Repository {
  readonly actor: Actor;
  readonly employees: EmployeeStore;
  readonly tickets: TicketStore;
  readonly calendar: CalendarStore;
  readonly reference: ReferenceStore;
  readonly audit: AuditStore;
  readonly accessLog: AccessLog;
}

/** Carries an id and nothing else. See rule 2 in the file header. */
export interface Actor {
  readonly employeeId: Uuid;
}

export interface RepositoryFactory {
  /**
   * Run `fn` with a repository bound to `actor`.
   *
   * Under Postgres this opens a transaction, sets the identity GUC and drops to
   * the non-privileged role, so RLS is in force for everything `fn` does. The
   * repository must not be used after `fn` resolves.
   */
  withActor<T>(actor: Actor, fn: (repo: Repository) => Promise<T>): Promise<T>;

  /**
   * Resolve a verified email to an employee, BEFORE any actor exists.
   *
   * The one pre-authorisation query in the system, and deliberately the only
   * one. Returns ACTIVE employees only, so a deactivated person is simply not
   * found and offboarding takes effect without a separate check anyone could
   * forget. Null means "not allow-listed" — which is also the answer for an
   * address that was never a colleague, so it leaks nothing either way.
   *
   * Backed by `app.resolve_identity()` (db/migrations/0004_identity.sql), which
   * cannot enumerate the table.
   */
  resolveIdentity(email: string): Promise<Employee | null>;

  close(): Promise<void>;
}
