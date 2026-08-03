'use server';

/**
 * Administrative server actions — the only write path into the admin console.
 *
 * Same shape as app/tickets/actions.ts, deliberately: authenticate, run inside a
 * transaction with RLS in force, delegate every rule to `src/service/admin.ts`,
 * record an access event. None of them takes an actor id — identity comes from
 * the verified request, never from the payload — and none of them takes a role,
 * because the service reads that from the store.
 *
 * Expected failures come back as a result object so the form can show why. A
 * thrown 500 for "that email is already on the list" teaches an admin nothing.
 */

import { revalidatePath } from 'next/cache';
import { headers } from 'next/headers';
import { withUser } from '@/server/session';
import { AccessDeniedError } from '@/auth/access';
import { AuthorizationError, ValidationError } from '@/repo/types';
import type { Role } from '@/domain/tickets';
import {
  addCategory,
  addEmployee,
  addHoliday,
  deactivateEmployee,
  recordAccessReview,
  removeHoliday,
  setCategoryActive,
  setEmployeeManager,
  setEmployeeRole,
} from '@/service/admin';

export type ActionResult = { readonly ok: true } | { readonly ok: false; readonly error: string };

const ROLES: readonly string[] = ['EMPLOYEE', 'MANAGER', 'ADMIN'];

function text(form: FormData, key: string): string {
  const v = form.get(key);
  return typeof v === 'string' ? v.trim() : '';
}

/** An empty select means "nobody", which is a real value for a manager. */
function optionalId(form: FormData, key: string): string | null {
  const v = text(form, key);
  return v.length > 0 ? v : null;
}

function isoDate(form: FormData, key: string): string {
  const v = text(form, key);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) {
    throw new ValidationError(`${key} must be a date (YYYY-MM-DD)`);
  }
  return v;
}

function role(form: FormData, key: string): Role {
  const v = text(form, key);
  if (!ROLES.includes(v)) throw new ValidationError('choose a role');
  return v as Role;
}

/**
 * Turn expected failures into a message and let everything else through.
 *
 * `redirect()` works by throwing, so anything carrying a Next.js digest must be
 * re-thrown. Swallowing it would make a successful submission look like a silent
 * failure — a genuinely nasty bug to chase, and the reason this check exists in
 * app/tickets/actions.ts too. No action here redirects today, but the guard stays
 * so that adding one later cannot reintroduce it.
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

/**
 * Both admin pages read the same rows, so any write invalidates both.
 *
 * Note also what every action below does alongside its audit entry: it records an
 * ADMIN_ACTION access event. The two answer different questions — "what changed"
 * versus "who touched the console, from where, and when" — and CSCRF PR.AA asks
 * for the second with two-year retention (DESIGN §8).
 */
function refresh(): void {
  revalidatePath('/admin');
  revalidatePath('/admin/access-review');
}

// -----------------------------------------------------------------------------
// People
// -----------------------------------------------------------------------------

export async function addEmployeeAction(
  _prev: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const result = await run(async () => {
    const wanted = role(form, 'role');
    const ctx = await requestContext();
    await withUser(async (repo) => {
      const created = await addEmployee(repo, {
        workEmail: text(form, 'workEmail'),
        displayName: text(form, 'displayName'),
        role: wanted,
        managerId: optionalId(form, 'managerId'),
      });
      await repo.accessLog.record({
        event: 'ADMIN_ACTION',
        entity: 'employees',
        entityId: created.id,
        ...ctx,
      });
    });
  });
  if (result.ok) refresh();
  return result;
}

export async function setRoleAction(
  _prev: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const result = await run(async () => {
    const wanted = role(form, 'role');
    const employeeId = text(form, 'employeeId');
    const ctx = await requestContext();
    await withUser(async (repo) => {
      await setEmployeeRole(repo, employeeId, wanted);
      await repo.accessLog.record({
        event: 'ADMIN_ACTION',
        entity: 'employees',
        entityId: employeeId,
        ...ctx,
      });
    });
  });
  if (result.ok) refresh();
  return result;
}

export async function setManagerAction(
  _prev: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const result = await run(async () => {
    const employeeId = text(form, 'employeeId');
    const managerId = optionalId(form, 'managerId');
    const ctx = await requestContext();
    await withUser(async (repo) => {
      await setEmployeeManager(repo, employeeId, managerId);
      await repo.accessLog.record({
        event: 'ADMIN_ACTION',
        entity: 'employees',
        entityId: employeeId,
        ...ctx,
      });
    });
  });
  if (result.ok) refresh();
  return result;
}

export async function deactivateEmployeeAction(
  _prev: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const result = await run(async () => {
    const employeeId = text(form, 'employeeId');
    const ctx = await requestContext();
    await withUser(async (repo) => {
      await deactivateEmployee(repo, employeeId, text(form, 'reason'));
      await repo.accessLog.record({
        event: 'ADMIN_ACTION',
        entity: 'employees',
        entityId: employeeId,
        ...ctx,
      });
    });
  });
  if (result.ok) refresh();
  return result;
}

// -----------------------------------------------------------------------------
// Holiday calendar
// -----------------------------------------------------------------------------

export async function addHolidayAction(
  _prev: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const result = await run(async () => {
    const date = isoDate(form, 'date');
    const ctx = await requestContext();
    await withUser(async (repo) => {
      await addHoliday(repo, date, text(form, 'name'));
      await repo.accessLog.record({
        event: 'ADMIN_ACTION',
        entity: 'holidays',
        entityId: date,
        ...ctx,
      });
    });
  });
  if (result.ok) refresh();
  return result;
}

export async function removeHolidayAction(
  _prev: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const result = await run(async () => {
    const date = isoDate(form, 'date');
    const ctx = await requestContext();
    await withUser(async (repo) => {
      await removeHoliday(repo, date);
      await repo.accessLog.record({
        event: 'ADMIN_ACTION',
        entity: 'holidays',
        entityId: date,
        ...ctx,
      });
    });
  });
  if (result.ok) refresh();
  return result;
}

// -----------------------------------------------------------------------------
// Categories
// -----------------------------------------------------------------------------

export async function addCategoryAction(
  _prev: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const result = await run(async () => {
    const ctx = await requestContext();
    await withUser(async (repo) => {
      const created = await addCategory(repo, text(form, 'name'));
      await repo.accessLog.record({
        event: 'ADMIN_ACTION',
        entity: 'categories',
        entityId: created.id,
        ...ctx,
      });
    });
  });
  if (result.ok) refresh();
  return result;
}

export async function setCategoryActiveAction(
  _prev: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const result = await run(async () => {
    const categoryId = text(form, 'categoryId');
    const active = text(form, 'active');
    if (active !== 'true' && active !== 'false') {
      throw new ValidationError('active must be true or false');
    }
    const ctx = await requestContext();
    await withUser(async (repo) => {
      await setCategoryActive(repo, categoryId, active === 'true');
      await repo.accessLog.record({
        event: 'ADMIN_ACTION',
        entity: 'categories',
        entityId: categoryId,
        ...ctx,
      });
    });
  });
  if (result.ok) refresh();
  return result;
}

// -----------------------------------------------------------------------------
// The access review
// -----------------------------------------------------------------------------

/**
 * Sign off the half-yearly access-rights and privileged-user review.
 *
 * The note is the only thing taken from the form. The figures in the audit entry
 * are recomputed inside the service, so the record cannot claim a clean review of
 * numbers nobody looked at.
 */
export async function recordAccessReviewAction(
  _prev: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const result = await run(async () => {
    const note = text(form, 'note');
    const ctx = await requestContext();
    await withUser(async (repo) => {
      const entry = await recordAccessReview(repo, note);
      await repo.accessLog.record({
        event: 'ADMIN_ACTION',
        entity: 'audit_log',
        entityId: String(entry.seq),
        ...ctx,
      });
    });
  });
  if (result.ok) {
    revalidatePath('/admin/access-review');
    revalidatePath('/admin/audit');
  }
  return result;
}
