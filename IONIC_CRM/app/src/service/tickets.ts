/**
 * Ticket operations — where the domain rules and the audit trail meet.
 *
 * The repository is deliberately dumb: it reads and writes rows under RLS. The
 * rules that make this a *disciplined* tracker rather than a task list live here:
 *
 *   - a status change is legal only per the transition table (domain/tickets.ts);
 *   - a status change ALWAYS produces a punch, so there is no way to move a ticket
 *     without leaving a record of who moved it and why;
 *   - a deadline cannot move until somebody has said where things stand;
 *   - a reassignment requires a handover note, recorded as a punch;
 *   - every one of these writes an audit entry into the hash chain.
 *
 * Everything runs inside the caller's `withActor` transaction, so a failure
 * anywhere rolls the whole thing back. A punch without its audit row, or a status
 * change without its punch, cannot be left behind.
 */

import { istDateOf, type IsoDate } from '../domain/calendar';
import {
  checkTransition,
  type Priority,
  type TicketStatus,
  type TransitionActor,
} from '../domain/tickets';
import {
  ValidationError,
  AuthorizationError,
  type DeadlineChange,
  type Punch,
  type Repository,
  type Ticket,
  type Uuid,
} from '../repo/types';

/** What the acting person is *to this ticket*. Computed, never supplied. */
export async function actorRoles(
  repo: Repository,
  ticket: Ticket,
): Promise<Set<TransitionActor>> {
  const me = await repo.employees.findById(repo.actor.employeeId);
  if (me === null) throw new AuthorizationError('acting employee not found');

  const roles = new Set<TransitionActor>();
  if (ticket.assigneeId === repo.actor.employeeId) roles.add('ASSIGNEE');
  if (ticket.raiserId === repo.actor.employeeId) roles.add('RAISER');
  if (me.role === 'ADMIN') roles.add('ADMIN');

  const assignee = await repo.employees.findById(ticket.assigneeId);
  if (assignee !== null && assignee.managerId === repo.actor.employeeId) roles.add('MANAGER');

  return roles;
}

async function requireVisible(repo: Repository, ticketId: Uuid): Promise<Ticket> {
  const t = await repo.tickets.findById(ticketId);
  if (t === null) throw new AuthorizationError(`not visible or not permitted: ${ticketId}`);
  return t;
}

function today(): IsoDate {
  return istDateOf(new Date());
}

// -----------------------------------------------------------------------------

export interface CreateTicketInput {
  readonly title: string;
  readonly description?: string;
  readonly categoryId?: Uuid | null;
  readonly priority: Priority;
  readonly assigneeId: Uuid;
  readonly deadline: IsoDate;
}

export async function createTicket(repo: Repository, input: CreateTicketInput): Promise<Ticket> {
  if (input.title.trim().length === 0) throw new ValidationError('a title is required');

  const ticket = await repo.tickets.create({
    title: input.title.trim(),
    description: input.description?.trim() ?? '',
    categoryId: input.categoryId ?? null,
    priority: input.priority,
    assigneeId: input.assigneeId,
    // Always the acting employee. The repository enforces this too, via RLS.
    raiserId: repo.actor.employeeId,
    deadline: input.deadline,
  });

  await repo.audit.append({
    action: 'TICKET_CREATED',
    entity: 'tickets',
    entityId: ticket.id,
    payload: {
      ref: ticket.ref,
      assigneeId: ticket.assigneeId,
      priority: ticket.priority,
      deadline: ticket.deadline,
    },
  });

  return ticket;
}

// -----------------------------------------------------------------------------

export interface PunchInput {
  readonly ticketId: Uuid;
  /** Omit to record progress without changing status. */
  readonly status?: TicketStatus;
  readonly note?: string;
  readonly blockedReason?: string;
  readonly minutesSpent?: number | null;
  readonly nextAction?: string;
  readonly nextActionBy?: IsoDate | null;
  readonly correctsUpdateId?: Uuid | null;
}

/**
 * Record progress, optionally changing status.
 *
 * A status change and its punch are one operation on purpose. Two separate calls
 * would allow a status to move with no record of why, which is the exact failure
 * this system exists to prevent.
 */
export async function punch(repo: Repository, input: PunchInput): Promise<Punch> {
  const ticket = await requireVisible(repo, input.ticketId);
  const nextStatus = input.status ?? ticket.status;
  const changing = nextStatus !== ticket.status;

  if (changing) {
    const roles = await actorRoles(repo, ticket);
    const check = checkTransition(ticket.status, nextStatus, roles);
    if (!check.ok) throw new ValidationError(check.reason);
    if (check.requiresReason && (input.note ?? '').trim().length === 0) {
      throw new ValidationError(`moving ${ticket.status} → ${nextStatus} requires a note`);
    }
  }

  if (nextStatus === 'BLOCKED' && (input.blockedReason ?? '').trim().length === 0) {
    throw new ValidationError('blocked_reason is required when reporting BLOCKED');
  }

  const punchDate = today();

  const created = await repo.tickets.addPunch({
    ticketId: ticket.id,
    actorId: repo.actor.employeeId,
    punchDate,
    status: nextStatus,
    note: input.note?.trim() ?? '',
    blockedReason: input.blockedReason?.trim() ?? null,
    minutesSpent: input.minutesSpent ?? null,
    nextAction: input.nextAction?.trim() ?? null,
    nextActionBy: input.nextActionBy ?? null,
    correctsUpdateId: input.correctsUpdateId ?? null,
  });

  if (changing) {
    const terminal = nextStatus === 'DONE' || nextStatus === 'CANCELLED';
    await repo.tickets.setStatus({
      ticketId: ticket.id,
      status: nextStatus,
      closedDate: terminal ? punchDate : null,
      ...(nextStatus === 'CANCELLED' ? { cancelReason: input.note?.trim() ?? 'cancelled' } : {}),
    });
  }

  await repo.audit.append({
    action: changing ? 'TICKET_STATUS_CHANGED' : 'PUNCH_CREATED',
    entity: 'status_updates',
    entityId: created.id,
    payload: {
      ticketId: ticket.id,
      ref: ticket.ref,
      from: ticket.status,
      to: nextStatus,
      punchSeq: created.seq,
      ...(input.correctsUpdateId ? { corrects: input.correctsUpdateId } : {}),
    },
  });

  return created;
}

// -----------------------------------------------------------------------------

export interface ReassignInput {
  readonly ticketId: Uuid;
  readonly newAssigneeId: Uuid;
  /** Mandatory. Work handed over with no context is work dropped. */
  readonly handoverNote: string;
}

export async function reassign(repo: Repository, input: ReassignInput): Promise<Ticket> {
  const ticket = await requireVisible(repo, input.ticketId);
  if (input.handoverNote.trim().length === 0) {
    throw new ValidationError('a handover note is required to reassign');
  }
  if (input.newAssigneeId === ticket.assigneeId) {
    throw new ValidationError('that person is already the assignee');
  }
  if (ticket.status === 'DONE' || ticket.status === 'CANCELLED') {
    throw new ValidationError(`cannot reassign a ${ticket.status} ticket`);
  }

  // The handover note is a punch, so it appears in the ticket's history where the
  // next person will actually read it — not buried in an audit log only an admin
  // can see.
  await repo.tickets.addPunch({
    ticketId: ticket.id,
    actorId: repo.actor.employeeId,
    punchDate: today(),
    status: ticket.status,
    note: `Handover: ${input.handoverNote.trim()}`,
  });

  const updated = await repo.tickets.setAssignee(ticket.id, input.newAssigneeId);

  await repo.audit.append({
    action: 'TICKET_REASSIGNED',
    entity: 'tickets',
    entityId: ticket.id,
    payload: { ref: ticket.ref, from: ticket.assigneeId, to: input.newAssigneeId },
  });

  return updated;
}

// -----------------------------------------------------------------------------

export interface DeadlineChangeRequestInput {
  readonly ticketId: Uuid;
  readonly toDate: IsoDate;
  readonly reason: string;
}

/**
 * Ask to move a deadline.
 *
 * REQUIREMENTS §5: a punch must come first. The rule enforced here is the simple,
 * unambiguous version — **the ticket must already have at least one punch**. A
 * stricter reading ("a punch since the last deadline move") would need a total
 * ordering between punches and deadline changes that the schema does not provide,
 * so it would be guesswork dressed as a rule. This version captures the intent
 * for the case that matters: you cannot open a ticket and immediately push its
 * date without saying anything.
 */
export async function requestDeadlineChange(
  repo: Repository,
  input: DeadlineChangeRequestInput,
): Promise<DeadlineChange> {
  const ticket = await requireVisible(repo, input.ticketId);
  if (input.reason.trim().length === 0) {
    throw new ValidationError('a reason is required to move a deadline');
  }
  if (input.toDate === ticket.deadline) {
    throw new ValidationError('the new deadline is the same as the current one');
  }
  if (ticket.status === 'DONE' || ticket.status === 'CANCELLED') {
    throw new ValidationError(`cannot move the deadline of a ${ticket.status} ticket`);
  }

  const history = await repo.tickets.listPunches(ticket.id);
  if (history.length === 0) {
    throw new ValidationError(
      'record a status update before moving the deadline: say where things stand first',
    );
  }

  const change = await repo.tickets.requestDeadlineChange({
    ticketId: ticket.id,
    toDate: input.toDate,
    reason: input.reason.trim(),
  });

  await repo.audit.append({
    action: 'DEADLINE_CHANGE_REQUESTED',
    entity: 'deadline_changes',
    entityId: change.id,
    payload: {
      ref: ticket.ref,
      from: change.fromDate,
      to: change.toDate,
      reason: change.reason,
      originalDeadline: ticket.originalDeadline,
    },
  });

  return change;
}

/**
 * Approve or reject. Approval also applies the new date.
 *
 * `original_deadline` is untouched — the database has a trigger that refuses to
 * change it. Both dates are then reportable, which is the only honest way to
 * measure delivery against what was actually promised.
 */
export async function decideDeadlineChange(
  repo: Repository,
  changeId: Uuid,
  decision: 'APPROVED' | 'REJECTED',
): Promise<DeadlineChange> {
  const decided = await repo.tickets.decideDeadlineChange(changeId, decision);

  if (decision === 'APPROVED') {
    await repo.tickets.setDeadline(decided.ticketId, decided.toDate);
  }

  await repo.audit.append({
    action: 'DEADLINE_CHANGE_DECIDED',
    entity: 'deadline_changes',
    entityId: decided.id,
    payload: {
      ticketId: decided.ticketId,
      decision,
      from: decided.fromDate,
      to: decided.toDate,
    },
  });

  return decided;
}
