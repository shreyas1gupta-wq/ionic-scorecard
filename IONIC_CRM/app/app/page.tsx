import { redirect } from 'next/navigation';

export default function Home() {
  // There is no landing page for an internal tool: the useful thing is your work.
  redirect('/tickets');
}
