'use client';

import { useActionState } from 'react';
import { createTicketAction, type ActionResult } from '../actions';
import { Button, ErrorText, Field, Select, TextArea, TextInput } from '../../_components/ui';

export interface Colleague {
  readonly id: string;
  readonly displayName: string;
}

export interface CategoryOption {
  readonly id: string;
  readonly name: string;
}

export function NewTicketForm({
  colleagues,
  categories,
  defaultAssigneeId,
  minDeadline,
}: {
  colleagues: readonly Colleague[];
  categories: readonly CategoryOption[];
  defaultAssigneeId: string;
  /** Today, in IST. Stops someone raising work that was already late. */
  minDeadline: string;
}) {
  const [state, formAction, pending] = useActionState<ActionResult | null, FormData>(
    createTicketAction,
    null,
  );

  return (
    <form action={formAction} className="mt-6 max-w-xl space-y-5">
      <Field label="Title" htmlFor="title" required hint="What needs doing, in one line.">
        <TextInput
          id="title"
          name="title"
          required
          maxLength={200}
          autoComplete="off"
          placeholder="Prepare the August client reporting pack"
        />
      </Field>

      <Field
        label="Detail"
        htmlFor="description"
        hint="No client names, no investment reasoning, no client complaints. This tool holds general task data only."
      >
        <TextArea id="description" name="description" maxLength={4000} />
      </Field>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Assignee" htmlFor="assigneeId" required>
          <Select id="assigneeId" name="assigneeId" required defaultValue={defaultAssigneeId}>
            {colleagues.map((c) => (
              <option key={c.id} value={c.id}>
                {c.displayName}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Priority" htmlFor="priority" required hint="P1 needs a daily update.">
          <Select id="priority" name="priority" required defaultValue="P2">
            <option value="P1">P1 — update daily</option>
            <option value="P2">P2 — update every 3 working days</option>
            <option value="P3">P3 — update every 5 working days</option>
          </Select>
        </Field>
      </div>

      {categories.length > 0 && (
        <Field label="Category" htmlFor="categoryId" hint="Optional.">
          <Select id="categoryId" name="categoryId" defaultValue="">
            <option value="">Uncategorised</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
        </Field>
      )}

      <Field
        label="Deadline"
        htmlFor="deadline"
        required
        hint="End of this day, IST. This is recorded permanently as the original deadline, even if it is moved later."
      >
        <TextInput id="deadline" name="deadline" type="date" required min={minDeadline} />
      </Field>

      {state && !state.ok && <ErrorText>{state.error}</ErrorText>}

      <div className="flex gap-3 pt-1">
        <Button type="submit" disabled={pending}>
          {pending ? 'Raising…' : 'Raise ticket'}
        </Button>
        <Button type="reset" variant="secondary" disabled={pending}>
          Clear
        </Button>
      </div>
    </form>
  );
}
