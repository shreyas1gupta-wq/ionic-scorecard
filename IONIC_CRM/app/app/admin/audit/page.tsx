import { AccessDeniedError } from '@/auth/access';
import { withUser } from '@/server/session';
import { istDateOf } from '@/domain/calendar';
import { readAuditLog } from '@/service/admin';
import type { AuditRecord, Employee } from '@/repo/types';
import { Denied, Shell } from '../../_components/shell';
import { Card, PageHeading } from '../../_components/ui';
import { AdminNav } from '../nav';

export const dynamic = 'force-dynamic';

const PAGE_SIZE = 200;

/** India is UTC+05:30 and has never observed daylight saving — see domain/calendar.ts. */
const IST_OFFSET_MS = (5 * 60 + 30) * 60 * 1000;

/**
 * The clock time in IST, `HH:MM:SS`.
 *
 * Shift by the offset and read UTC fields, which is what `istDateOf` does for the
 * date half. Not `toLocaleTimeString('en-IN', { timeZone: … })`: that depends on
 * the runtime shipping a full ICU timezone database, and the Workers runtime is
 * not the place to discover that it does not.
 */
function istTimeOf(instant: string): string {
  const shifted = new Date(new Date(instant).getTime() + IST_OFFSET_MS);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(shifted.getUTCHours())}:${pad(shifted.getUTCMinutes())}:${pad(shifted.getUTCSeconds())}`;
}

/**
 * The audit log, with the chain verified on every view.
 *
 * `readAuditLog` records the fact that the log was read before it verifies —
 * REQUIREMENTS §10 asks for reads of the audit log to be audited too, and doing it
 * first means the head hash on screen includes the act of looking, rather than
 * being one entry stale the moment it renders.
 */
async function load() {
  try {
    return await withUser(async (repo, user) => {
      if (user.employee.role !== 'ADMIN') {
        await repo.accessLog.record({ event: 'DENIED', entity: 'audit_log', entityId: null });
        return { user, admin: false } as const;
      }

      const view = await readAuditLog(repo, PAGE_SIZE);
      const people = await repo.employees.listAll();
      await repo.accessLog.record({ event: 'VIEW', entity: 'audit_log', entityId: null });

      return { user, admin: true, view, people } as const;
    });
  } catch (err) {
    if (err instanceof AccessDeniedError) return null;
    throw err;
  }
}

export default async function AuditPage() {
  const data = await load();
  if (data === null || data.admin === false) return <Denied />;

  const { user, view, people } = data;
  const { entries, verification } = view;
  const nameOf = new Map(people.map((e: Employee) => [e.id, e.displayName]));

  return (
    <Shell user={user}>
      <PageHeading
        title="Audit log"
        meta={<span className="tnum">{verification.checked} entries checked</span>}
      />
      <AdminNav here="audit" />

      {/* ==================================================================
          The integrity indicator, not a badge.

          If the chain is broken this page must say so in the first thing the reader
          sees, and say which entries failed. A green tick that goes grey on failure
          is exactly the design that gets missed.
      */}
      {verification.ok ? (
        <Card className="mt-4 border-[var(--accent)]">
          <h2 className="text-sm font-medium text-[var(--accent)]">
            Chain intact — {verification.checked}{' '}
            {verification.checked === 1 ? 'entry' : 'entries'} recomputed
          </h2>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Every entry&rsquo;s hash was recalculated from its predecessor. Removing or altering a
            past entry — including deleting one and renumbering the rest — breaks this check,
            because the sequence number is inside the hash.
          </p>
          <dl className="mt-3 text-sm">
            <dt className="text-xs uppercase tracking-wide text-[var(--muted)]">
              Head hash · publish this as today&rsquo;s external anchor
            </dt>
            <dd className="mt-1 break-all font-mono text-xs">
              {verification.headHashHex ?? '— (the log is empty)'}
            </dd>
          </dl>
          <p className="mt-3 text-xs text-[var(--muted)]">
            Committing this value to the backup repository each day is what makes the chain hold
            against a database administrator: internal verification cannot detect a complete,
            consistent rewrite of history, but it cannot rewrite yesterday&rsquo;s commit.
          </p>
        </Card>
      ) : (
        <Card className="mt-4 border-[var(--danger)]">
          <h2 className="text-sm font-medium text-[var(--danger)]">
            CHAIN BROKEN — {verification.failures.length}{' '}
            {verification.failures.length === 1 ? 'failure' : 'failures'} across{' '}
            {verification.checked} entries
          </h2>
          <p className="mt-2 text-sm">
            The audit trail below can no longer be relied on. Compare the last-known-good head hash
            in the backup repository against the entries listed here to find where history
            diverges, and treat this as a security incident: SEBI&rsquo;s clock is 6 hours from
            noticing, CERT-In&rsquo;s the same.
          </p>
          <ul className="mt-3 space-y-1 font-mono text-xs">
            {verification.failures.map((failure, i) => (
              <li key={i} className="break-all text-[var(--danger)]">
                {failure}
              </li>
            ))}
          </ul>
          <dl className="mt-3 text-sm">
            <dt className="text-xs uppercase tracking-wide text-[var(--muted)]">
              Current head hash — do NOT publish this as an anchor
            </dt>
            <dd className="mt-1 break-all font-mono text-xs">
              {verification.headHashHex ?? '—'}
            </dd>
          </dl>
        </Card>
      )}

      <section className="mt-8">
        <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--muted)]">
          Newest first
          <span className="ml-2 font-normal normal-case tracking-normal">
            showing up to {PAGE_SIZE}; nothing here can be edited or deleted, by anyone
          </span>
        </h2>

        {entries.length === 0 ? (
          <p className="mt-3 rounded-md border border-dashed border-[var(--border)] px-4 py-6 text-sm text-[var(--muted)]">
            Nothing recorded yet.
          </p>
        ) : (
          <ol className="mt-3 space-y-2">
            {entries.map((e: AuditRecord) => (
              <li
                key={e.seq}
                className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm"
              >
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <span className="font-mono text-xs text-[var(--muted)] tnum">#{e.seq}</span>
                  <span className="font-medium">{e.action}</span>
                  <span className="text-xs text-[var(--muted)]">{e.entity}</span>
                  <span className="text-[var(--muted)]">
                    {e.actorId === null ? 'system' : (nameOf.get(e.actorId) ?? e.actorId)}
                  </span>
                  <span className="ml-auto text-xs text-[var(--muted)] tnum">
                    {istDateOf(new Date(e.occurredAt))} {istTimeOf(e.occurredAt)} IST
                  </span>
                </div>
                <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-all text-xs text-[var(--muted)]">
                  {JSON.stringify(e.payload)}
                </pre>
                <div className="mt-1 break-all font-mono text-[10px] text-[var(--muted)]">
                  {e.rowHashHex}
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </Shell>
  );
}
