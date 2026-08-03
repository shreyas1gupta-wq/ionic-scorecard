'use server';

/**
 * Server actions — the only write path from the browser.
 *
 * Each one authenticates, runs inside a transaction with RLS in force, delegates
 * the rules to `src/service/tickets.ts`, and records an access event. None of them
 * trust anything in the FormData beyond the values they explicitly read, and none
 * accept an actor id: identity comes from the verified request, never the payload.
 *
 * They return a result object rather than throwing for expected failures, so the
 * form can show the reason. Genuine faults still throw and surface as an error.
 */

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { headers } from 'next/headers';
import { withUser } from '@/server/session';
import { AccessDeniedError } from '@/auth/access';
import { AuthorizationError, ValidationError } from '@/repo/types';
import type { Priority, TicketStatus } from '@/domain/tickets';
import {
  createTicket,
  decideDeadlineChange,
  punch,
  reassign,
  requestDeadlineChange,
} from '@/service/tickets';

export type ActionResult = { readonly ok: true } | { readonly ok: false; readonly error: string };

const PRIORITIES: readonly string[] = ['P1', 'P2', 'P3'];
const STATUSES: readonly string[] = ['OPEN', 'IN_PROGRESS', 'BLOCKED', 'DONE', 'CANCELLED'];

function text(form: FormData, key: string): string {
  const v = form.get(key);
  return typeof v === 'string' ? v.trim() : '';
}

function optionalText(form: FormData, key: string): string | undefined {
  const v = text(form, key);
  return v.length > 0 ? v : undefined;
}

function isoDate(form: FormData, key: string): string {
  const v = text(form, key);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) {
    throw new ValidationError(`${key} must be a date (YYYY-MM-DD)`);
  }
  return v;
}

/**
 * Turn expected failures into a message and let everything else through.
 *
 * `redirect()` works by throwing, so it must not be swallowed — hence the digest
 * check. Getting this wrong makes successful submissions look like silent
 * failures, which is a genuinely confusing bug to chase.
 */
async function run(fn: () => Promise<void>): Promise<ActionResult> {
  try {
    await fn();
    return { ok: true };
  } catch (err) {
    if (typeof (err as { digest?: unknown }).digest === 'string') throw err;
    if (err instanceof ValidationError) return { ok: false, error: err.message };
    if (err instanceof AuthorizationError) {
      return { ok: false, error: 'You do not have permission to do that.' };
    }
    if (err instanceof AccessDeniedError) return { ok: false, error: 'Not available.' };
    throw err;
  }
}

/** Client hints for the access log. Best-effort; never trusted for authorisation. */
async function requestContext(): Promise<{ ip: string | null; userAgent: string | null }> {
  const h = await headers();
  const forwarded = h.get('cf-connecting-ip') ?? h.get('x-forwarded-for');
  const ip = forwarded ? (forwarded.split(',')[0]?.trim() ?? null) : null;
  return { ip: ip && ip.length > 0 ? ip : null, userAgent: h.get('user-agent') };
}

// -----------------------------------------------------------------------------

export async function createTicketAction(
  _prev: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  let createdRef: string | null = null;

  const result = await run(async () => {
    const priority = text(form, 'priority');
    if (!PRIORITIES.includes(priority)) throw new ValidationError('choose a priority');

    const ctx = await requestContext();

    await withUser(async (repo) => {
      const ticket = await createTicket(repo, {
        title: text(form, 'title'),
        description: optionalText(form, 'description') ?? '',
        categoryId: optionalText(form, 'categoryId') ?? null,
        priority: priority as Priority,
        assigneeId: text(form, 'assigneeId'),
        deadline: isoDate(form, 'deadline'),
      });
      createdRef = ticket.ref;
      await repo.accessLog.record({
        event: 'ADMIN_ACTION',
        entity: 'tickets',
        entityId: ticket.id,
        ...ctx,
      });
    });
  });

  if (!result.ok) return result;
  revalidatePath('/tickets');
  // Outside `run`, so the redirect throw is never mistaken for a failure.
  redirect(`/tickets/${createdRef}`);
}

export async function punchAction(
  _prev: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const result = await run(async () => {
    const ticketId = text(form, 'ticketId');
    const rawStatus = text(form, 'status');
    // An empty status means "record progress, do not move the ticket".
    const status = rawStatus.length > 0 ? rawStatus : undefined;
    if (status !== undefined && !STATUSES.includes(status)) {
      throw new ValidationError('unknown status');
    }
    const minutesRaw = text(form, 'minutesSpent');
    const minutes = minutesRaw.length > 0 ? Number(minutesRaw) : null;
    if (minutes !== null && !Number.isFinite(minutes)) {
      throw new ValidationError('time spent must be a number of minutes');
    }

    const ctx = await requestContext();

    await withUser(async (repo) => {
      await punch(repo, {
        ticketId,
        ...(status !== undefined ? { status: status as TicketStatus } : {}),
        ...(optionalText(form, 'note') !== undefined ? { note: text(form, 'note') } : {}),
        ...(optionalText(form, 'blockedReason') !== undefined
          ? { blockedReason: text(form, 'blockedReason') }
          : {}),
        minutesSpent: minutes,
        ...(optionalText(form, 'nextAction') !== undefined
          ? { nextAction: text(form, 'nextAction') }
          : {}),
      });
      await repo.accessLog.record({
        event: 'ADMIN_ACTION',
        entity: 'status_updates',
        entityId: ticketId,
        ...ctx,
      });
    });
  });

  if (result.ok) revalidatePath('/tickets');
  return result;
}

export async function reassignAction(
  _prev: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const result = await run(async () => {
    const ctx = await requestContext();
    await withUser(async (repo) => {
      await reassign(repo, {
        ticketId: text(form, 'ticketId'),
        newAssigneeId: text(form, 'newAssigneeId'),
        handoverNote: text(form, 'handoverNote'),
      });
      await repo.accessLog.record({
        event: 'ADMIN_ACTION',
        entity: 'tickets',
        entityId: text(form, 'ticketId'),
        ...ctx,
      });
    });
  });
  if (result.ok) revalidatePath('/tickets');
  return result;
}

export async function requestDeadlineChangeAction(
  _prev: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const result = await run(async () => {
    const ctx = await requestContext();
    await withUser(async (repo) => {
      const change = await requestDeadlineChange(repo, {
        ticketId: text(form, 'ticketId'),
        toDate: isoDate(form, 'toDate'),
        reason: text(form, 'reason'),
      });
      await repo.accessLog.record({
        event: 'ADMIN_ACTION',
        entity: 'deadline_changes',
        entityId: change.id,
        ...ctx,
      });
    });
  });
  if (result.ok) revalidatePath('/tickets');
  return result;
}

export async function decideDeadlineChangeAction(
  _prev: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const result = await run(async () => {
    const decision = text(form, 'decision');
    if (decision !== 'APPROVED' && decision !== 'REJECTED') {
      throw new ValidationError('decision must be APPROVED or REJECTED');
    }
    const ctx = await requestContext();
    await withUser(async (repo) => {
      const changeId = text(form, 'changeId');
      await decideDeadlineChange(repo, changeId, decision);
      await repo.accessLog.record({
        event: 'ADMIN_ACTION',
        entity: 'deadline_changes',
        entityId: changeId,
        ...ctx,
      });
    });
  });
  if (result.ok) revalidatePath('/tickets');
  return result;
}
