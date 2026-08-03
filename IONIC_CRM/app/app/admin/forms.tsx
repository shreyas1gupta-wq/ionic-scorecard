'use client';

import { useActionState } from 'react';
import {
  addCategoryAction,
  addEmployeeAction,
  addHolidayAction,
  deactivateEmployeeAction,
  recordAccessReviewAction,
  removeHolidayAction,
  setCategoryActiveAction,
  setManagerAction,
  setRoleAction,
  type ActionResult,
} from './actions';
import { Button, ErrorText, Field, Select, TextArea, TextInput } from '../_components/ui';

export interface Person {
  readonly id: string;
  readonly displayName: string;
}

const ROLES = [
  { value: 'EMPLOYEE', label: 'Employee' },
  { value: 'MANAGER', label: 'Manager' },
  { value: 'ADMIN', label: 'Administrator' },
] as const;

/** Shared feedback line, so every form on the page reports the same way. */
function Feedback({ state, done }: { state: ActionResult | null; done: string }) {
  if (state === null) return null;
  if (!state.ok) return <ErrorText>{state.error}</ErrorText>;
  return (
    <p className="text-sm text-[var(--accent)]" role="status">
      {done}
    </p>
  );
}

/**
 * Add a colleague.
 *
 * This form IS account creation: there is no password to issue, so once the
 * address is here Cloudflare Access will mail them a one-time PIN on first visit.
 * The hint says so, because an admin who expects to send credentials will
 * otherwise go looking for a field that does not exist.
 */
export function AddPersonForm({ people }: { people: readonly Person[] }) {
  const [state, formAction, pending] = useActionState<ActionResult | null, FormData>(
    addEmployeeAction,
    null,
  );

  return (
    <form action={formAction} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          label="Work email"
          htmlFor="workEmail"
          required
          hint="Their @ionic.in address. This is the allow-list: no password is issued."
        >
          <TextInput id="workEmail" name="workEmail" type="email" required maxLength={320} />
        </Field>
        <Field label="Name" htmlFor="displayName" required>
          <TextInput id="displayName" name="displayName" required maxLength={200} />
        </Field>
        <Field label="Role" htmlFor="role" required>
          <Select id="role" name="role" defaultValue="EMPLOYEE" required>
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Reports to" htmlFor="managerId" hint="Optional.">
          <Select id="managerId" name="managerId" defaultValue="">
            <option value="">Nobody</option>
            {people.map((p) => (
              <option key={p.id} value={p.id}>
                {p.displayName}
              </option>
            ))}
          </Select>
        </Field>
      </div>
      <Feedback state={state} done="Added. They can sign in now." />
      <Button type="submit" disabled={pending}>
        {pending ? 'Adding…' : 'Add to the allow-list'}
      </Button>
    </form>
  );
}

/**
 * Role and manager, as two one-field forms per person.
 *
 * Both need an explicit button rather than submitting on change: a mis-click in a
 * dropdown should not be a privilege change.
 */
export function RoleForm({
  employeeId,
  current,
  isSelf,
}: {
  employeeId: string;
  current: string;
  isSelf: boolean;
}) {
  const [state, formAction, pending] = useActionState<ActionResult | null, FormData>(
    setRoleAction,
    null,
  );

  if (isSelf) {
    // Not merely hidden: the database refuses it too (0005_admin_guards.sql).
    // Rendering the reason is friendlier than rendering a control that always
    // fails, and it tells the next admin that the rule is intentional.
    return (
      <span className="text-xs text-[var(--muted)]" title="Ask another administrator.">
        {current} · your own
      </span>
    );
  }

  return (
    <form action={formAction} className="flex flex-wrap items-center gap-2">
      <input type="hidden" name="employeeId" value={employeeId} />
      <Select
        name="role"
        defaultValue={current}
        aria-label="Role"
        className="w-auto min-w-32 py-1 text-xs"
      >
        {ROLES.map((r) => (
          <option key={r.value} value={r.value}>
            {r.label}
          </option>
        ))}
      </Select>
      <Button type="submit" variant="secondary" className="px-2 py-1 text-xs" disabled={pending}>
        Set
      </Button>
      {state && !state.ok && <ErrorText>{state.error}</ErrorText>}
    </form>
  );
}

export function ManagerForm({
  employeeId,
  current,
  people,
}: {
  employeeId: string;
  current: string | null;
  people: readonly Person[];
}) {
  const [state, formAction, pending] = useActionState<ActionResult | null, FormData>(
    setManagerAction,
    null,
  );

  return (
    <form action={formAction} className="flex flex-wrap items-center gap-2">
      <input type="hidden" name="employeeId" value={employeeId} />
      <Select
        name="managerId"
        defaultValue={current ?? ''}
        aria-label="Reports to"
        className="w-auto min-w-32 py-1 text-xs"
      >
        <option value="">Nobody</option>
        {people
          // Self-management is refused by the database; offering it would be
          // offering a control that cannot work.
          .filter((p) => p.id !== employeeId)
          .map((p) => (
            <option key={p.id} value={p.id}>
              {p.displayName}
            </option>
          ))}
      </Select>
      <Button type="submit" variant="secondary" className="px-2 py-1 text-xs" disabled={pending}>
        Set
      </Button>
      {state && !state.ok && <ErrorText>{state.error}</ErrorText>}
    </form>
  );
}

/**
 * Offboarding, behind a disclosure with a mandatory reason.
 *
 * Deliberately not a one-click button in a table row. It is the most consequential
 * action in the console, it cannot be undone through this UI, and it needs a
 * sentence typed before it will go through.
 */
export function DeactivateForm({ employeeId, name }: { employeeId: string; name: string }) {
  const [state, formAction, pending] = useActionState<ActionResult | null, FormData>(
    deactivateEmployeeAction,
    null,
  );

  return (
    <details>
      <summary className="cursor-pointer text-xs text-[var(--danger)]">Deactivate</summary>
      <form action={formAction} className="mt-2 space-y-2">
        <input type="hidden" name="employeeId" value={employeeId} />
        <TextInput
          name="reason"
          required
          maxLength={500}
          placeholder={`Why is ${name} being offboarded?`}
          aria-label="Reason"
          className="py-1 text-xs"
        />
        <p className="text-xs text-[var(--muted)]">
          Their tickets and history stay, attributed to them. Open work must be reassigned first.
        </p>
        {state && !state.ok && <ErrorText>{state.error}</ErrorText>}
        <Button type="submit" variant="secondary" className="px-2 py-1 text-xs" disabled={pending}>
          {pending ? 'Deactivating…' : 'Confirm'}
        </Button>
      </form>
    </details>
  );
}

export function AddHolidayForm() {
  const [state, formAction, pending] = useActionState<ActionResult | null, FormData>(
    addHolidayAction,
    null,
  );

  return (
    <form action={formAction} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Date" htmlFor="holidayDate" required>
          <TextInput id="holidayDate" name="date" type="date" required />
        </Field>
        <Field label="Name" htmlFor="holidayName" required>
          <TextInput id="holidayName" name="name" required maxLength={200} placeholder="Diwali" />
        </Field>
      </div>
      <Feedback state={state} done="Added to the calendar." />
      <Button type="submit" disabled={pending}>
        {pending ? 'Adding…' : 'Add holiday'}
      </Button>
    </form>
  );
}

export function RemoveHolidayButton({ date }: { date: string }) {
  const [state, formAction, pending] = useActionState<ActionResult | null, FormData>(
    removeHolidayAction,
    null,
  );
  return (
    <form action={formAction} className="inline-flex items-center gap-2">
      <input type="hidden" name="date" value={date} />
      <Button type="submit" variant="secondary" className="px-2 py-0.5 text-xs" disabled={pending}>
        Remove
      </Button>
      {state && !state.ok && <ErrorText>{state.error}</ErrorText>}
    </form>
  );
}

export function AddCategoryForm() {
  const [state, formAction, pending] = useActionState<ActionResult | null, FormData>(
    addCategoryAction,
    null,
  );
  return (
    <form action={formAction} className="space-y-4">
      <Field label="Category" htmlFor="categoryName" required>
        <TextInput
          id="categoryName"
          name="name"
          required
          maxLength={100}
          placeholder="Client Reporting"
        />
      </Field>
      <Feedback state={state} done="Added." />
      <Button type="submit" disabled={pending}>
        {pending ? 'Adding…' : 'Add category'}
      </Button>
    </form>
  );
}

/**
 * Retire or restore a category.
 *
 * Never a delete: tickets reference categories, and removing one would either
 * orphan history or force a rewrite of it.
 */
export function CategoryActiveButton({ id, active }: { id: string; active: boolean }) {
  const [state, formAction, pending] = useActionState<ActionResult | null, FormData>(
    setCategoryActiveAction,
    null,
  );
  return (
    <form action={formAction} className="inline-flex items-center gap-2">
      <input type="hidden" name="categoryId" value={id} />
      <input type="hidden" name="active" value={active ? 'false' : 'true'} />
      <Button type="submit" variant="secondary" className="px-2 py-0.5 text-xs" disabled={pending}>
        {active ? 'Retire' : 'Restore'}
      </Button>
      {state && !state.ok && <ErrorText>{state.error}</ErrorText>}
    </form>
  );
}

/**
 * Sign off the review.
 *
 * DESIGN §8: the evidence that the review happened is worth more than the report
 * itself, so this button writes an entry into the hash chain — where it cannot be
 * back-dated or quietly removed — rather than setting a flag on a row.
 */
export function RecordReviewForm() {
  const [state, formAction, pending] = useActionState<ActionResult | null, FormData>(
    recordAccessReviewAction,
    null,
  );
  return (
    <form action={formAction} className="space-y-3">
      <Field
        label="Reviewer note"
        htmlFor="note"
        hint="Optional. What you checked, and anything you acted on."
      >
        <TextArea id="note" name="note" maxLength={2000} />
      </Field>
      <Feedback
        state={state}
        done="Recorded in the audit chain, with the accounts it covered."
      />
      <Button type="submit" disabled={pending}>
        {pending ? 'Recording…' : 'Record that this review was performed'}
      </Button>
    </form>
  );
}
