-- =============================================================================
-- 0003_rls.sql — row-level security, grants, and the ticket-ref allocator
--
-- Authorisation lives HERE, not in the UI. A bug in a React component must not
-- be able to show one employee another's tickets, so the database refuses
-- regardless of what the application asks for. This is the defence against
-- IDOR, which is the most likely real bug in an app of this shape.
--
-- WHY NOT `FORCE ROW LEVEL SECURITY`: forcing would apply policies to the table
-- owner too, which breaks migrations, seeding and the archival job. The actual
-- control is stronger and simpler — the runtime role `crm_app` does not own any
-- object, so ordinary RLS binds it. Nothing serving a user request ever connects
-- as the owner.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Ticket reference allocation — atomic, no runtime DDL.
-- -----------------------------------------------------------------------------
create or replace function app.next_ticket_seq(p_year int) returns int
  language plpgsql volatile security definer set search_path = public, pg_temp
as $$
declare
  v_seq int;
begin
  insert into ticket_counters (year, last_seq)
  values (p_year, 1)
  on conflict (year) do update set last_seq = ticket_counters.last_seq + 1
  returning last_seq into v_seq;
  return v_seq;
end $$;

-- -----------------------------------------------------------------------------
-- Visibility helper for a ticket's children.
--
-- SECURITY DEFINER, so it reads `tickets` without re-entering that table's own
-- policy. Used by status_updates / watchers / deadline_changes so the rule
-- exists in exactly one place.
-- -----------------------------------------------------------------------------
create or replace function app.can_see_ticket(p_ticket uuid) returns boolean
  language sql stable security definer set search_path = public, pg_temp
as $$
  select exists (
    select 1
    from tickets t
    where t.id = p_ticket
      and (
        app.is_admin()
        or t.assignee_id = app.current_employee()
        or t.raiser_id   = app.current_employee()
        or app.manages(t.assignee_id)
        or exists (
          select 1 from ticket_watchers w
          where w.ticket_id = t.id and w.employee_id = app.current_employee()
        )
      )
  );
$$;

-- =============================================================================
-- Enable RLS
-- =============================================================================
alter table employees        enable row level security;
alter table categories       enable row level security;
alter table holidays         enable row level security;
alter table settings         enable row level security;
alter table tickets          enable row level security;
alter table ticket_watchers  enable row level security;
alter table status_updates   enable row level security;
alter table deadline_changes enable row level security;
alter table audit_log        enable row level security;
alter table access_events    enable row level security;
alter table ticket_counters  enable row level security;

-- =============================================================================
-- employees — an internal staff directory
--
-- Readable by any signed-in employee: names appear on every ticket, and hiding
-- them would break the UI while protecting nothing (everyone already knows who
-- works here). Writes are admin-only.
-- =============================================================================
drop policy if exists employees_select on employees;
create policy employees_select on employees
  for select using (app.current_employee() is not null);

drop policy if exists employees_admin_write on employees;
create policy employees_admin_write on employees
  for all using (app.is_admin()) with check (app.is_admin());

-- =============================================================================
-- Reference data — readable by all, writable by admin
-- =============================================================================
drop policy if exists categories_select on categories;
create policy categories_select on categories
  for select using (app.current_employee() is not null);
drop policy if exists categories_admin_write on categories;
create policy categories_admin_write on categories
  for all using (app.is_admin()) with check (app.is_admin());

drop policy if exists holidays_select on holidays;
create policy holidays_select on holidays
  for select using (app.current_employee() is not null);
drop policy if exists holidays_admin_write on holidays;
create policy holidays_admin_write on holidays
  for all using (app.is_admin()) with check (app.is_admin());

drop policy if exists settings_select on settings;
create policy settings_select on settings
  for select using (app.current_employee() is not null);
drop policy if exists settings_admin_write on settings;
create policy settings_admin_write on settings
  for all using (app.is_admin()) with check (app.is_admin());

-- =============================================================================
-- tickets
--
-- Predicate inlined rather than calling can_see_ticket(), to avoid a policy
-- defined in terms of a function that reads the same table.
-- =============================================================================
drop policy if exists tickets_select on tickets;
create policy tickets_select on tickets
  for select using (
    app.is_admin()
    or assignee_id = app.current_employee()
    or raiser_id   = app.current_employee()
    or app.manages(assignee_id)
    or exists (
      select 1 from ticket_watchers w
      where w.ticket_id = tickets.id and w.employee_id = app.current_employee()
    )
  );

-- Anyone signed in may raise a ticket, but only ever as themselves. The
-- with-check clause is what stops a forged raiser_id.
drop policy if exists tickets_insert on tickets;
create policy tickets_insert on tickets
  for insert with check (
    app.current_employee() is not null
    and raiser_id = app.current_employee()
  );

-- Assignee, the assignee's manager, and admin may modify. Note the raiser is
-- NOT included: raising work does not confer control over how it is done.
-- Cancellation by the raiser is handled as an explicit admin/manager action.
drop policy if exists tickets_update on tickets;
create policy tickets_update on tickets
  for update using (
    app.is_admin()
    or assignee_id = app.current_employee()
    or app.manages(assignee_id)
  );

-- No delete policy anywhere: tickets are cancelled, never deleted.

-- =============================================================================
-- ticket_watchers
-- =============================================================================
drop policy if exists ticket_watchers_select on ticket_watchers;
create policy ticket_watchers_select on ticket_watchers
  for select using (app.can_see_ticket(ticket_id));

drop policy if exists ticket_watchers_write on ticket_watchers;
create policy ticket_watchers_write on ticket_watchers
  for all using (app.can_see_ticket(ticket_id))
  with check (app.can_see_ticket(ticket_id));

-- =============================================================================
-- status_updates — the punch table
--
-- INSERT only, and only as yourself. There is no update or delete policy
-- because 0002 revoked those privileges outright and traps them in a trigger;
-- omitting the policy here is the third statement of the same rule.
-- =============================================================================
drop policy if exists status_updates_select on status_updates;
create policy status_updates_select on status_updates
  for select using (app.can_see_ticket(ticket_id));

drop policy if exists status_updates_insert on status_updates;
create policy status_updates_insert on status_updates
  for insert with check (
    actor_id = app.current_employee()
    and app.can_see_ticket(ticket_id)
  );

-- =============================================================================
-- deadline_changes
-- =============================================================================
drop policy if exists deadline_changes_select on deadline_changes;
create policy deadline_changes_select on deadline_changes
  for select using (app.can_see_ticket(ticket_id));

drop policy if exists deadline_changes_insert on deadline_changes;
create policy deadline_changes_insert on deadline_changes
  for insert with check (
    requested_by = app.current_employee()
    and app.can_see_ticket(ticket_id)
  );

-- Only a manager of the assignee, or an admin, may decide. Deliberately not the
-- requester: self-approving a deadline move would make the approval meaningless.
drop policy if exists deadline_changes_decide on deadline_changes;
create policy deadline_changes_decide on deadline_changes
  for update using (
    app.is_admin()
    or exists (
      select 1 from tickets t
      where t.id = deadline_changes.ticket_id
        and app.manages(t.assignee_id)
    )
  );

-- =============================================================================
-- audit_log / access_events — admin read only
-- =============================================================================
drop policy if exists audit_log_admin_select on audit_log;
create policy audit_log_admin_select on audit_log
  for select using (app.is_admin());

drop policy if exists access_events_admin_select on access_events;
create policy access_events_admin_select on access_events
  for select using (app.is_admin());

-- Every signed-in request writes its own access row; nobody reads them but admin.
drop policy if exists access_events_insert on access_events;
create policy access_events_insert on access_events
  for insert with check (app.current_employee() is not null);

-- ticket_counters: no policy at all, so RLS denies everything. Access is only
-- ever through app.next_ticket_seq(), which is SECURITY DEFINER.

-- =============================================================================
-- Grants
--
-- RLS filters rows; grants decide which verbs exist at all. Both are required —
-- a policy without a grant is unreachable, and a grant without a policy on an
-- RLS-enabled table returns nothing.
-- =============================================================================
grant usage on schema public, app to crm_app;

grant select                 on employees, categories, holidays, settings to crm_app;
grant select, insert, update  on tickets                                   to crm_app;
grant select, insert, delete  on ticket_watchers                           to crm_app;
grant select, insert          on status_updates                            to crm_app;
grant select, insert, update  on deadline_changes                          to crm_app;
grant select                  on audit_log                                 to crm_app;
grant select, insert          on access_events                             to crm_app;

-- bigserial sequences need explicit usage for INSERT to work.
grant usage on sequence status_updates_seq_seq to crm_app;
grant usage on sequence access_events_seq_seq  to crm_app;

grant execute on function
  app.current_employee(), app.current_role_name(), app.is_admin(),
  app.manages(uuid), app.can_see_ticket(uuid),
  app.next_ticket_seq(int), app.audit_chain_head(), app.audit_next_seq(),
  app.append_audit(bigint, timestamptz, uuid, text, text, text, jsonb, bytea, bytea)
  to crm_app;

-- Admin-only writes to reference data still flow through crm_app, gated by the
-- admin policies above rather than by a separate database role. One connection
-- role keeps the deployment simple; the policy is the boundary.
grant insert, update, delete on employees, categories, holidays, settings to crm_app;
