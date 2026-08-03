import Link from 'next/link';
import { notFound } from 'next/navigation';
import { AccessDeniedError } from '@/auth/access';
import { withUser } from '@/server/session';
import { istDateOf, workingDaysBetween } from '@/domain/calendar';
import { isOverdue, legalTransitions, type TicketStatus } from '@/domain/tickets';
import { actorRoles } from '@/service/tickets';
import type { Employee, Punch } from '@/repo/types';
import { Denied, Shell } from '../../_components/shell';
import { Card, PageHeading } from '../../_components/ui';
import { DeadlineChangeForm, DecideDeadlineChange, PunchForm, ReassignForm } from './forms';

export const dynamic = 'force-dynamic';

const STATUS_LABEL: Record<TicketStatus, string> = {
  OPEN: 'Open',
  IN_PROGRESS: 'In progress',
  BLOCKED: 'Blocked',
  DONE: 'Done',
  CANCELLED: 'Cancelled',
};

async function load(ref: string) {
  try {
    return await withUser(async (repo, user) => {
      const ticket = await repo.tickets.findByRef(ref);
      if (ticket === null) return { user, ticket: null } as const;

      const [punches, colleagues, holidays, changes, roles] = await Promise.all([
        repo.tickets.listPunches(ticket.id),
        repo.employees.listActive(),
        repo.calendar.holidays(),
        repo.tickets.listDeadlineChanges(ticket.id),
        actorRoles(repo, ticket),
      ]);

      // CSCRF PR.AA: who looked at what, retained two years. Recorded on the read
      // path, not only on writes.
      await repo.accessLog.record({ event: 'VIEW', entity: 'tickets', entityId: ticket.id });

      return { user, ticket, punches, colleagues, holidays, changes, roles } as const;
    });
  } catch (err) {
    if (err instanceof AccessDeniedError) return null;
    throw err;
  }
}

export default async function TicketPage({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params;
  const data = await load(decodeURIComponent(ref));
  if (data === null) return <Denied />;
  // A ticket that exists but is not yours is indistinguishable from one that does
  // not exist. Anything else is an existence oracle.
  if (data.ticket === null) notFound();

  const { user, ticket, punches, colleagues, holidays, changes, roles } = data;
  const today = istDateOf(new Date());
  const nameOf = new Map(colleagues.map((e: Employee) => [e.id, e.displayName]));
  const overdue = isOverdue(ticket, today);
  const terminal = ticket.status === 'DONE' || ticket.status === 'CANCELLED';

  const allowed = legalTransitions(ticket.status, roles).map((s) => ({
    value: s,
    label: STATUS_LABEL[s],
  }));
  const canDecide = roles.has('MANAGER') || roles.has('ADMIN');
  const pending = changes.filter((c) => c.decision === 'PENDING');

  return (
    <Shell user={user}>
      <PageHeading
        title={ticket.title}
        meta={
          <Link href="/tickets" className="hover:text-[var(--text)]">
            Back to open work
          </Link>
        }
      />

      <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-4">
        <Meta label="Reference">
          <span className="font-mono text-xs">{ticket.ref}</span>
        </Meta>
        <Meta label="Status">{STATUS_LABEL[ticket.status]}</Meta>
        <Meta label="Priority">{ticket.priority}</Meta>
        <Meta label="Assignee">{nameOf.get(ticket.assigneeId) ?? '—'}</Meta>
        <Meta label="Raised by">{nameOf.get(ticket.raiserId) ?? '—'}</Meta>
        <Meta label="Deadline">
          <span className={overdue ? 'font-medium text-[var(--danger)] tnum' : 'tnum'}>
            {ticket.deadline}
          </span>
          {overdue && <span className="ml-2 text-xs text-[var(--danger)]">overdue</span>}
          {!overdue && !terminal && (
            <span className="ml-2 text-xs text-[var(--muted)]">
              {workingDaysBetween(today, ticket.deadline, holidays)} working days
            </span>
          )}
        </Meta>
        <Meta label="Originally promised">
          <span className="tnum">{ticket.originalDeadline}</span>
          {ticket.deadline !== ticket.originalDeadline && (
            <span className="ml-2 text-xs text-[var(--warn)]">moved</span>
          )}
        </Meta>
        {ticket.closedDate && (
          <Meta label="Closed">
            <span className="tnum">{ticket.closedDate}</span>
          </Meta>
        )}
      </dl>

      {ticket.description && (
        <Card className="mt-5">
          <p className="whitespace-pre-wrap text-sm">{ticket.description}</p>
        </Card>
      )}

      {pending.length > 0 && (
        <Card className="mt-6 border-[var(--warn)]">
          <h2 className="text-sm font-medium">Deadline change requested</h2>
          {pending.map((c) => (
            <div key={c.id} className="mt-3 space-y-3 text-sm">
              <p className="tnum">
                {c.fromDate} → {c.toDate}
                <span className="ml-2 text-[var(--muted)]">
                  by {nameOf.get(c.requestedBy) ?? '—'}
                </span>
              </p>
              <p className="text-[var(--muted)]">{c.reason}</p>
              {canDecide ? (
                <DecideDeadlineChange changeId={c.id} />
              ) : (
                <p className="text-xs text-[var(--muted)]">
                  Waiting on a manager. The requester cannot approve their own request.
                </p>
              )}
            </div>
          ))}
        </Card>
      )}

      {!terminal && (
        <section className="mt-8">
          <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--muted)]">
            Record an update
          </h2>
          <Card className="mt-3">
            <PunchForm
              ticketId={ticket.id}
              currentStatus={ticket.status}
              allowedStatuses={allowed}
            />
          </Card>
        </section>
      )}

      <section className="mt-8">
        <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--muted)]">
          History
          <span className="ml-2 font-normal normal-case tracking-normal">
            {punches.length} {punches.length === 1 ? 'entry' : 'entries'} · nothing here can be
            edited or deleted
          </span>
        </h2>
        {punches.length === 0 ? (
          <p className="mt-3 rounded-md border border-dashed border-[var(--border)] px-4 py-6 text-sm text-[var(--muted)]">
            No updates yet. The deadline cannot be moved until someone records where things stand.
          </p>
        ) : (
          <ol className="mt-3 space-y-3">
            {[...punches].reverse().map((p: Punch) => (
              <li
                key={p.id}
                className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-4"
              >
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm">
                  <span className="font-medium">{nameOf.get(p.actorId) ?? '—'}</span>
                  <span className="text-[var(--muted)] tnum">{p.punchDate}</span>
                  <span className="rounded border border-[var(--border)] px-1.5 py-0.5 text-xs text-[var(--muted)]">
                    {STATUS_LABEL[p.status]}
                  </span>
                  {p.minutesSpent !== null && (
                    <span className="text-xs text-[var(--muted)] tnum">{p.minutesSpent} min</span>
                  )}
                  {p.correctsUpdateId && (
                    <span className="text-xs text-[var(--warn)]">correction</span>
                  )}
                </div>
                {p.note && <p className="mt-2 whitespace-pre-wrap text-sm">{p.note}</p>}
                {p.blockedReason && (
                  <p className="mt-2 text-sm text-[var(--danger)]">Blocked: {p.blockedReason}</p>
                )}
                {p.nextAction && (
                  <p className="mt-2 text-sm text-[var(--muted)]">Next: {p.nextAction}</p>
                )}
              </li>
            ))}
          </ol>
        )}
      </section>

      {!terminal && (
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <details className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-4">
            <summary className="cursor-pointer text-sm font-medium">Move the deadline</summary>
            <div className="mt-4">
              <DeadlineChangeForm ticketId={ticket.id} currentDeadline={ticket.deadline} />
            </div>
          </details>

          <details className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-4">
            <summary className="cursor-pointer text-sm font-medium">Hand this over</summary>
            <div className="mt-4">
              <ReassignForm
                ticketId={ticket.id}
                currentAssigneeId={ticket.assigneeId}
                colleagues={colleagues.map((c) => ({ id: c.id, displayName: c.displayName }))}
              />
            </div>
          </details>
        </div>
      )}
    </Shell>
  );
}

function Meta({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</dt>
      <dd className="mt-0.5">{children}</dd>
    </div>
  );
}
