import Link from 'next/link';

/**
 * Sub-navigation for the three admin pages.
 *
 * Local to /admin rather than in the global shell: the shell's nav is shown to
 * everyone, and an "Admin" link that leads to a refusal for most of the firm is a
 * worse experience than no link. Whoever owns the shell can add a role-gated
 * entry point to it; until then these three pages link to each other.
 */
export function AdminNav({ here }: { here: 'home' | 'review' | 'audit' }) {
  const item = (key: typeof here, href: string, label: string) =>
    key === here ? (
      <span key={key} className="font-medium">
        {label}
      </span>
    ) : (
      <Link key={key} href={href} className="text-[var(--muted)] hover:text-[var(--text)]">
        {label}
      </Link>
    );

  return (
    <nav className="mt-2 flex flex-wrap gap-4 text-sm">
      {item('home', '/admin', 'People, calendar, categories')}
      {item('review', '/admin/access-review', 'Access review')}
      {item('audit', '/admin/audit', 'Audit log')}
    </nav>
  );
}
