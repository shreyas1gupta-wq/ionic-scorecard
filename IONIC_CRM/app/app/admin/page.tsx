import { AccessDeniedError } from '@/auth/access';
import { withUser } from '@/server/session';
import { istDateOf } from '@/domain/calendar';
import { buildAccessReview, type AccountReview } from '@/service/admin';
import { Denied, Shell } from '../_components/shell';
import { Card, PageHeading } from '../_components/ui';
import { AdminNav } from './nav';
import {
  AddCategoryForm,
  AddHolidayForm,
  AddPersonForm,
  CategoryActiveButton,
  DeactivateForm,
  ManagerForm,
  RemoveHolidayButton,
  RoleForm,
} from './forms';

export const dynamic = 'force-dynamic';

/**
 * The people table reuses `buildAccessReview`.
 *
 * It already assembles exactly what this section needs — role, manager name,
 * status, last login — and duplicating that assembly here would be a second place
 * for "how do we work out when someone last signed in" to drift. Only the sort
 * order differs: the review leads with its findings, a directory is alphabetical.
 */
async function load() {
  try {
    return await withUser(async (repo, user) => {
      if (user.employee.role !== 'ADMIN') {
        // Recorded, not silently dropped. CSCRF PR.AA asks who tried what, and a
        // refused attempt at the admin console is the more interesting half.
        await repo.accessLog.record({ event: 'DENIED', entity: 'admin', entityId: null });
        return { user, admin: false } as const;
      }

      // Sequential: everything here shares one database transaction, and issuing
      // statements on it concurrently relies on the driver queueing rather than
      // interleaving them. Three round trips is not worth resting on that.
      const review = await buildAccessReview(repo);
      const holidays = await repo.calendar.listHolidays();
      const categories = await repo.reference.allCategories();
      await repo.accessLog.record({ event: 'LIST', entity: 'employees', entityId: null });

      return { user, admin: true, review, holidays, categories } as const;
    });
  } catch (err) {
    if (err instanceof AccessDeniedError) return null;
    throw err;
  }
}

const ROLE_LABEL: Record<string, string> = {
  EMPLOYEE: 'Employee',
  MANAGER: 'Manager',
  ADMIN: 'Administrator',
};

export default async function AdminPage() {
  const data = await load();
  if (data === null || data.admin === false) return <Denied />;

  const { user, review, holidays, categories } = data;
  const today = istDateOf(new Date());

  const directory = [...review.accounts].sort((a, b) =>
    a.employee.displayName.localeCompare(b.employee.displayName),
  );
  const selectable = review.accounts
    .filter((a) => a.employee.status === 'ACTIVE')
    .map((a) => ({ id: a.employee.id, displayName: a.employee.displayName }))
    .sort((a, b) => a.displayName.localeCompare(b.displayName));

  const upcoming = holidays.filter((h) => h.date >= today);
  const past = holidays.filter((h) => h.date < today);

  return (
    <Shell user={user}>
      <PageHeading title="Administration" meta={<span className="tnum">{today}</span>} />
      <AdminNav here="home" />

      <p className="mt-4 max-w-2xl text-sm text-[var(--muted)]">
        Every change on this page is written into the tamper-evident audit chain, including who
        made it. Nobody can change their own role, and nobody is ever deleted — accounts are
        deactivated, so the work they did keeps their name on it.
      </p>

      {/* ================================================================== */}
      <section className="mt-8">
        <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--muted)]">
          People
          <span className="ml-2 font-normal normal-case tracking-normal">
            {review.activeCount} active
            {review.deactivatedCount > 0 && `, ${review.deactivatedCount} deactivated`}
          </span>
        </h2>

        <div className="mt-3 overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--surface)]">
          <table className="w-full min-w-[52rem] border-collapse text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                <th className="px-3 py-2 font-medium">Person</th>
                <th className="px-3 py-2 font-medium">Role</th>
                <th className="px-3 py-2 font-medium">Reports to</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Last login</th>
                <th className="px-3 py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {directory.map((a) => (
                <tr key={a.employee.id} className="border-b border-[var(--border)] last:border-0">
                  <td className="px-3 py-2">
                    <span className={a.employee.status === 'ACTIVE' ? '' : 'text-[var(--muted)]'}>
                      {a.employee.displayName}
                    </span>
                    {a.employee.id === user.employee.id && (
                      <span className="ml-2 text-xs text-[var(--muted)]">you</span>
                    )}
                    <div className="text-xs text-[var(--muted)]">{a.employee.workEmail}</div>
                  </td>
                  <td className="px-3 py-2">
                    {a.employee.status === 'ACTIVE' ? (
                      <RoleForm
                        employeeId={a.employee.id}
                        current={a.employee.role}
                        isSelf={a.employee.id === user.employee.id}
                      />
                    ) : (
                      <span className="text-xs text-[var(--muted)]">
                        {ROLE_LABEL[a.employee.role] ?? a.employee.role}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {a.employee.status === 'ACTIVE' ? (
                      <ManagerForm
                        employeeId={a.employee.id}
                        current={a.employee.managerId}
                        people={selectable}
                      />
                    ) : (
                      <span className="text-xs text-[var(--muted)]">{a.managerName ?? '—'}</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {a.employee.status === 'ACTIVE' ? (
                      <span className="text-xs">Active</span>
                    ) : (
                      <span className="text-xs text-[var(--muted)]">Deactivated</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <LastSeen account={a} />
                  </td>
                  <td className="px-3 py-2">
                    {a.employee.status === 'ACTIVE' && a.employee.id !== user.employee.id && (
                      <DeactivateForm
                        employeeId={a.employee.id}
                        name={a.employee.displayName}
                      />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mt-2 text-xs text-[var(--muted)]">
          &ldquo;Last login&rdquo; comes from this application&rsquo;s own access log, not from
          Cloudflare&rsquo;s — that one is discarded after about a day, and CSCRF requires two
          years. Where no sign-in has been recorded, the most recent activity of any kind is shown
          instead and labelled as such.
        </p>

        <Card className="mt-4">
          <h3 className="text-sm font-medium">Add someone</h3>
          <div className="mt-3">
            <AddPersonForm people={selectable} />
          </div>
        </Card>
      </section>

      {/* ================================================================== */}
      <section className="mt-10">
        <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--muted)]">
          Holiday calendar
          <span className="ml-2 font-normal normal-case tracking-normal">
            {holidays.length} {holidays.length === 1 ? 'day' : 'days'}
          </span>
        </h2>
        <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">
          Maintained here rather than pulled from an external API, because a holiday list that
          silently goes stale corrupts every deadline and staleness figure in the system. Changes
          are audited: adding a day retrospectively changes whether past work was late.
        </p>

        <div className="mt-3 grid gap-4 lg:grid-cols-2">
          <Card>
            <h3 className="text-sm font-medium">Blocked out</h3>
            {holidays.length === 0 ? (
              <p className="mt-2 text-sm text-[var(--muted)]">
                No holidays yet, so every weekday counts as a working day.
              </p>
            ) : (
              <ul className="mt-3 space-y-1.5 text-sm">
                {[...upcoming, ...past].map((h) => (
                  <li key={h.date} className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <span className={`tnum ${h.date < today ? 'text-[var(--muted)]' : ''}`}>
                      {h.date}
                    </span>
                    <span className={h.date < today ? 'text-[var(--muted)]' : ''}>{h.name}</span>
                    <span className="ml-auto">
                      <RemoveHolidayButton date={h.date} />
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <h3 className="text-sm font-medium">Add a holiday</h3>
            <div className="mt-3">
              <AddHolidayForm />
            </div>
          </Card>
        </div>
      </section>

      {/* ================================================================== */}
      <section className="mt-10">
        <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--muted)]">
          Categories
        </h2>
        <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">
          Retired categories stay on the tickets that already use them and disappear from the
          picker. They are never deleted, because deleting one would mean rewriting history.
        </p>

        <div className="mt-3 grid gap-4 lg:grid-cols-2">
          <Card>
            <h3 className="text-sm font-medium">In use</h3>
            {categories.length === 0 ? (
              <p className="mt-2 text-sm text-[var(--muted)]">None yet.</p>
            ) : (
              <ul className="mt-3 space-y-1.5 text-sm">
                {categories.map((c) => (
                  <li key={c.id} className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <span className={c.active ? '' : 'text-[var(--muted)] line-through'}>
                      {c.name}
                    </span>
                    {!c.active && <span className="text-xs text-[var(--muted)]">retired</span>}
                    <span className="ml-auto">
                      <CategoryActiveButton id={c.id} active={c.active} />
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <h3 className="text-sm font-medium">Add a category</h3>
            <div className="mt-3">
              <AddCategoryForm />
            </div>
          </Card>
        </div>
      </section>
    </Shell>
  );
}

/**
 * Last login, with last activity as an explicitly-labelled fallback.
 *
 * The two are not the same thing and the page must not let them look the same: a
 * read is not an authentication, and treating one as the other would let a dormant
 * account with a live session read as current.
 */
function LastSeen({ account }: { account: AccountReview }) {
  if (account.lastLoginAt !== null) {
    return <span className="tnum text-xs">{istDateOf(new Date(account.lastLoginAt))}</span>;
  }
  if (account.lastSeenAt !== null) {
    return (
      <span className="text-xs text-[var(--muted)]">
        <span className="tnum">{istDateOf(new Date(account.lastSeenAt))}</span> · activity
      </span>
    );
  }
  return <span className="text-xs text-[var(--warn)]">never</span>;
}
