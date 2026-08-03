import Link from 'next/link';
import { AccessDeniedError } from '@/auth/access';
import { withUser } from '@/server/session';
import { istDateOf, workingDaysBetween, type IsoDate } from '@/domain/calendar';
import { isOverdue, isStale, type Priority, type TicketStatus } from '@/domain/tickets';
import type { Employee, TicketSummary } from '@/repo/types';
import { Denied, Shell } from '../_components/shell';
import { PageHeading } from '../_components/ui';

export const dynamic = 'force-dynamic';

/**
 * Load everything the page needs, or null if this account may not be here.
 *
 * Only `AccessDeniedError` becomes null. Anything else propagates, because a
 * database failure rendering as "not available" would be a genuinely misleading
 * thing to show someone.
 */
async function load() {
  try {
    return await withUser(async (repo, user) => {
      const [summaries, employees, holidays] = await Promise.all([
        // Summaries rather than plain tickets: staleness needs the last punch, and
        // fetching each ticket's history in turn would make this page slower with
        // every ticket the firm ever raises.
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

export default async function TicketsPage() {
  const data = await load();
  if (data === null) return <Denied />;

  const { user, summaries, employees, holidays } = data;
  const today = istDateOf(new Date());
  const nameOf = new Map(employees.map((e: Employee) => [e.id, e.displayName]));

  const mine = summaries.filter((s) => s.ticket.assigneeId === user.employee.id);
  const others = summaries.filter((s) => s.ticket.assigneeId !== user.employee.id);
  const overdueCount = mine.filter((s) => isOverdue(s.ticket, today)).length;

  return (
    <Shell user={user}>
      <PageHeading
        title="Open work"
        meta={
          <>
            {today} · {mine.length} assigned to you
            {overdueCount > 0 && (
              <span className="ml-2 font-medium text-[var(--danger)]">{overdueCount} overdue</span>
            )}
          </>
        }
      />

      <Section
        title="Assigned to you"
        rows={mine}
        today={today}
        holidays={holidays}
        nameOf={nameOf}
        emptyMessage="Nothing open. Either you are on top of everything, or nobody has raised anything yet."
      />

      {others.length > 0 && (
        <Section
          title="Also visible to you"
          rows={others}
          today={today}
          holidays={holidays}
          nameOf={nameOf}
          emptyMessage=""
        />
      )}
    </Shell>
  );
}

function Section({
  title,
  rows,
  today,
  holidays,
  nameOf,
  emptyMessage,
}: {
  title: string;
  rows: readonly TicketSummary[];
  today: IsoDate;
  holidays: ReadonlySet<IsoDate>;
  nameOf: Map<string, string>;
  emptyMessage: string;
}) {
  return (
    <section className="mt-8">
      <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--muted)]">{title}</h2>

      {rows.length === 0 ? (
        <p className="mt-3 rounded-md border border-dashed border-[var(--border)] px-4 py-6 text-sm text-[var(--muted)]">
          {emptyMessage}
        </p>
      ) : (
        // Wide tables scroll inside their own container so the page body never
        // scrolls sideways on a phone.
        <div className="mt-3 overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--surface)]">
          <table className="w-full min-w-[48rem] border-collapse text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                <th className="px-3 py-2 font-medium">Ref</th>
                <th className="px-3 py-2 font-medium">Title</th>
                <th className="px-3 py-2 font-medium">Assignee</th>
                <th className="px-3 py-2 font-medium">Pri</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Last update</th>
                <th className="px-3 py-2 font-medium">Deadline</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => {
                const t = s.ticket;
                const overdue = isOverdue(t, today);
                // istDateOf, not createdAt.slice(0,10): the latter is the UTC
                // date and is a day early for anything raised after 18:30 UTC.
                const since = s.lastPunchDate ?? istDateOf(new Date(t.createdAt));
                const stale = isStale(
                  { status: t.status, priority: t.priority, lastActivityDate: since },
                  today,
                  holidays,
                );
                const daysLeft = workingDaysBetween(today, t.deadline, holidays);
                const dueToday = t.deadline === today;
                return (
                  <tr key={t.id} className="border-b border-[var(--border)] last:border-0">
                    <td className="px-3 py-2 font-mono text-xs whitespace-nowrap">
                      <Link
                        href={`/tickets/${t.ref}`}
                        className="underline decoration-[var(--border)] underline-offset-2 hover:decoration-[var(--text)]"
                      >
                        {t.ref}
                      </Link>
                    </td>
                    <td className="px-3 py-2">
                      <Link
                        href={`/tickets/${t.ref}`}
                        className="block max-w-[24rem] truncate hover:underline"
                        title={t.title}
                      >
                        {t.title}
                      </Link>
                      {t.deadline !== t.originalDeadline && (
                        <span
                          className="text-xs text-[var(--muted)] tnum"
                          title="The deadline has been moved. Performance is reported against both dates."
                        >
                          originally {t.originalDeadline}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {nameOf.get(t.assigneeId) ?? '—'}
                    </td>
                    <td className="px-3 py-2">
                      <PriorityTag priority={t.priority} />
                    </td>
                    <td className="px-3 py-2">
                      <StatusTag status={t.status} />
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap tnum">
                      {s.punchCount === 0 ? (
                        <span className="text-xs text-[var(--muted)]">never</span>
                      ) : (
                        <span className={stale ? 'text-[var(--warn)]' : undefined}>
                          {s.lastPunchDate}
                        </span>
                      )}
                      {stale && (
                        <span
                          className="ml-2 text-xs font-medium text-[var(--warn)]"
                          title="In flight but silent for longer than this priority allows."
                        >
                          stale
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap tnum">
                      <span className={overdue ? 'font-medium text-[var(--danger)]' : undefined}>
                        {t.deadline}
                      </span>
                      {overdue ? (
                        <span className="ml-2 text-xs text-[var(--danger)]">overdue</span>
                      ) : dueToday ? (
                        <span className="ml-2 text-xs text-[var(--warn)]">due today</span>
                      ) : (
                        <span className="ml-2 text-xs text-[var(--muted)]">
                          {daysLeft} working {daysLeft === 1 ? 'day' : 'days'}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function PriorityTag({ priority }: { priority: Priority }) {
  const tone =
    priority === 'P1'
      ? 'text-[var(--danger)] border-[var(--danger)]'
      : priority === 'P2'
        ? 'text-[var(--warn)] border-[var(--warn)]'
        : 'text-[var(--muted)] border-[var(--border)]';
  return (
    <span className={`rounded border px-1.5 py-0.5 text-xs font-medium ${tone}`}>{priority}</span>
  );
}

const STATUS_LABEL: Record<TicketStatus, string> = {
  OPEN: 'Open',
  IN_PROGRESS: 'In progress',
  BLOCKED: 'Blocked',
  DONE: 'Done',
  CANCELLED: 'Cancelled',
};

function StatusTag({ status }: { status: TicketStatus }) {
  const tone =
    status === 'BLOCKED'
      ? 'text-[var(--danger)] border-[var(--danger)]'
      : status === 'IN_PROGRESS'
        ? 'text-[var(--accent)] border-[var(--accent)]'
        : 'text-[var(--muted)] border-[var(--border)]';
  return (
    <span className={`whitespace-nowrap rounded border px-1.5 py-0.5 text-xs ${tone}`}>
      {STATUS_LABEL[status]}
    </span>
  );
}
