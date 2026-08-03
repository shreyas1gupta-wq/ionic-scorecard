import Link from 'next/link';
import { AccessDeniedError } from '@/auth/access';
import { withUser } from '@/server/session';
import { istDateOf } from '@/domain/calendar';
import { Denied, Shell } from '../../_components/shell';
import { PageHeading } from '../../_components/ui';
import { NewTicketForm } from './new-ticket-form';

export const dynamic = 'force-dynamic';

async function load() {
  try {
    return await withUser(async (repo, user) => {
      const [colleagues, categories] = await Promise.all([
        repo.employees.listActive(),
        repo.reference.categories(),
      ]);
      return { user, colleagues, categories };
    });
  } catch (err) {
    if (err instanceof AccessDeniedError) return null;
    throw err;
  }
}

export default async function NewTicketPage() {
  const data = await load();
  if (data === null) return <Denied />;

  const { user, colleagues, categories } = data;

  return (
    <Shell user={user}>
      <PageHeading
        title="Raise a ticket"
        meta={
          <Link href="/tickets" className="hover:text-[var(--text)]">
            Back to open work
          </Link>
        }
      />
      <NewTicketForm
        colleagues={colleagues.map((c) => ({ id: c.id, displayName: c.displayName }))}
        categories={categories.map((c) => ({ id: c.id, name: c.name }))}
        defaultAssigneeId={user.employee.id}
        minDeadline={istDateOf(new Date())}
      />
    </Shell>
  );
}
