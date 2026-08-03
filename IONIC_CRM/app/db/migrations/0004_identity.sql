-- =============================================================================
-- 0004_identity.sql — the single pre-authorisation query
--
-- Every other read in this system happens as a known employee, under RLS. But
-- resolving "who is this verified email?" necessarily happens BEFORE an identity
-- exists, so it cannot go through a policy that requires one.
--
-- Rather than granting the app a broad read of `employees` (which would defeat
-- the point), there is exactly one SECURITY DEFINER function, scoped as tightly
-- as the job allows:
--
--   * takes an email and returns at most one row;
--   * returns ACTIVE employees only, so a deactivated person is simply not
--     found — offboarding takes effect immediately, with no extra check for a
--     caller to forget;
--   * exposes no way to enumerate the table.
--
-- This is the whole trusted surface for authentication. It is small on purpose:
-- it should be reviewable in one sitting.
-- =============================================================================

create or replace function app.resolve_identity(p_email text)
returns table (
  id           uuid,
  work_email   text,
  display_name text,
  role         text,
  manager_id   uuid,
  status       text
)
language sql stable security definer set search_path = public, pg_temp
as $$
  select e.id, e.work_email, e.display_name, e.role, e.manager_id, e.status
  from employees e
  where e.work_email = lower(trim(p_email))
    and e.status = 'ACTIVE'
  limit 1;
$$;

grant execute on function app.resolve_identity(text) to crm_app;
