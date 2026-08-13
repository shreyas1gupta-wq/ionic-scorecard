/**
 * In-memory repository.
 *
 * Not a mock. It re-implements the same authorisation and validation rules the
 * database enforces, and `contract.test.ts` runs one suite against both this and
 * the Postgres adapter. If the two ever diverge, that suite fails — which is the
 * only thing that makes a fake safe to develop and test against.
 *
 * The visibility predicate here is a hand translation of the `tickets_select`
 * RLS policy in db/migrations/0003_rls.sql. When one changes, the other must.
 */

import { formatTicketRef } from '../domain/ticket-ref';
import { GENESIS_HASH, linkRow, verifyChain, type AuditRow } from '../domain/hash-chain';
import type { IsoDate } from '../domain/calendar';
import {
  AuthorizationError,
  ValidationError,
  type AccessEventInput,
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
  type Holiday,
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

interface State {
  employees: Employee[];
  tickets: Ticket[];
  punches: Punch[];
  watchers: { ticketId: Uuid; employeeId: Uuid }[];
  deadlineChanges: DeadlineChange[];
  auditRows: AuditRow[];
  accessEvents: AccessEventRecord[];
  holidayRows: Holiday[];
  categoryRows: Category[];
  refCounters: Map<number, number>;
  nextPunchSeq: number;
  nextAuditSeq: number;
  nextAccessSeq: number;
  idCounter: number;
}

/**
 * Managers are named by email, not id, because ids do not exist until seeding
 * runs. Resolved in a second pass below.
 */
export interface MemorySeedEmployee {
  readonly workEmail: string;
  readonly displayName: string;
  readonly role: Employee['role'];
  readonly status?: Employee['status'];
  readonly managerEmail?: string;
}

export interface MemorySeed {
  readonly employees: readonly MemorySeedEmployee[];
  /**
   * A bare date or a date with its name.
   *
   * The bare form exists so a dev seed need not invent a name for every day it
   * blocks out; the named form is what the test fixtures use, so the contract
   * suite can assert that both stores return the same holiday name.
   */
  readonly holidays?: readonly (IsoDate | Holiday)[];
  /** Named categories. Takes precedence over `categoryCount`. */
  readonly categories?: readonly string[];
  readonly categoryCount?: number;
}

export interface MemoryRepositoryFactory extends RepositoryFactory {
  /** Insert a ticket bypassing authorisation. Arranging test state only. */
  seedTicket(t: Omit<Ticket, 'id' | 'ref' | 'createdAt'> & { ref?: string }): Ticket;
  addWatcher(ticketId: Uuid, employeeId: Uuid): void;
  idByEmail(email: string): Uuid;
  categoryIds(): Uuid[];
  /** Clear transactional data, keeping employees, categories and holidays.
   *  Mirrors `resetTransactionalData` on the Postgres side. */
  reset(): void;
}

export function createMemoryRepository(seed: MemorySeed): MemoryRepositoryFactory {
  const state: State = {
    employees: [],
    tickets: [],
    punches: [],
    watchers: [],
    deadlineChanges: [],
    auditRows: [],
    accessEvents: [],
    holidayRows: (seed.holidays ?? []).map((h) =>
      typeof h === 'string' ? { date: h, name: 'Holiday' } : h,
    ),
    categoryRows: [],
    refCounters: new Map(),
    nextPunchSeq: 1,
    nextAuditSeq: 1,
    nextAccessSeq: 1,
    idCounter: 0,
  };

  const newId = (prefix: string): Uuid => {
    state.idCounter += 1;
    // Shaped like a uuid so nothing downstream can depend on the format.
    return `${prefix}${String(state.idCounter).padStart(8, '0')}-0000-4000-8000-000000000000`;
  };

  // Pass 1: create rows without manager links.
  for (const e of seed.employees) {
    state.employees.push({
      id: newId('e'),
      workEmail: e.workEmail.trim().toLowerCase(),
      displayName: e.displayName,
      role: e.role,
      status: e.status ?? 'ACTIVE',
      managerId: null,
    });
  }
  // Pass 2: resolve manager emails to the ids just minted.
  seed.employees.forEach((e, i) => {
    if (!e.managerEmail) return;
    const target = e.managerEmail.trim().toLowerCase();
    const manager = state.employees.find((x) => x.workEmail === target);
    if (!manager) throw new Error(`seed error: unknown managerEmail ${e.managerEmail}`);
    const row = state.employees[i]!;
    state.employees[i] = { ...row, managerId: manager.id };
  });

  const categoryNames =
    seed.categories ?? Array.from({ length: seed.categoryCount ?? 1 }, (_, i) => `Category ${i + 1}`);
  for (const name of categoryNames) {
    state.categoryRows.push({ id: newId('c'), name, active: true });
  }

  const employeeById = (id: Uuid): Employee | null =>
    state.employees.find((e) => e.id === id) ?? null;

  /** Active employees only: a deactivated actor has no role and no visibility. */
  const activeActor = (actorId: Uuid): Employee | null => {
    const e = employeeById(actorId);
    return e && e.status === 'ACTIVE' ? e : null;
  };

  /** Hand translation of the tickets_select RLS policy. Keep in step with 0003. */
  const canSee = (actorId: Uuid, t: Ticket): boolean => {
    const me = activeActor(actorId);
    if (!me) return false;
    if (me.role === 'ADMIN') return true;
    if (t.assigneeId === actorId) return true;
    if (t.raiserId === actorId) return true;
    if (state.watchers.some((w) => w.ticketId === t.id && w.employeeId === actorId)) return true;
    const assignee = employeeById(t.assigneeId);
    if (assignee && assignee.managerId === actorId) return true;
    return false;
  };

  const isAdmin = (actorId: Uuid): boolean => activeActor(actorId)?.role === 'ADMIN';

  /**
   * Hand translation of the `*_admin_write` policies in 0003.
   *
   * Under Postgres a non-admin write simply matches no row, and the adapter turns
   * that into the same indistinguishable AuthorizationError raised here. Keeping
   * the two identical is what the contract suite checks.
   */
  const requireAdmin = (actorId: Uuid): void => {
    if (!isAdmin(actorId)) {
      throw new AuthorizationError('not visible or not permitted: administration');
    }
  };

  /** Hand translation of requireRow() in postgres.ts. */
  const notFound = (id: string): never => {
    throw new AuthorizationError(`not visible or not permitted: ${id}`);
  };

  /**
   * Hand translation of employees_guard_manager_cycle (0005).
   *
   * Walks upward from the proposed manager; reaching `subject` means the edge
   * closes a loop. Reads the CURRENT chain, exactly as the BEFORE trigger does.
   */
  const wouldCycle = (subject: Uuid, managerId: Uuid | null): boolean => {
    let cursor = managerId;
    let hops = 0;
    while (cursor !== null) {
      if (cursor === subject) return true;
      hops += 1;
      if (hops > 64) return true;
      cursor = employeeById(cursor)?.managerId ?? null;
    }
    return false;
  };

  const replaceEmployee = (e: Employee): Employee => {
    const i = state.employees.findIndex((x) => x.id === e.id);
    if (i >= 0) state.employees[i] = e;
    return e;
  };

  /** Hand translation of the tickets_update policy. Keep in step with 0003. */
  const canWrite = (actorId: Uuid, t: Ticket): boolean => {
    const me = activeActor(actorId);
    if (!me) return false;
    if (me.role === 'ADMIN') return true;
    if (t.assigneeId === actorId) return true;
    const assignee = employeeById(t.assigneeId);
    return assignee !== null && assignee.managerId === actorId;
    // The raiser is deliberately absent: raising work does not confer control
    // over how it is done.
  };

  const mutableTicket = (actorId: Uuid, ticketId: Uuid): Ticket => {
    const t = state.tickets.find((x) => x.id === ticketId);
    if (!t || !canWrite(actorId, t)) {
      // Same message whether it is missing, invisible or forbidden — see the
      // note on requireRow in postgres.ts.
      throw new AuthorizationError(`not visible or not permitted: ${ticketId}`);
    }
    return t;
  };

  const replaceTicket = (t: Ticket): void => {
    const i = state.tickets.findIndex((x) => x.id === t.id);
    if (i >= 0) state.tickets[i] = t;
  };

  function buildRepository(actor: Actor): Repository {
    const employees: EmployeeStore = {
      async findByEmail(email) {
        const target = email.trim().toLowerCase();
        return state.employees.find((e) => e.workEmail === target) ?? null;
      },
      async findById(id) {
        // Mirrors the employees_select policy: any signed-in employee may read
        // the directory, nobody signed out may read anything.
        if (!activeActor(actor.employeeId)) return null;
        return employeeById(id);
      },
      async listActive() {
        if (!activeActor(actor.employeeId)) return [];
        return state.employees.filter((e) => e.status === 'ACTIVE');
      },

      async listAll() {
        if (!activeActor(actor.employeeId)) return [];
        return state.employees
          .slice()
          .sort((a, b) => a.displayName.localeCompare(b.displayName));
      },

      async create(input: NewEmployee) {
        requireAdmin(actor.employeeId);
        const workEmail = input.workEmail.trim().toLowerCase();
        // Mirrors the work_email CHECK in 0001: lowercase, and an address rather
        // than a bare word.
        if (workEmail.indexOf('@') < 1) {
          throw new ValidationError('a work email address is required');
        }
        if (input.displayName.trim().length === 0) {
          throw new ValidationError('a display name is required');
        }
        // The stored column is already lowercase, so the unique index is
        // case-insensitive in effect. Lowercasing the input is what makes it so.
        if (state.employees.some((e) => e.workEmail === workEmail)) {
          throw new ValidationError(`${workEmail} is already on the allow-list`);
        }
        if (input.managerId !== null && !employeeById(input.managerId)) {
          throw new ValidationError(`unknown manager ${input.managerId}`);
        }
        const created: Employee = {
          id: newId('e'),
          workEmail,
          displayName: input.displayName.trim(),
          role: input.role,
          managerId: input.managerId,
          status: 'ACTIVE',
        };
        state.employees.push(created);
        return created;
      },

      async setRole(id, role) {
        requireAdmin(actor.employeeId);
        const e = employeeById(id);
        if (!e) return notFound(id);
        // Hand translation of employees_guard_self_role (0005), including its
        // `new.role is distinct from old.role`: refusing a no-op would be a rule
        // the database does not have, and a fake that is stricter than the store
        // it stands in for is still a fake that lies.
        if (id === actor.employeeId && e.role !== role) {
          throw new AuthorizationError('you cannot change your own role');
        }
        return replaceEmployee({ ...e, role });
      },

      async setManager(id, managerId) {
        requireAdmin(actor.employeeId);
        const e = employeeById(id);
        if (!e) return notFound(id);
        if (managerId !== null && !employeeById(managerId)) {
          throw new ValidationError(`unknown manager ${managerId}`);
        }
        if (managerId === id) {
          throw new ValidationError('an employee cannot manage themselves');
        }
        if (wouldCycle(id, managerId)) {
          throw new ValidationError(
            `that would make ${e.workEmail} manage themselves through the reporting chain`,
          );
        }
        return replaceEmployee({ ...e, managerId });
      },

      async deactivate(id, reason) {
        requireAdmin(actor.employeeId);
        const e = employeeById(id);
        if (!e) return notFound(id);

        // Order mirrors Postgres: a BEFORE ROW trigger runs before CHECK
        // constraints, so the open-work refusal wins over the missing-reason one
        // when both apply. Same rule, same message, either store.
        if (e.status !== 'DEACTIVATED') {
          const open = state.tickets.filter(
            (t) => t.assigneeId === id && t.status !== 'DONE' && t.status !== 'CANCELLED',
          ).length;
          if (open > 0) {
            throw new ValidationError(
              `reassign ${open} open ticket(s) before deactivating ${e.workEmail}`,
            );
          }
        }
        if (reason.trim().length === 0) {
          throw new ValidationError('a reason is required to deactivate someone');
        }
        // The reason is not kept here because `Employee` does not expose it. The
        // durable record of WHY someone was offboarded is the audit entry the
        // service writes, which is where a reviewer would look for it anyway.
        return replaceEmployee({ ...e, status: 'DEACTIVATED' });
      },
    };

    const tickets: TicketStore = {
      async create(input: NewTicket) {
        const me = activeActor(actor.employeeId);
        if (!me) throw new AuthorizationError('no active employee for actor');
        if (input.raiserId !== actor.employeeId) {
          throw new AuthorizationError('raiser_id must be the acting employee');
        }
        if (!employeeById(input.assigneeId)) {
          throw new ValidationError(`unknown assignee ${input.assigneeId}`);
        }
        if (input.title.trim().length === 0) {
          throw new ValidationError('title is required');
        }
        const year = Number(input.deadline.slice(0, 4));
        const next = (state.refCounters.get(year) ?? 0) + 1;
        state.refCounters.set(year, next);

        const t: Ticket = {
          id: newId('t'),
          ref: formatTicketRef(year, next),
          title: input.title,
          description: input.description ?? '',
          categoryId: input.categoryId ?? null,
          priority: input.priority,
          assigneeId: input.assigneeId,
          raiserId: input.raiserId,
          status: 'OPEN',
          deadline: input.deadline,
          originalDeadline: input.deadline,
          createdAt: FIXED_INSTANT,
          closedDate: null,
          cancelReason: null,
        };
        state.tickets.push(t);
        return t;
      },

      async findById(id) {
        const t = state.tickets.find((x) => x.id === id);
        if (!t) return null;
        return canSee(actor.employeeId, t) ? t : null;
      },

      async findByRef(ref) {
        const t = state.tickets.find((x) => x.ref === ref);
        if (!t) return null;
        return canSee(actor.employeeId, t) ? t : null;
      },

      async list(filter?: TicketFilter) {
        return state.tickets
          .filter((t) => canSee(actor.employeeId, t))
          .filter((t) => (filter?.assigneeId ? t.assigneeId === filter.assigneeId : true))
          .filter((t) => (filter?.status ? filter.status.includes(t.status) : true))
          .filter((t) =>
            filter?.openOnly ? t.status !== 'DONE' && t.status !== 'CANCELLED' : true,
          )
          .slice()
          .sort((a, b) => (a.deadline < b.deadline ? -1 : a.deadline > b.deadline ? 1 : 0));
      },

      async listSummaries(filter?: TicketFilter) {
        const visible = await this.list(filter);
        return visible.map((t) => {
          const own = state.punches
            .filter((p) => p.ticketId === t.id)
            .sort((a, b) => a.seq - b.seq);
          const last = own.at(-1) ?? null;
          return {
            ticket: t,
            // max() over punch dates, matching the SQL aggregate - the latest
            // date recorded, not the date of the highest-seq row, which can
            // differ if someone backdates.
            lastPunchDate:
              own.length === 0
                ? null
                : own.map((p) => p.punchDate).reduce((a, b) => (a > b ? a : b)),
            lastPunchBy: last?.actorId ?? null,
            punchCount: own.length,
          };
        });
      },

      async addPunch(input: NewPunch) {
        if (input.actorId !== actor.employeeId) {
          throw new AuthorizationError('actor_id must be the acting employee');
        }
        const t = state.tickets.find((x) => x.id === input.ticketId);
        if (!t || !canSee(actor.employeeId, t)) {
          throw new AuthorizationError(`ticket ${input.ticketId} is not visible`);
        }
        if (input.status === 'BLOCKED' && (input.blockedReason ?? '').trim().length === 0) {
          throw new ValidationError('blocked_reason is required when status is BLOCKED');
        }
        if (
          input.minutesSpent !== undefined &&
          input.minutesSpent !== null &&
          (input.minutesSpent < 0 || input.minutesSpent > 1440)
        ) {
          throw new ValidationError('minutes_spent must be between 0 and 1440');
        }
        const p: Punch = {
          id: newId('p'),
          seq: state.nextPunchSeq++,
          ticketId: input.ticketId,
          actorId: input.actorId,
          createdAt: FIXED_INSTANT,
          punchDate: input.punchDate,
          status: input.status,
          note: input.note ?? '',
          blockedReason: input.blockedReason ?? null,
          minutesSpent: input.minutesSpent ?? null,
          nextAction: input.nextAction ?? null,
          nextActionBy: input.nextActionBy ?? null,
          correctsUpdateId: input.correctsUpdateId ?? null,
        };
        state.punches.push(p);
        return p;
      },

      async listPunches(ticketId) {
        const t = state.tickets.find((x) => x.id === ticketId);
        if (!t || !canSee(actor.employeeId, t)) return [];
        return state.punches.filter((p) => p.ticketId === ticketId).sort((a, b) => a.seq - b.seq);
      },

      async setStatus(change) {
        const t = mutableTicket(actor.employeeId, change.ticketId);
        const patched: Ticket = {
          ...t,
          status: change.status,
          closedDate:
            change.status === 'DONE' || change.status === 'CANCELLED'
              ? (change.closedDate ?? null)
              : null,
          cancelReason:
            change.status === 'CANCELLED' ? (change.cancelReason ?? null) : t.cancelReason,
        };
        replaceTicket(patched);
        return patched;
      },

      async setAssignee(ticketId, assigneeId) {
        const t = mutableTicket(actor.employeeId, ticketId);
        if (!employeeById(assigneeId)) {
          throw new ValidationError(`unknown assignee ${assigneeId}`);
        }
        const patched = { ...t, assigneeId };
        replaceTicket(patched);
        return patched;
      },

      async setDeadline(ticketId, deadline) {
        const t = mutableTicket(actor.employeeId, ticketId);
        // originalDeadline is intentionally not touched; the database enforces the
        // same thing with a trigger.
        const patched = { ...t, deadline };
        replaceTicket(patched);
        return patched;
      },

      async requestDeadlineChange(input) {
        const t = state.tickets.find((x) => x.id === input.ticketId);
        if (!t || !canSee(actor.employeeId, t)) {
          throw new AuthorizationError(`ticket ${input.ticketId} is not visible`);
        }
        if (input.reason.trim().length === 0) {
          throw new ValidationError('a reason is required to move a deadline');
        }
        if (input.toDate === t.deadline) {
          throw new ValidationError('the new deadline is the same as the current one');
        }
        const change: DeadlineChange = {
          id: newId('d'),
          ticketId: t.id,
          fromDate: t.deadline,
          toDate: input.toDate,
          reason: input.reason,
          requestedBy: actor.employeeId,
          requestedAt: FIXED_INSTANT,
          decision: 'PENDING',
          approvedBy: null,
          decidedAt: null,
        };
        state.deadlineChanges.push(change);
        return change;
      },

      async listDeadlineChanges(ticketId) {
        const t = state.tickets.find((x) => x.id === ticketId);
        if (!t || !canSee(actor.employeeId, t)) return [];
        return state.deadlineChanges.filter((d) => d.ticketId === ticketId);
      },

      async decideDeadlineChange(id, decision) {
        const i = state.deadlineChanges.findIndex((d) => d.id === id);
        const existing = i >= 0 ? state.deadlineChanges[i]! : undefined;
        const t = existing ? state.tickets.find((x) => x.id === existing.ticketId) : undefined;

        // Mirrors the deadline_changes_decide policy: admin, or the assignee's
        // manager. Deliberately not the requester — self-approval would make the
        // approval meaningless.
        const me = activeActor(actor.employeeId);
        const assignee = t ? employeeById(t.assigneeId) : null;
        const permitted =
          me !== null &&
          (me.role === 'ADMIN' || (assignee !== null && assignee.managerId === actor.employeeId));

        if (!existing || !t || existing.decision !== 'PENDING' || !permitted) {
          throw new AuthorizationError(`not visible or not permitted: ${id}`);
        }
        const decided: DeadlineChange = {
          ...existing,
          decision,
          approvedBy: actor.employeeId,
          decidedAt: FIXED_INSTANT,
        };
        state.deadlineChanges[i] = decided;
        return decided;
      },
    };

    const audit: AuditStore = {
      async append(entry) {
        const prev =
          state.auditRows.length === 0
            ? GENESIS_HASH
            : state.auditRows[state.auditRows.length - 1]!.rowHash;
        const seq = state.nextAuditSeq++;
        const row = linkRow(prev, {
          seq,
          // Derived from seq rather than the clock, so a chain built in a test is
          // reproducible. The Postgres side uses the database's now().
          occurredAt: auditInstant(seq),
          actorId: actor.employeeId,
          action: entry.action,
          entity: entry.entity,
          entityId: entry.entityId,
          payload: entry.payload as never,
        });
        state.auditRows.push(row);
        return {
          ...entry,
          seq,
          occurredAt: row.occurredAt,
          actorId: actor.employeeId,
          prevHashHex: row.prevHash.toString('hex'),
          rowHashHex: row.rowHash.toString('hex'),
        };
      },

      async list(limit = 200) {
        if (!isAdmin(actor.employeeId)) return [];
        return state.auditRows
          .slice()
          .reverse()
          .slice(0, limit)
          .map(
            (r): AuditRecord => ({
              seq: Number(r.seq),
              occurredAt: r.occurredAt,
              actorId: r.actorId,
              action: r.action,
              entity: r.entity,
              entityId: r.entityId,
              payload: r.payload as Record<string, unknown>,
              prevHashHex: r.prevHash.toString('hex'),
              rowHashHex: r.rowHash.toString('hex'),
            }),
          );
      },

      async verify() {
        const result = verifyChain(state.auditRows);
        return {
          ok: result.ok,
          checked: result.checked,
          headHashHex: result.headHash,
          failures: result.failures.map((f) => JSON.stringify(f)),
        };
      },
    };

    const byName = (a: { name: string }, b: { name: string }) => a.name.localeCompare(b.name);

    const reference: ReferenceStore = {
      async categories() {
        return state.categoryRows.filter((c) => c.active).sort(byName);
      },

      async allCategories() {
        return state.categoryRows.slice().sort(byName);
      },

      async createCategory(name) {
        requireAdmin(actor.employeeId);
        const trimmed = name.trim();
        if (trimmed.length === 0) throw new ValidationError('a category name is required');
        if (state.categoryRows.some((c) => c.name === trimmed)) {
          throw new ValidationError(`there is already a category called ${trimmed}`);
        }
        const created: Category = { id: newId('c'), name: trimmed, active: true };
        state.categoryRows.push(created);
        return created;
      },

      async setCategoryActive(id, active) {
        requireAdmin(actor.employeeId);
        const i = state.categoryRows.findIndex((c) => c.id === id);
        const existing = i >= 0 ? state.categoryRows[i]! : undefined;
        if (!existing) return notFound(id);
        const updated: Category = { ...existing, active };
        state.categoryRows[i] = updated;
        return updated;
      },
    };

    const accessLog: AccessLog = {
      async record(e) {
        const seq = state.nextAccessSeq++;
        state.accessEvents.push({
          seq,
          // The real clock here, unlike `createdAt` and the audit chain.
          //
          // Nothing hashes this value and nothing compares it to a fixture, so
          // determinism buys nothing — while a FIXED timestamp would silently rot:
          // "when was this account last used" is measured against today, so a
          // login frozen at a date in the past becomes dormant as the calendar
          // moves, and the access-review tests would start failing on a date
          // nobody chose. Ordering still comes from `seq`, not from this.
          occurredAt: new Date().toISOString(),
          employeeId: actor.employeeId,
          event: e.event,
          entity: e.entity ?? null,
          entityId: e.entityId ?? null,
        });
      },

      async recentFor(employeeId, limit = 20) {
        // Mirrors access_events_admin_select: nothing at all for anyone else.
        if (!isAdmin(actor.employeeId)) return [];
        return state.accessEvents
          .filter((e) => e.employeeId === employeeId)
          .sort((a, b) => b.seq - a.seq)
          .slice(0, limit);
      },

      async lastLoginAt(employeeId) {
        if (!isAdmin(actor.employeeId)) return null;
        const logins = state.accessEvents.filter(
          (e) => e.employeeId === employeeId && e.event === 'LOGIN',
        );
        return logins.length === 0
          ? null
          : logins.reduce((a, b) => (a.seq > b.seq ? a : b)).occurredAt;
      },
    };

    const calendar: CalendarStore = {
      async holidays() {
        return new Set(state.holidayRows.map((h) => h.date));
      },

      async listHolidays() {
        if (!activeActor(actor.employeeId)) return [];
        return state.holidayRows.slice().sort((a, b) => (a.date < b.date ? -1 : 1));
      },

      async addHoliday(date, name) {
        requireAdmin(actor.employeeId);
        if (name.trim().length === 0) throw new ValidationError('a holiday needs a name');
        if (state.holidayRows.some((h) => h.date === date)) {
          throw new ValidationError(`${date} is already in the calendar`);
        }
        const created: Holiday = { date, name: name.trim() };
        state.holidayRows.push(created);
        return created;
      },

      async removeHoliday(date) {
        requireAdmin(actor.employeeId);
        const i = state.holidayRows.findIndex((h) => h.date === date);
        if (i < 0) notFound(date);
        state.holidayRows.splice(i, 1);
      },
    };

    return { actor, employees, tickets, calendar, reference, audit, accessLog };
  }

  return {
    async withActor(actor, fn) {
      return fn(buildRepository(actor));
    },
    async resolveIdentity(email) {
      // Mirrors app.resolve_identity(): ACTIVE only, so a deactivated employee
      // is simply not found rather than found-and-then-rejected.
      const target = email.trim().toLowerCase();
      return state.employees.find((e) => e.workEmail === target && e.status === 'ACTIVE') ?? null;
    },

    async close() {
      /* nothing to release */
    },
    seedTicket(t) {
      const year = Number(t.deadline.slice(0, 4));
      const next = (state.refCounters.get(year) ?? 0) + 1;
      state.refCounters.set(year, next);
      const ticket: Ticket = {
        ...t,
        id: newId('t'),
        ref: t.ref ?? formatTicketRef(year, next),
        createdAt: FIXED_INSTANT,
      };
      state.tickets.push(ticket);
      return ticket;
    },
    addWatcher(ticketId, employeeId) {
      if (!state.watchers.some((w) => w.ticketId === ticketId && w.employeeId === employeeId)) {
        state.watchers.push({ ticketId, employeeId });
      }
    },
    idByEmail(email) {
      const target = email.trim().toLowerCase();
      const found = state.employees.find((e) => e.workEmail === target);
      if (!found) throw new Error(`no seeded employee with email ${email}`);
      return found.id;
    },
    reset() {
      state.tickets.length = 0;
      state.punches.length = 0;
      state.watchers.length = 0;
      state.deadlineChanges.length = 0;
      state.auditRows.length = 0;
      state.accessEvents.length = 0;
      state.refCounters.clear();
      state.nextPunchSeq = 1;
      state.nextAuditSeq = 1;
      state.nextAccessSeq = 1;
    },
    categoryIds() {
      return state.categoryRows.map((c) => c.id);
    },
  };
}

/**
 * A fixed created-at.
 *
 * The fake must not read the clock: a repository that stamps Date.now() makes
 * every test that compares records non-deterministic, and `createdAt` is never
 * the thing under test here. The real adapter uses the database's now().
 */
const FIXED_INSTANT = '2026-08-03T00:00:00.000Z';

/**
 * Audit timestamps derived from the sequence number, not the clock.
 *
 * The chain hashes `occurredAt`, so a clock-derived value would make a chain
 * built in a test unreproducible between runs. The Postgres side uses the
 * database's `now()`, which is the right authority in production.
 */
const AUDIT_EPOCH_MS = Date.parse('2026-08-03T00:00:00.000Z');

function auditInstant(seq: number): string {
  return new Date(AUDIT_EPOCH_MS + seq * 1000)
    .toISOString()
    .replace(/\.(\d{3})Z$/, '.$1000Z');
}
