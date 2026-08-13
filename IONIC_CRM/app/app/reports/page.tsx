import { AccessDeniedError } from '@/auth/access';
import { withUser } from '@/server/session';
import { UNCATEGORISED, type GroupReport } from '@/domain/reports';
import { loadReport } from '@/service/reports';
import { Denied, Shell } from '../_components/shell';
import { Card, PageHeading } from '../_components/ui';

export const dynamic = 'force-dynamic';

async function load() {
  try {
    return await withUser(async (repo, user) => {
      const bundle = await loadReport(repo);
      await repo.accessLog.record({ event: 'LIST', entity: 'reports', entityId: null });
      return { user, ...bundle };
    });
  } catch (err) {
    if (err instanceof AccessDeniedError) return null;
    throw err;
  }
}

export default async function ReportsPage() {
  const data = await load();
  if (data === null) return <Denied />;

  const { user, report, nameOf, categoryNameOf } = data;
  const o = report.overall;

  return (
    <Shell user={user}>
      <PageHeading
        title="Reports"
        meta={
          <span className="flex flex-wrap items-center gap-3">
            <span className="tnum">{report.today}</span>
            <a href="/reports/export?kind=people" className="underline underline-offset-2">
              Export by person
            </a>
            <a href="/reports/export?kind=tickets" className="underline underline-offset-2">
              Export tickets
            </a>
          </span>
        }
      />

      <p className="mt-2 max-w-3xl text-sm text-[var(--muted)]">
        Everything you are permitted to see, including closed work. Exports carry exactly these
        numbers and the same visibility rules.
      </p>

      {/* The headline pair. Two on-time figures, side by side, on purpose. */}
      <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="On time vs promised"
          value={o.onTimePctOriginal === null ? '—' : `${o.onTimePctOriginal}%`}
          note="Against the deadline first set. The honest number."
          tone={
            o.onTimePctOriginal === null
              ? 'muted'
              : o.onTimePctOriginal >= 80
                ? 'good'
                : o.onTimePctOriginal >= 50
                  ? 'warn'
                  : 'bad'
          }
        />
        <Stat
          label="On time vs current"
          value={o.onTimePctCurrent === null ? '—' : `${o.onTimePctCurrent}%`}
          note="Against the deadline as it stood at closing."
          tone="muted"
        />
        <Stat
          label="Cycle time"
          value={o.medianCycleDays === null ? '—' : `${o.medianCycleDays}d`}
          note={
            o.p90CycleDays === null
              ? 'Working days, raised to closed.'
              : `Median. 90th percentile ${o.p90CycleDays}d. Working days.`
          }
          tone="muted"
        />
        <Stat
          label="Open now"
          value={String(o.open)}
          note={`${o.overdue} overdue · ${o.stale} stale · ${o.neverUpdated} never updated`}
          tone={o.overdue > 0 ? 'bad' : o.stale > 0 ? 'warn' : 'muted'}
        />
      </section>

      {o.deadlinesMoved > 0 && (
        <Card className="mt-4 border-[var(--warn)]">
          <p className="text-sm">
            <span className="font-medium">{o.deadlinesMoved}</span>{' '}
            {o.deadlinesMoved === 1 ? 'ticket has had its' : 'tickets have had their'} deadline
            moved, totalling <span className="font-medium tnum">{o.workingDaysSlipped}</span>{' '}
            working {o.workingDaysSlipped === 1 ? 'day' : 'days'} of slippage.
          </p>
          <p className="mt-1 text-xs text-[var(--muted)]">
            The gap between the two on-time figures above is the cost of those moves.
          </p>
        </Card>
      )}

      <GroupTable
        title="By person"
        groups={report.byPerson}
        labelOf={(k) => nameOf.get(k) ?? k}
        selfKey={user.employee.id}
      />

      <GroupTable
        title="By category"
        groups={report.byCategory}
        labelOf={(k) => (k === UNCATEGORISED ? UNCATEGORISED : (categoryNameOf.get(k) ?? k))}
      />

      <section className="mt-8">
        <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--muted)]">
          How long open work has been open
        </h2>
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Bucket label="0–3 working days" n={report.ageing.d0to3} />
          <Bucket label="4–7" n={report.ageing.d4to7} />
          <Bucket label="8–14" n={report.ageing.d8to14} />
          <Bucket label="15+" n={report.ageing.d15plus} emphasise />
        </div>
      </section>
    </Shell>
  );
}

function Stat({
  label,
  value,
  note,
  tone,
}: {
  label: string;
  value: string;
  note: string;
  tone: 'good' | 'warn' | 'bad' | 'muted';
}) {
  const colour =
    tone === 'good'
      ? 'text-[var(--accent)]'
      : tone === 'warn'
        ? 'text-[var(--warn)]'
        : tone === 'bad'
          ? 'text-[var(--danger)]'
          : 'text-[var(--text)]';
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tnum ${colour}`}>{value}</p>
      <p className="mt-1 text-xs text-[var(--muted)]">{note}</p>
    </Card>
  );
}

function Bucket({ label, n, emphasise }: { label: string; n: number; emphasise?: boolean }) {
  return (
    <Card>
      <p className="text-xs text-[var(--muted)]">{label}</p>
      <p
        className={`mt-1 text-xl font-semibold tnum ${
          emphasise && n > 0 ? 'text-[var(--danger)]' : ''
        }`}
      >
        {n}
      </p>
    </Card>
  );
}

function GroupTable({
  title,
  groups,
  labelOf,
  selfKey,
}: {
  title: string;
  groups: readonly GroupReport[];
  labelOf: (key: string) => string;
  selfKey?: string;
}) {
  if (groups.length === 0) return null;
  return (
    <section className="mt-8">
      <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--muted)]">{title}</h2>
      <div className="mt-3 overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--surface)]">
        <table className="w-full min-w-[52rem] border-collapse text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--muted)]">
              <th className="px-3 py-2 font-medium">Name</th>
              <th className="px-3 py-2 font-medium">Open</th>
              <th className="px-3 py-2 font-medium">Overdue</th>
              <th className="px-3 py-2 font-medium">Stale</th>
              <th className="px-3 py-2 font-medium">Closed</th>
              <th className="px-3 py-2 font-medium" title="Against the deadline first promised">
                On time (promised)
              </th>
              <th className="px-3 py-2 font-medium" title="Against the deadline at closing time">
                On time (current)
              </th>
              <th className="px-3 py-2 font-medium">Cycle med / p90</th>
              <th className="px-3 py-2 font-medium">Moved</th>
            </tr>
          </thead>
          <tbody>
            {groups.map((g) => (
              <tr key={g.key} className="border-b border-[var(--border)] last:border-0">
                <td className="px-3 py-2">
                  {labelOf(g.key)}
                  {selfKey === g.key && (
                    <span className="ml-2 text-xs text-[var(--muted)]">you</span>
                  )}
                </td>
                <td className="px-3 py-2 tnum">{g.open}</td>
                <td className="px-3 py-2 tnum">
                  {g.overdue > 0 ? (
                    <span className="font-medium text-[var(--danger)]">{g.overdue}</span>
                  ) : (
                    <span className="text-[var(--muted)]">0</span>
                  )}
                </td>
                <td className="px-3 py-2 tnum">
                  {g.stale > 0 ? (
                    <span className="font-medium text-[var(--warn)]">{g.stale}</span>
                  ) : (
                    <span className="text-[var(--muted)]">0</span>
                  )}
                </td>
                <td className="px-3 py-2 tnum">{g.closed}</td>
                <td className="px-3 py-2 tnum">
                  {g.onTimePctOriginal === null ? (
                    <span className="text-[var(--muted)]">—</span>
                  ) : (
                    `${g.onTimePctOriginal}%`
                  )}
                </td>
                <td className="px-3 py-2 tnum">
                  {g.onTimePctCurrent === null ? (
                    <span className="text-[var(--muted)]">—</span>
                  ) : (
                    `${g.onTimePctCurrent}%`
                  )}
                </td>
                <td className="px-3 py-2 tnum">
                  {g.medianCycleDays === null
                    ? '—'
                    : `${g.medianCycleDays} / ${g.p90CycleDays ?? '—'}`}
                </td>
                <td className="px-3 py-2 tnum">
                  {g.deadlinesMoved > 0 ? (
                    <span title={`${g.workingDaysSlipped} working days of slippage`}>
                      {g.deadlinesMoved}
                    </span>
                  ) : (
                    <span className="text-[var(--muted)]">0</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
