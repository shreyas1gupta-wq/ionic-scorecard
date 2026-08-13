-- =============================================================================
-- 0005_admin_guards.sql — the four admin invariants the schema did not yet hold
--
-- REQUIREMENTS §2 and §9 state four rules about the people table that 0001–0003
-- left to application discipline. Each is put here instead, for the same reason
-- 0002 put append-only in the database: a rule that lives only in TypeScript is
-- one forgotten call site away from not existing.
--
--   1. Nobody changes their own role.        Privilege escalation is the one
--                                            authorisation bug an admin console
--                                            can introduce that matters.
--   2. Employees are never hard-deleted.     A punch written in 2027 must still
--                                            name its author in 2031.
--   3. Deactivation waits for a handover.    Open work assigned to someone who
--                                            can no longer log in is work lost.
--   4. No management cycles.                 `app.manages()` is used by RLS; a
--                                            cycle makes visibility circular and
--                                            "who approves this" unanswerable.
--
-- ERRCODES ARE PART OF THE INTERFACE. `insufficient_privilege` (42501) is mapped
-- to AuthorizationError by src/repo/postgres.ts and `check_violation` (23514) to
-- ValidationError, so the choice below decides what the user is told. Refusals
-- that are about permission use the former; refusals that are about the state of
-- the data use the latter.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Nobody changes their own role.
--
-- This cannot be an RLS policy: WITH CHECK sees only the new row, and the rule is
-- about the difference between old and new. A row-level trigger is the only place
-- that comparison exists.
--
-- `app.current_employee()` is NULL for migrations, seeding and the archival job,
-- so those are unaffected — the rule binds a signed-in actor, which is precisely
-- who it is aimed at.
-- -----------------------------------------------------------------------------
create or replace function employees_guard_self_role() returns trigger
  language plpgsql as $$
begin
  if new.role is distinct from old.role and old.id = app.current_employee() then
    raise exception
      'you cannot change your own role (%): ask another administrator', old.work_email
      using errcode = 'insufficient_privilege';
  end if;
  return new;
end $$;

drop trigger if exists employees_guard_self_role on employees;
create trigger employees_guard_self_role
  before update on employees
  for each row execute function employees_guard_self_role();

-- -----------------------------------------------------------------------------
-- 2. Employees are never hard-deleted.
--
-- Two layers, matching 0002's reasoning: the revoke narrows 0003's blanket grant,
-- and the trigger holds even if a later migration re-grants it. Statement-level,
-- so `delete ... where false` is refused too — an admin console that reports
-- "0 rows deleted" for a forbidden operation has taught the wrong lesson.
--
-- Nothing in the codebase deletes an employee: `resetTransactionalData` keeps the
-- team, and offboarding is `status = 'DEACTIVATED'`.
-- -----------------------------------------------------------------------------
revoke delete, truncate on employees from public;
revoke delete, truncate on employees from crm_app;

create or replace function employees_forbid_delete() returns trigger
  language plpgsql as $$
begin
  raise exception
    'employees are never deleted: deactivate instead, so past work keeps its author'
    using errcode = 'insufficient_privilege';
end $$;

drop trigger if exists employees_no_delete on employees;
create trigger employees_no_delete
  before delete on employees
  for each statement execute function employees_forbid_delete();

drop trigger if exists employees_no_truncate on employees;
create trigger employees_no_truncate
  before truncate on employees
  for each statement execute function employees_forbid_delete();

-- -----------------------------------------------------------------------------
-- 3. Deactivation waits for the work to be handed over. REQUIREMENTS §9.
--
-- SECURITY DEFINER on purpose: without it the count runs under the caller's RLS
-- policies, and a caller who cannot see a ticket would be told there is no open
-- work when there is. A check that fails open is worse than no check.
-- -----------------------------------------------------------------------------
create or replace function employees_guard_deactivation() returns trigger
  language plpgsql security definer set search_path = public, pg_temp as $$
declare
  v_open int;
begin
  if new.status = 'DEACTIVATED' and old.status <> 'DEACTIVATED' then
    select count(*) into v_open
      from tickets
     where assignee_id = old.id
       and status not in ('DONE', 'CANCELLED');

    if v_open > 0 then
      raise exception
        'reassign % open ticket(s) before deactivating %', v_open, old.work_email
        using errcode = 'check_violation';
    end if;
  end if;
  return new;
end $$;

drop trigger if exists employees_guard_deactivation on employees;
create trigger employees_guard_deactivation
  before update on employees
  for each row execute function employees_guard_deactivation();

-- -----------------------------------------------------------------------------
-- 4. No management cycles.
--
-- Self-management is already a CHECK constraint (0001). The two-step case — A
-- manages B, B manages A — is not expressible as a CHECK, because it depends on
-- another row. Walking the chain upward from the proposed manager is the whole
-- test: if it ever reaches this employee, the edge closes a loop.
--
-- The direct case falls through to that CHECK deliberately. A BEFORE ROW trigger
-- runs before constraints, so raising here would shadow
-- `employees_no_self_manage` and give two different errors for one condition.
-- One condition, one refusal, one message.
--
-- The hop cap is not defensive noise. If corrupt data ever did contain a cycle,
-- an uncapped walk would hang the connection holding a write lock on `employees`,
-- which is a far worse failure than a refused update.
-- -----------------------------------------------------------------------------
create or replace function employees_guard_manager_cycle() returns trigger
  language plpgsql security definer set search_path = public, pg_temp as $$
declare
  v_cursor uuid;
  v_hops   int := 0;
begin
  if new.manager_id = new.id then
    return new;
  end if;

  v_cursor := new.manager_id;
  while v_cursor is not null loop
    if v_cursor = new.id then
      raise exception
        'that would make % manage themselves through the reporting chain', new.work_email
        using errcode = 'check_violation';
    end if;
    v_hops := v_hops + 1;
    if v_hops > 64 then
      raise exception 'reporting chain above % is longer than 64 links', new.work_email
        using errcode = 'check_violation';
    end if;
    select e.manager_id into v_cursor from employees e where e.id = v_cursor;
  end loop;
  return new;
end $$;

drop trigger if exists employees_guard_manager_cycle on employees;
create trigger employees_guard_manager_cycle
  before insert or update on employees
  for each row when (new.manager_id is not null)
  execute function employees_guard_manager_cycle();
