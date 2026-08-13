import { AccessDeniedError } from '@/auth/access';
import { withUser } from '@/server/session';
import { istDateOf } from '@/domain/calendar';
import { DORMANT_AFTER_DAYS, buildAccessReview, type AccountReview } from '@/service/admin';
import { Denied, Shell } from '../../_components/shell';
import { Card, PageHeading } from '../../_components/ui';
import { AdminNav } from '../nav';
import { RecordReviewForm } from '../forms';

export const dynamic = 'force-dynamic';

/** How far back to look for the previous sign-off. See `load`. */
const AUDIT_SCAN = 500;

/**
 * The half-yearly access-rights and privileged-user review.
 *
 * CSCRF PR.AA, mandatory for all regulated entities and not exempted (DESIGN §8).
 * Two findings are asked for by name — accounts that are not being used, and
 * accounts that hold privilege — and one action matters more than the report:
 * recording that the review happened, with who did it and what it covered.
 */
async function load() {
  try {
    return await withUser(async (repo, user) => {
      if (user.employee.role !== 'ADMIN') {
        await repo.accessLog.record({
          event: 'DENIED',
          entity: 'admin',
          entityId: 'access-review',
        });
        return { user, admin: false } as const;
      }

      const review = await buildAccessReview(repo);
      // Found by scanning the newest AUDIT_SCAN entries rather than by a dedicated
      // query, so no new port is needed for a page run twice a year. The bound is
      // reported honestly below: absence here means "not in the recent log", not
      // "never happened".
      const recent = await repo.audit.list(AUDIT_SCAN);
      const lastReview = recent.find((e) => e.action === 'ACCESS_REVIEW_PERFORMED');

      // Reading a report of who has access to what is itself an access event.
      await repo.accessLog.record({ event: 'EXPORT', entity: 'employees', entityId: null });

      return { user, admin: true, review, lastReview } as const;
    });
  } catch (err) {
    if (err instanceof AccessDeniedError) return null;
    throw err;
  }
}

export default async function AccessReviewPage() {
  const data = await load();
  if (data === null || data.admin === false) return <Denied />;

  const { user, review, lastReview } = data;
  const privileged = review.accounts.filter((a) => a.privileged);
  const dormant = review.accounts.filter((a) => a.dormant);

  return (
    <Shell user={user}>
      <PageHeading
        title="Access-rights and privileged-user review"
        meta={<span className="tnum">{review.reviewDate}</span>}
      />
      <AdminNav here="review" />

      <p className="mt-4 max-w-2xl text-sm text-[var(--muted)]">
        Due every six months. Check that every account below still needs the access it has, act on
        anything that does not, then record the review — the record is the part an auditor asks
        for, and it goes into the audit chain where it cannot be back-dated.
      </p>

      <div className="mt-6 grid gap-3 sm:grid-cols-4">
        <Stat label="Accounts" value={review.accounts.length} />
        <Stat label="Active" value={review.activeCount} />
        <Stat label="Privileged" value={review.privilegedCount} warnAboveZero />
        <Stat
          label={`No login in ${DORMANT_AFTER_DAYS} days`}
          value={review.dormantCount}
          warnAboveZero
        />
      </div>

      <Card className="mt-6">
        <h2 className="text-sm font-medium">Last recorded review</h2>
        {lastReview === undefined ? (
          <p className="mt-2 text-sm text-[var(--warn)]">
            No review found in the most recent {AUDIT_SCAN} audit entries. If one was performed
            outside this system, there is no evidence of it here.
          </p>
        ) : (
          <p className="mt-2 text-sm">
            <span className="tnum">{String(lastReview.payload.reviewDate ?? '—')}</span>
            <span className="ml-2 text-[var(--muted)]">
              by {String(lastReview.payload.reviewedBy ?? '—')}
            </span>
            {typeof lastReview.payload.note === 'string' && (
              <span className="ml-2 text-[var(--muted)]">— {lastReview.payload.note}</span>
            )}
          </p>
        )}
      </Card>

      {/* ==================================================================
          Findings first. The full list is below, but a page that opens with 40
          unremarkable rows invites the reviewer to skim past the two that matter.
      */}
      <section className="mt-8">
        <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--muted)]">
          Privileged accounts
          <span className="ml-2 font-normal normal-case tracking-normal">
            {privileged.length} {privileged.length === 1 ? 'account' : 'accounts'} with full access
            to every ticket and to this audit trail
          </span>
        </h2>
        {privileged.length === 0 ? (
          <p className="mt-3 rounded-md border border-dashed border-[var(--border)] px-4 py-6 text-sm text-[var(--warn)]">
            No administrators. Nobody can maintain the allow-list or read the audit log.
          </p>
        ) : (
          <AccountTable rows={privileged} />
        )}
      </section>

      <section className="mt-8">
        <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--muted)]">
          Dormant accounts
          <span className="ml-2 font-normal normal-case tracking-normal">
            no recorded sign-in in the last {DORMANT_AFTER_DAYS} days
          </span>
        </h2>
        {dormant.length === 0 ? (
          <p className="mt-3 rounded-md border border-dashed border-[var(--border)] px-4 py-6 text-sm text-[var(--muted)]">
            Every account has signed in inside the window.
          </p>
        ) : (
          <AccountTable rows={dormant} />
        )}
      </section>

      <section className="mt-10">
        <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--muted)]">
          Every account
        </h2>
        <AccountTable rows={review.accounts} />
      </section>

      <Card className="mt-8">
        <h2 className="text-sm font-medium">Sign off</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Recorded against you, {user.employee.displayName}, with the figures as they stand at the
          moment you submit — not the ones on screen, in case the two have drifted.
        </p>
        <div className="mt-4">
          <RecordReviewForm />
        </div>
      </Card>
    </Shell>
  );
}

/** `warnAboveZero` is for the two counts that are findings when non-zero. */
function Stat({
  label,
  value,
  warnAboveZero = false,
}: {
  label: string;
  value: number;
  warnAboveZero?: boolean;
}) {
  const warn = warnAboveZero && value > 0;
  return (
    <div className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</div>
      <div className={`mt-1 text-xl font-semibold tnum ${warn ? 'text-[var(--warn)]' : ''}`}>
        {value}
      </div>
    </div>
  );
}

function AccountTable({ rows }: { rows: readonly AccountReview[] }) {
  return (
    <div className="mt-3 overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--surface)]">
      <table className="w-full min-w-[44rem] border-collapse text-sm">
        <thead>
          <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--muted)]">
            <th className="px-3 py-2 font-medium">Account</th>
            <th className="px-3 py-2 font-medium">Role</th>
            <th className="px-3 py-2 font-medium">Reports to</th>
            <th className="px-3 py-2 font-medium">Status</th>
            <th className="px-3 py-2 font-medium">Last login</th>
            <th className="px-3 py-2 font-medium">Flags</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((a) => (
            <tr key={a.employee.id} className="border-b border-[var(--border)] last:border-0">
              <td className="px-3 py-2">
                {a.employee.displayName}
                <div className="text-xs text-[var(--muted)]">{a.employee.workEmail}</div>
              </td>
              <td className="px-3 py-2 text-xs">{a.employee.role}</td>
              <td className="px-3 py-2 text-xs text-[var(--muted)]">{a.managerName ?? '—'}</td>
              <td className="px-3 py-2 text-xs">
                {a.employee.status === 'ACTIVE' ? (
                  'Active'
                ) : (
                  <span className="text-[var(--muted)]">Deactivated</span>
                )}
              </td>
              <td className="px-3 py-2 text-xs">
                {a.lastLoginAt !== null ? (
                  <span className="tnum">{istDateOf(new Date(a.lastLoginAt))}</span>
                ) : a.lastSeenAt !== null ? (
                  <span className="text-[var(--muted)]">
                    <span className="tnum">{istDateOf(new Date(a.lastSeenAt))}</span> · activity,
                    not a sign-in
                  </span>
                ) : (
                  <span className="text-[var(--warn)]">never</span>
                )}
              </td>
              <td className="px-3 py-2 text-xs">
                <span className="flex flex-wrap gap-1.5">
                  {a.privileged && (
                    <span className="rounded border border-[var(--warn)] px-1.5 py-0.5 text-[var(--warn)]">
                      privileged
                    </span>
                  )}
                  {a.dormant && a.employee.status === 'ACTIVE' && (
                    <span className="rounded border border-[var(--warn)] px-1.5 py-0.5 text-[var(--warn)]">
                      dormant
                    </span>
                  )}
                  {a.privileged && a.dormant && a.employee.status === 'ACTIVE' && (
                    <span className="rounded border border-[var(--danger)] px-1.5 py-0.5 text-[var(--danger)]">
                      revoke first
                    </span>
                  )}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
