import Link from 'next/link';
import type { AuthenticatedUser } from '@/auth/identity';

/** Chrome around every authenticated page. */
export function Shell({
  user,
  children,
}: {
  user: AuthenticatedUser;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-dvh">
      <header className="border-b border-[var(--border)] bg-[var(--surface)]">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <Link href="/tickets" className="font-semibold tracking-tight">
            Ionic CRM
          </Link>
          <nav className="flex gap-4 text-sm">
            <Link href="/tickets" className="text-[var(--muted)] hover:text-[var(--text)]">
              My tickets
            </Link>
            <Link href="/team" className="text-[var(--muted)] hover:text-[var(--text)]">
              Team board
            </Link>
            <Link href="/reports" className="text-[var(--muted)] hover:text-[var(--text)]">
              Reports
            </Link>
            {/*
              Shown only to admins. This is presentation, not protection: the
              admin pages check the role themselves and the database enforces it
              regardless. Hiding the link stops the other 49 people wondering
              what they are missing; it is not what keeps them out.
            */}
            {user.employee.role === 'ADMIN' && (
              <Link href="/admin" className="text-[var(--muted)] hover:text-[var(--text)]">
                Admin
              </Link>
            )}
            <Link href="/tickets/new" className="text-[var(--muted)] hover:text-[var(--text)]">
              Raise a ticket
            </Link>
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm">
            {user.viaDevShim && (
              <span
                className="rounded border border-[var(--warn)] px-2 py-0.5 text-xs font-medium text-[var(--warn)]"
                title="Identity is coming from CRM_DEV_IDENTITY_EMAIL, not Cloudflare Access. This cannot happen in production — the app refuses to boot."
              >
                DEV IDENTITY
              </span>
            )}
            <span className="text-[var(--muted)]">
              {user.employee.displayName}
              <span className="ml-2 text-xs uppercase tracking-wide">{user.employee.role}</span>
            </span>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  );
}

/**
 * The unauthorised view.
 *
 * Says nothing about why. The only person who benefits from a reason here is
 * someone probing, and the reason is in the server log where it is useful.
 */
export function Denied() {
  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6">
      <h1 className="text-lg font-semibold">Not available</h1>
      <p className="mt-2 text-sm text-[var(--muted)]">
        This account cannot access Ionic CRM. If that seems wrong, ask an administrator to check
        whether your work address is on the allow-list.
      </p>
    </div>
  );
}
