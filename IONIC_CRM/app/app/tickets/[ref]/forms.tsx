'use client';

import { useActionState, useState } from 'react';
import {
  decideDeadlineChangeAction,
  punchAction,
  reassignAction,
  requestDeadlineChangeAction,
  type ActionResult,
} from '../actions';
import { Button, ErrorText, Field, Select, TextArea, TextInput } from '../../_components/ui';

export interface Colleague {
  readonly id: string;
  readonly displayName: string;
}

/**
 * The punch form — the single most-used thing in the application.
 *
 * Kept short on purpose: only status and a note are prominent, because a form
 * that asks for eight fields gets filled in once and then avoided, and a tool
 * nobody punches into is worse than no tool. Time spent and next action are
 * optional and visually secondary.
 */
export function PunchForm({
  ticketId,
  currentStatus,
  allowedStatuses,
}: {
  ticketId: string;
  currentStatus: string;
  /** Only legal transitions from the current status, computed server-side. */
  allowedStatuses: readonly { value: string; label: string }[];
}) {
  const [state, formAction, pending] = useActionState<ActionResult | null, FormData>(
    punchAction,
    null,
  );
  const [status, setStatus] = useState('');

  const blocking = status === 'BLOCKED' || (status === '' && currentStatus === 'BLOCKED');

  return (
    <form action={formAction} className="space-y-4">
      <input type="hidden" name="ticketId" value={ticketId} />

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Status" htmlFor="status" hint="Leave as-is to log progress without moving it.">
          <Select
            id="status"
            name="status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">No change</option>
            {allowedStatuses.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Time spent" htmlFor="minutesSpent" hint="Minutes. Optional.">
          <TextInput id="minutesSpent" name="minutesSpent" type="number" min={0} max={1440} />
        </Field>
      </div>

      <Field label="Where things stand" htmlFor="note">
        <TextArea
          id="note"
          name="note"
          maxLength={4000}
          placeholder="What moved, what is next, anything the next person needs to know."
        />
      </Field>

      {blocking && (
        <Field
          label="What is blocking this"
          htmlFor="blockedReason"
          required
          hint="Required. A blocker with no reason is the least useful entry in the system."
        >
          <TextInput id="blockedReason" name="blockedReason" required maxLength={500} />
        </Field>
      )}

      <Field label="Next action" htmlFor="nextAction">
        <TextInput id="nextAction" name="nextAction" maxLength={500} />
      </Field>

      {state && !state.ok && <ErrorText>{state.error}</ErrorText>}
      {state && state.ok && (
        <p className="text-sm text-[var(--accent)]" role="status">
          Recorded.
        </p>
      )}

      <Button type="submit" disabled={pending}>
        {pending ? 'Recording…' : 'Record update'}
      </Button>
    </form>
  );
}

export function ReassignForm({
  ticketId,
  colleagues,
  currentAssigneeId,
}: {
  ticketId: string;
  colleagues: readonly Colleague[];
  currentAssigneeId: string;
}) {
  const [state, formAction, pending] = useActionState<ActionResult | null, FormData>(
    reassignAction,
    null,
  );

  return (
    <form action={formAction} className="space-y-4">
      <input type="hidden" name="ticketId" value={ticketId} />
      <Field label="New assignee" htmlFor="newAssigneeId" required>
        <Select id="newAssigneeId" name="newAssigneeId" required>
          {colleagues
            .filter((c) => c.id !== currentAssigneeId)
            .map((c) => (
              <option key={c.id} value={c.id}>
                {c.displayName}
              </option>
            ))}
        </Select>
      </Field>
      <Field
        label="Handover note"
        htmlFor="handoverNote"
        required
        hint="Required, and it goes into the ticket history where the next person will read it."
      >
        <TextArea id="handoverNote" name="handoverNote" required maxLength={2000} />
      </Field>
      {state && !state.ok && <ErrorText>{state.error}</ErrorText>}
      <Button type="submit" variant="secondary" disabled={pending}>
        {pending ? 'Reassigning…' : 'Reassign'}
      </Button>
    </form>
  );
}

export function DeadlineChangeForm({
  ticketId,
  currentDeadline,
}: {
  ticketId: string;
  currentDeadline: string;
}) {
  const [state, formAction, pending] = useActionState<ActionResult | null, FormData>(
    requestDeadlineChangeAction,
    null,
  );

  return (
    <form action={formAction} className="space-y-4">
      <input type="hidden" name="ticketId" value={ticketId} />
      <Field
        label="New deadline"
        htmlFor="toDate"
        required
        hint={`Currently ${currentDeadline}. The original deadline is kept permanently and both are reported.`}
      >
        <TextInput id="toDate" name="toDate" type="date" required />
      </Field>
      <Field label="Why" htmlFor="reason" required>
        <TextArea id="reason" name="reason" required maxLength={2000} />
      </Field>
      {state && !state.ok && <ErrorText>{state.error}</ErrorText>}
      <Button type="submit" variant="secondary" disabled={pending}>
        {pending ? 'Requesting…' : 'Request change'}
      </Button>
    </form>
  );
}

export function DecideDeadlineChange({ changeId }: { changeId: string }) {
  const [state, formAction, pending] = useActionState<ActionResult | null, FormData>(
    decideDeadlineChangeAction,
    null,
  );
  return (
    <form action={formAction} className="flex flex-wrap items-center gap-2">
      <input type="hidden" name="changeId" value={changeId} />
      <Button type="submit" name="decision" value="APPROVED" disabled={pending}>
        Approve
      </Button>
      <Button type="submit" name="decision" value="REJECTED" variant="secondary" disabled={pending}>
        Reject
      </Button>
      {state && !state.ok && <ErrorText>{state.error}</ErrorText>}
    </form>
  );
}
