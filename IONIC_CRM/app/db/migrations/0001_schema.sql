-- =============================================================================
-- 0001_schema.sql — tables, roles, helper functions, immutability triggers
--
-- Portable Postgres. No Supabase-specific constructs: identity comes from
-- `SET LOCAL app.employee_id`, not from auth.uid(). That keeps the schema
-- runnable on PGlite for tests, on a self-hosted Postgres, and on Supabase
-- without change — which is what DESIGN.md D6 (movable store) requires.
--
-- SCOPE (Principal, 2026-08-03): general internal task tickets only.
-- No client identifiers, no investment reasoning, no client complaints,
-- no client-report evidence. See REQUIREMENTS.md §8. There is therefore no
-- client_ref column and no encrypted column in V1.
-- =============================================================================

-- gen_random_uuid() is core from Postgres 13 on; no pgcrypto needed.

-- -----------------------------------------------------------------------------
-- Roles
--
-- crm_app is the ONLY role the application uses to serve a user request.
-- It is deliberately not the table owner, because RLS does not apply to a
-- table's owner unless forced, and "we forced it" is a weaker guarantee than
-- "the runtime role never owned anything".
-- -----------------------------------------------------------------------------
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'crm_app') then
    create role crm_app nologin;
  end if;
end $$;

create schema if not exists app;

-- -----------------------------------------------------------------------------
-- The acting employee, or NULL when unset. NULL makes every policy fail closed.
--
-- Defined here because it touches no table. The helpers that DO read `employees`
-- are declared after that table exists: a `language sql` body is parsed and
-- validated at CREATE time (unlike plpgsql, which resolves names lazily), so a
-- forward reference to a missing relation is a hard error, not a warning.
-- -----------------------------------------------------------------------------
create or replace function app.current_employee() returns uuid
  language sql stable
as $$
  select nullif(current_setting('app.employee_id', true), '')::uuid;
$$;

-- -----------------------------------------------------------------------------
-- employees
--
-- Never hard-deleted. Deactivation preserves attribution: a punch from 2027 must
-- still name who wrote it in 2031, so the row survives the person leaving.
-- work_email is the join key to Cloudflare Access identity, stored lowercase.
-- -----------------------------------------------------------------------------
create table if not exists employees (
  id             uuid primary key default gen_random_uuid(),
  work_email     text not null unique
                   check (work_email = lower(work_email) and position('@' in work_email) > 1),
  display_name   text not null check (length(trim(display_name)) > 0),
  role           text not null default 'EMPLOYEE'
                   check (role in ('EMPLOYEE', 'MANAGER', 'ADMIN')),
  manager_id     uuid references employees(id) on delete set null,
  status         text not null default 'ACTIVE'
                   check (status in ('ACTIVE', 'DEACTIVATED')),
  created_at     timestamptz not null default now(),
  deactivated_at timestamptz,
  deactivated_reason text,
  -- A person cannot manage themselves.
  constraint employees_no_self_manage check (manager_id is null or manager_id <> id),
  -- Deactivation must be explained; an unexplained one is indistinguishable
  -- from an accident.
  constraint employees_deactivation_complete check (
    (status = 'ACTIVE'      and deactivated_at is null and deactivated_reason is null)
    or
    (status = 'DEACTIVATED' and deactivated_at is not null
                            and coalesce(length(trim(deactivated_reason)), 0) > 0)
  )
);

create index if not exists employees_manager_idx on employees(manager_id);
create index if not exists employees_status_idx  on employees(status);

-- -----------------------------------------------------------------------------
-- Identity helpers that read `employees`
--
-- SECURITY DEFINER so they can read the table without re-entering the RLS
-- policies that are themselves written in terms of these functions. Without it,
-- every policy on `employees` would recurse.
--
-- A deactivated employee resolves to no role, so `is_admin()` and every policy
-- built on it fail closed the moment someone is offboarded.
-- -----------------------------------------------------------------------------
create or replace function app.current_role_name() returns text
  language sql stable security definer set search_path = public, pg_temp
as $$
  select e.role
  from employees e
  where e.id = app.current_employee()
    and e.status = 'ACTIVE';
$$;

create or replace function app.is_admin() returns boolean
  language sql stable security definer set search_path = public, pg_temp
as $$
  select coalesce(app.current_role_name() = 'ADMIN', false);
$$;

-- Is the acting employee the line manager of `subject`?
create or replace function app.manages(subject uuid) returns boolean
  language sql stable security definer set search_path = public, pg_temp
as $$
  select exists (
    select 1 from employees e
    where e.id = subject
      and e.manager_id = app.current_employee()
  );
$$;

-- -----------------------------------------------------------------------------
-- categories · holidays · settings
-- -----------------------------------------------------------------------------
create table if not exists categories (
  id     uuid primary key default gen_random_uuid(),
  name   text not null unique check (length(trim(name)) > 0),
  active boolean not null default true
);

-- Admin-maintained. Deliberately not fed by an external API: a holiday list
-- that silently goes stale corrupts every deadline and staleness calculation.
create table if not exists holidays (
  holiday_date date primary key,
  name         text not null check (length(trim(name)) > 0)
);

create table if not exists settings (
  key   text primary key,
  value jsonb not null
);

-- -----------------------------------------------------------------------------
-- ticket_counters — per-year reference allocation
--
-- A table rather than a sequence per year: `insert ... on conflict do update
-- returning` is atomic, needs no DDL at runtime, and dumps/restores cleanly.
-- References are never reused, including for cancelled tickets, because people
-- quote them in email.
-- -----------------------------------------------------------------------------
create table if not exists ticket_counters (
  year     int primary key check (year between 2000 and 9999),
  last_seq int not null default 0 check (last_seq >= 0)
);

-- -----------------------------------------------------------------------------
-- tickets
--
-- original_deadline is set once and enforced immutable by trigger below. It is
-- the only honest basis for an on-time metric: if the promised date can be
-- edited, the metric measures nothing.
-- -----------------------------------------------------------------------------
create table if not exists tickets (
  id                uuid primary key default gen_random_uuid(),
  ref               text not null unique check (ref ~ '^TKT-[0-9]{4}-[0-9]{4,}$'),
  title             text not null check (length(trim(title)) > 0),
  description       text not null default '',
  category_id       uuid references categories(id) on delete set null,
  priority          text not null check (priority in ('P1', 'P2', 'P3')),
  assignee_id       uuid not null references employees(id),
  raiser_id         uuid not null references employees(id),
  status            text not null default 'OPEN'
                      check (status in ('OPEN', 'IN_PROGRESS', 'BLOCKED', 'DONE', 'CANCELLED')),
  deadline          date not null,
  original_deadline date not null,
  created_at        timestamptz not null default now(),
  closed_at         timestamptz,
  closed_date       date,
  cancel_reason     text,
  -- Terminal states must record when they happened; non-terminal must not.
  constraint tickets_closure_consistent check (
    (status in ('DONE', 'CANCELLED') and closed_at is not null and closed_date is not null)
    or
    (status not in ('DONE', 'CANCELLED') and closed_at is null and closed_date is null)
  ),
  constraint tickets_cancel_reason check (
    status <> 'CANCELLED' or coalesce(length(trim(cancel_reason)), 0) > 0
  )
);

create index if not exists tickets_assignee_idx on tickets(assignee_id);
create index if not exists tickets_raiser_idx   on tickets(raiser_id);
create index if not exists tickets_status_idx   on tickets(status);
-- Supports the commonest query in the app: my open work, soonest deadline first.
create index if not exists tickets_open_deadline_idx
  on tickets(assignee_id, deadline)
  where status not in ('DONE', 'CANCELLED');

create table if not exists ticket_watchers (
  ticket_id   uuid not null references tickets(id) on delete cascade,
  employee_id uuid not null references employees(id) on delete cascade,
  primary key (ticket_id, employee_id)
);

create index if not exists ticket_watchers_employee_idx on ticket_watchers(employee_id);

-- -----------------------------------------------------------------------------
-- status_updates — THE PUNCH TABLE
--
-- Append-only. Enforced in 0002 by revoking UPDATE/DELETE from every role and
-- by a statement trigger, not by application discipline.
--
-- A correction is a NEW row pointing at the row it corrects. The original stays
-- visible forever, displayed beside its correction.
-- -----------------------------------------------------------------------------
create table if not exists status_updates (
  id                 uuid primary key default gen_random_uuid(),
  seq                bigserial not null unique,
  ticket_id          uuid not null references tickets(id),
  actor_id           uuid not null references employees(id),
  created_at         timestamptz not null default now(),
  punch_date         date not null,
  status             text not null
                       check (status in ('OPEN', 'IN_PROGRESS', 'BLOCKED', 'DONE', 'CANCELLED')),
  note               text not null default '',
  blocked_reason     text,
  minutes_spent      int check (minutes_spent is null or minutes_spent between 0 and 1440),
  next_action        text,
  next_action_by     date,
  corrects_update_id uuid references status_updates(id),
  -- REQUIREMENTS §4: a note is mandatory when reporting a blocker. "Blocked"
  -- with no reason is the least useful row in the system.
  constraint status_updates_blocked_needs_reason check (
    status <> 'BLOCKED' or coalesce(length(trim(blocked_reason)), 0) > 0
  ),
  constraint status_updates_no_self_correct check (
    corrects_update_id is null or corrects_update_id <> id
  )
);

create index if not exists status_updates_ticket_idx  on status_updates(ticket_id, seq);
create index if not exists status_updates_actor_idx   on status_updates(actor_id);
create index if not exists status_updates_corrects_idx on status_updates(corrects_update_id);

-- -----------------------------------------------------------------------------
-- deadline_changes
--
-- REQUIREMENTS §5: moving a deadline needs a reason, a preceding punch, and
-- manager approval. The preceding-punch rule is enforced in application code
-- (it needs the punch's own semantics) but the reason and approval are here.
-- -----------------------------------------------------------------------------
create table if not exists deadline_changes (
  id           uuid primary key default gen_random_uuid(),
  ticket_id    uuid not null references tickets(id),
  from_date    date not null,
  to_date      date not null,
  reason       text not null check (length(trim(reason)) > 0),
  requested_by uuid not null references employees(id),
  requested_at timestamptz not null default now(),
  decision     text not null default 'PENDING'
                 check (decision in ('PENDING', 'APPROVED', 'REJECTED')),
  approved_by  uuid references employees(id),
  decided_at   timestamptz,
  constraint deadline_changes_decided check (
    (decision = 'PENDING'  and approved_by is null     and decided_at is null)
    or
    (decision <> 'PENDING' and approved_by is not null and decided_at is not null)
  ),
  constraint deadline_changes_moves check (from_date <> to_date)
);

create index if not exists deadline_changes_ticket_idx on deadline_changes(ticket_id);
create index if not exists deadline_changes_pending_idx
  on deadline_changes(decision) where decision = 'PENDING';

-- -----------------------------------------------------------------------------
-- audit_log — hash-chained, append-only
--
-- Hashes are computed by the application (src/domain/hash-chain.ts, 29 tests)
-- rather than in SQL, for two reasons: it avoids depending on pgcrypto being
-- present in every target (PGlite included), and it keeps one tested
-- implementation instead of two that must agree byte-for-byte.
--
-- Insert ordering is serialised by a transaction-scoped advisory lock in the
-- application writer, so two concurrent inserts cannot read the same chain head.
-- -----------------------------------------------------------------------------
create table if not exists audit_log (
  seq         bigserial primary key,
  occurred_at timestamptz not null default now(),
  actor_id    uuid references employees(id),
  action      text not null check (length(trim(action)) > 0),
  entity      text not null check (length(trim(entity)) > 0),
  entity_id   text,
  payload     jsonb not null default '{}'::jsonb,
  prev_hash   bytea not null check (octet_length(prev_hash) = 32),
  row_hash    bytea not null check (octet_length(row_hash) = 32)
);

create index if not exists audit_log_entity_idx on audit_log(entity, entity_id);
create index if not exists audit_log_actor_idx  on audit_log(actor_id);

-- -----------------------------------------------------------------------------
-- access_events — CSCRF PR.AA guideline 1(e)
--
-- "not less than two (2) years (atleast 6 months in online mode and rest in
-- archival mode)", mandatory for all SEBI regulated entities and not exempted.
--
-- Separate from audit_log on purpose: this answers "who looked at what", is far
-- higher volume, is not hash-chained, and is aged into the encrypted backup at
-- six months to stay inside the 500 MB free database. Merging the two would
-- either bloat the chain or under-retain the audit trail.
-- -----------------------------------------------------------------------------
create table if not exists access_events (
  seq         bigserial primary key,
  occurred_at timestamptz not null default now(),
  employee_id uuid references employees(id),
  event       text not null
                check (event in ('LOGIN', 'VIEW', 'LIST', 'EXPORT', 'ADMIN_ACTION', 'DENIED')),
  entity      text,
  entity_id   text,
  ip          inet,
  user_agent  text,
  -- Set when the row has been written to the encrypted archive and is eligible
  -- to be pruned from the hot table.
  archived_at timestamptz
);

create index if not exists access_events_employee_idx on access_events(employee_id, occurred_at);
create index if not exists access_events_occurred_idx on access_events(occurred_at);
create index if not exists access_events_unarchived_idx
  on access_events(occurred_at) where archived_at is null;

-- =============================================================================
-- Immutability triggers
-- =============================================================================

-- original_deadline is write-once. REQUIREMENTS §5.
create or replace function forbid_original_deadline_change() returns trigger
  language plpgsql as $$
begin
  if new.original_deadline is distinct from old.original_deadline then
    raise exception
      'original_deadline is immutable (ticket %): promised dates cannot be rewritten', old.ref
      using errcode = 'check_violation';
  end if;
  return new;
end $$;

drop trigger if exists tickets_original_deadline_immutable on tickets;
create trigger tickets_original_deadline_immutable
  before update on tickets
  for each row execute function forbid_original_deadline_change();

-- The ticket reference is also write-once: people quote it externally.
create or replace function forbid_ref_change() returns trigger
  language plpgsql as $$
begin
  if new.ref is distinct from old.ref then
    raise exception 'ticket ref is immutable (was %, tried %)', old.ref, new.ref
      using errcode = 'check_violation';
  end if;
  return new;
end $$;

drop trigger if exists tickets_ref_immutable on tickets;
create trigger tickets_ref_immutable
  before update on tickets
  for each row execute function forbid_ref_change();

-- A raiser cannot be reassigned; it is part of the ticket's provenance.
create or replace function forbid_raiser_change() returns trigger
  language plpgsql as $$
begin
  if new.raiser_id is distinct from old.raiser_id then
    raise exception 'raiser_id is immutable (ticket %)', old.ref
      using errcode = 'check_violation';
  end if;
  return new;
end $$;

drop trigger if exists tickets_raiser_immutable on tickets;
create trigger tickets_raiser_immutable
  before update on tickets
  for each row execute function forbid_raiser_change();
