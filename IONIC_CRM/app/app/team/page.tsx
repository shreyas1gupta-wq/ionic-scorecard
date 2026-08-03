import Link from 'next/link';
import { AccessDeniedError } from '@/auth/access';
import { withUser } from '@/server/session';
import { istDateOf, workingDaysBetween, type IsoDate } from '@/domain/calendar';
import { isOverdue, isStale, STALE_THRESHOLD_WORKING_DAYS } from '@/domain/tickets';
import type { Employee, TicketSummary } from '@/repo/types';
import { Denied, Shell } from '../_components/shell';
import { Card, PageHeading } from '../_components/ui';

export const dynamic = 'force-dynamic';

/**
 * The board needs no role check of its own.
 *
 * `listSummaries` already returns only what row-level security permits, so
 * grouping those rows by assignee shows exactly the people the viewer can
 * already see: an employee sees themselves, a manager sees their reports, an
 * admin sees everyone. Adding a separate "are you a manager" gate here would be
 * a second authorisation rule to keep in step with the first, for no gain.
 */
async function load() {
  try {
    return await withUser(async (repo, user) => {
      const [summaries, employees, holidays] = await Promise.all([
        repo.tickets.listSummaries({ openOnly: true }),
        repo.employees.listActive(),
        repo.calendar.holidays(),
      ]);
      await repo.accessLog.record({ event: 'LIST', entity: 'tickets', entityId: null });
      return { user, summaries, employees, holidays };
    });
  } catch (err) {
    if (err instanceof AccessDeniedError) return null;
    throw err;
  }
}

interface PersonLoad {
  readonly id: string;
  readonly name: string;
  readonly open: number;
  readonly overdue: number;
  readonly stale: number;
  readonly nextDeadline: IsoDate | null;
}

export default async function TeamPage() {
  const data = await load();
  if (data === null) return <Denied />;

  const { user, summaries, employees, holidays } = data;
  const today = istDateOf(new Date());
  const nameOf = new Map(employees.map((e: Employee) => [e.id, e.displayName]));

  const staleOf = (s: TicketSummary): boolean =>
    isStale(
      {
        status: s.ticket.status,
        priority: s.ticket.priority,
        // Never punched: the clock runs from when the work was raised, otherwise a
        // ticket nobody has touched would never be flagged.
        //
        // istDateOf, NOT createdAt.slice(0,10) — the latter is the UTC date, which
        // is a day early for anything raised after 18:30 UTC. Exactly the bug
        // calendar.ts exists to prevent.
        lastActivityDate: s.lastPunchDate ?? istDateOf(new Date(s.ticket.createdAt)),
      },
      today,
      holidays,
    );

  const byPerson = new Map<string, PersonLoad>();
  for (const s of summaries) {
    const id = s.ticket.assigneeId;
    const prev = byPerson.get(id) ?? {
      id,
      name: nameOf.get(id) ?? 'Unknown',
      open: 0,
      overdue: 0,
      stale: 0,
      nextDeadline: null,
    };
    byPerson.set(id, {
      ...prev,
      open: prev.open + 1,
      overdue: prev.overdue + (isOverdue(s.ticket, today) ? 1 : 0),
      stale: prev.stale + (staleOf(s) ? 1 : 0),
      nextDeadline:
        prev.nextDeadline === null || s.ticket.deadline < prev.nextDeadline
          ? s.ticket.deadline
          : prev.nextDeadline,
    });
  }

  // Heaviest problem first: overdue, then stale, then raw load.
  const people = [...byPerson.values()].sort(
    (a, b) => b.overdue - a.overdue || b.stale - a.stale || b.open - a.open,
  );

  const staleTickets = summaries.filter(staleOf);

  return (
    <Shell user={user}>
      <PageHeading title="Team board" meta={<span className="tnum">{today}</span>} />

      <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">
        Everything currently open that you are permitted to see, grouped by the person doing it.
        Stale means in flight but silent: no update for {STALE_THRESHOLD_WORKING_DAYS.P1} working day
        on a P1, {STALE_THRESHOLD_WORKING_DAYS.P2} on a P2, {STALE_THRESHOLD_WORKING_DAYS.P3} on a P3.
      </p>

      <section className="mt-6">
        {people.length === 0 ? (
          <Card>
            <p className="text-sm text-[var(--muted)]">Nothing open across anyone you can see.</p>
          </Card>
        ) : (
          <div className="overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--surface)]">
            <table className="w-full min-w-[36rem] border-collapse text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                  <th className="px-3 py-2 font-medium">Person</th>
                  <th className="px-3 py-2 font-medium">Open</th>
                  <th className="px-3 py-2 font-medium">Overdue</th>
                  <th className="px-3 py-2 font-medium">Stale</th>
                  <th className="px-3 py-2 font-medium">Next deadline</th>
                </tr>
              </thead>
              <tbody>
                {people.map((p) => (
                  <tr key={p.id} className="border-b border-[var(--border)] last:border-0">
                    <td className="px-3 py-2">
                      {p.name}
                      {p.id === user.employee.id && (
                        <span className="ml-2 text-xs text-[var(--muted)]">you</span>
                      )}
                    </td>
                    <td className="px-3 py-2 tnum">{p.open}</td>
                    <td className="px-3 py-2 tnum">
                      {p.overdue > 0 ? (
                        <span className="font-medium text-[var(--danger)]">{p.overdue}</span>
                      ) : (
                        <span className="text-[var(--muted)]">0</span>
                      )}
                    </td>
                    <td className="px-3 py-2 tnum">
                      {p.stale > 0 ? (
                        <span className="font-medium text-[var(--warn)]">{p.stale}</span>
                      ) : (
                        <span className="text-[var(--muted)]">0</span>
                      )}
                    </td>
                    <td className="px-3 py-2 tnum">{p.nextDeadline ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="mt-8">
        <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--muted)]">
          Gone quiet
          <span className="ml-2 font-normal normal-case tracking-normal">
            {staleTickets.length} {staleTickets.length === 1 ? 'ticket' : 'tickets'}
          </span>
        </h2>

        {staleTickets.length === 0 ? (
          <p className="mt-3 rounded-md border border-dashed border-[var(--border)] px-4 py-6 text-sm text-[var(--muted)]">
            Nothing has gone quiet. Every open ticket has been updated within its priority window.
          </p>
        ) : (
          <ul className="mt-3 space-y-2">
            {staleTickets.map((s) => {
              const since = s.lastPunchDate ?? istDateOf(new Date(s.ticket.createdAt));
              const elapsed = workingDaysBetween(since, today, holidays);
              return (
                <li
                  key={s.ticket.id}
                  className="flex flex-wrap items-baseline gap-x-3 gap-y-1 rounded-md border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm"
                >
                  <Link
                    href={`/tickets/${s.ticket.ref}`}
                    className="font-mono text-xs underline decoration-[var(--border)] underline-offset-2 hover:decoration-[var(--text)]"
                  >
                    {s.ticket.ref}
                  </Link>
                  <span className="max-w-[24rem] truncate">{s.ticket.title}</span>
                  <span className="text-[var(--muted)]">
                    {nameOf.get(s.ticket.assigneeId) ?? '—'}
                  </span>
                  <span className="rounded border border-[var(--border)] px-1.5 py-0.5 text-xs text-[var(--muted)]">
                    {s.ticket.priority}
                  </span>
                  <span className="ml-auto text-xs text-[var(--warn)] tnum">
                    {s.punchCount === 0
                      ? `never updated, raised ${elapsed} working days ago`
                      : `${elapsed} working ${elapsed === 1 ? 'day' : 'days'} since the last update`}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </Shell>
  );
}
