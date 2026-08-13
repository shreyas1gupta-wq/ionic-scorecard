-- =============================================================================
-- 0002_append_only.sql — the guarantee everything else rests on
--
-- Three independent layers, because a single layer is a single mistake away
-- from silence:
--
--   1. PRIVILEGE   — UPDATE/DELETE revoked. Note this binds even a role that
--                    bypasses RLS: RLS-bypass is not privilege-bypass.
--   2. TRIGGER     — raises regardless, in case a later migration or a console
--                    session re-grants the privilege.
--   3. TEST        — db/__tests__ attempts both operations as every role and
--                    asserts failure.
--
-- Layer 2 exists specifically because layer 1 is a GRANT away from being undone
-- by someone with good intentions and a deadline.
-- =============================================================================

create or replace function forbid_mutation() returns trigger
  language plpgsql as $$
begin
  raise exception
    'append-only table %.%: % is never permitted. Corrections are new rows.',
    tg_table_schema, tg_table_name, tg_op
    using errcode = 'insufficient_privilege';
end $$;

-- -----------------------------------------------------------------------------
-- status_updates — punches. Absolutely immutable.
-- -----------------------------------------------------------------------------
revoke update, delete, truncate on status_updates from public;
revoke update, delete, truncate on status_updates from crm_app;

drop trigger if exists status_updates_no_update on status_updates;
create trigger status_updates_no_update
  before update on status_updates
  for each statement execute function forbid_mutation();

drop trigger if exists status_updates_no_delete on status_updates;
create trigger status_updates_no_delete
  before delete on status_updates
  for each statement execute function forbid_mutation();

drop trigger if exists status_updates_no_truncate on status_updates;
create trigger status_updates_no_truncate
  before truncate on status_updates
  for each statement execute function forbid_mutation();

-- -----------------------------------------------------------------------------
-- audit_log — the hash chain. Immutable, and INSERT is not granted to the app
-- role either: writes go through app.append_audit() below, which holds the
-- advisory lock that keeps the chain linear.
-- -----------------------------------------------------------------------------
revoke update, delete, truncate on audit_log from public;
revoke update, delete, truncate on audit_log from crm_app;
revoke insert                    on audit_log from public;
revoke insert                    on audit_log from crm_app;

drop trigger if exists audit_log_no_update on audit_log;
create trigger audit_log_no_update
  before update on audit_log
  for each statement execute function forbid_mutation();

drop trigger if exists audit_log_no_delete on audit_log;
create trigger audit_log_no_delete
  before delete on audit_log
  for each statement execute function forbid_mutation();

drop trigger if exists audit_log_no_truncate on audit_log;
create trigger audit_log_no_truncate
  before truncate on audit_log
  for each statement execute function forbid_mutation();

-- -----------------------------------------------------------------------------
-- Chain-head read + serialised append.
--
-- The advisory lock is the whole point: without it two concurrent transactions
-- both read the same head and produce two rows claiming the same predecessor,
-- which silently forks the chain. The lock is transaction-scoped, so it is
-- released on commit or rollback without any unlock call to forget.
--
-- The hash itself is computed by the caller (src/domain/hash-chain.ts) and
-- verified here only for shape. Recomputing it in SQL would mean two
-- implementations that must agree byte-for-byte forever.
-- -----------------------------------------------------------------------------
create or replace function app.audit_chain_head() returns bytea
  language sql stable security definer set search_path = public, pg_temp
as $$
  select coalesce(
    (select row_hash from audit_log order by seq desc limit 1),
    -- Genesis: 32 zero bytes. Must match GENESIS_HASH in hash-chain.ts.
    '\x0000000000000000000000000000000000000000000000000000000000000000'::bytea
  );
$$;

-- `p_occurred_at` is supplied by the caller and NOT defaulted here. That is
-- deliberate: occurred_at is inside the hash, so if the database stamped its own
-- now() the stored row would not match the hash computed over it, and every
-- verification would fail for a reason nobody could find. The caller hashes and
-- stores the same instant or neither.
--
-- `p_seq` is likewise supplied, because seq is inside the hash too. The advisory
-- lock lets the caller read the next value and use it without a race.
create or replace function app.append_audit(
  p_seq         bigint,
  p_occurred_at timestamptz,
  p_actor_id    uuid,
  p_action      text,
  p_entity      text,
  p_entity_id   text,
  p_payload     jsonb,
  p_prev_hash   bytea,
  p_row_hash    bytea
) returns bigint
  language plpgsql volatile security definer set search_path = public, pg_temp
as $$
declare
  v_head bytea;
  v_next bigint;
  v_seq  bigint;
begin
  -- Serialise all audit appends. Arbitrary but fixed key.
  perform pg_advisory_xact_lock(hashtext('ionic_crm.audit_log'));

  v_head := app.audit_chain_head();
  if v_head is distinct from p_prev_hash then
    raise exception
      'audit chain head moved under caller: expected %, actual %',
      encode(p_prev_hash, 'hex'), encode(v_head, 'hex')
      using errcode = 'serialization_failure';
  end if;

  v_next := app.audit_next_seq();
  if v_next is distinct from p_seq then
    raise exception
      'audit seq mismatch: caller hashed %, next is %', p_seq, v_next
      using errcode = 'serialization_failure';
  end if;

  insert into audit_log (seq, occurred_at, actor_id, action, entity, entity_id,
                         payload, prev_hash, row_hash)
  values (p_seq, p_occurred_at, p_actor_id, p_action, p_entity, p_entity_id,
          coalesce(p_payload, '{}'::jsonb), p_prev_hash, p_row_hash)
  returning seq into v_seq;

  -- Keep the backing sequence ahead of the explicit values we insert, so that
  -- anything relying on the default never collides with a chained row.
  perform setval(pg_get_serial_sequence('audit_log', 'seq'), v_seq);

  return v_seq;
end $$;

-- The seq the next chained row must use. Read under the same advisory lock as
-- the append, so caller and database agree on it.
create or replace function app.audit_next_seq() returns bigint
  language sql stable security definer set search_path = public, pg_temp
as $$
  select coalesce((select max(seq) from audit_log), 0) + 1;
$$;

-- -----------------------------------------------------------------------------
-- access_events — append-only for the app, with one narrow exception.
--
-- The archival job must stamp archived_at, and pruning must eventually delete
-- archived rows, so this table cannot be as absolute as the two above. Instead:
--   * the app role gets INSERT and SELECT only;
--   * any UPDATE may touch archived_at and nothing else;
--   * a row can only be deleted once it has actually been archived.
-- The last rule means a mistaken prune cannot destroy evidence that was never
-- written anywhere else.
-- -----------------------------------------------------------------------------
revoke update, delete, truncate on access_events from public;
revoke update, delete, truncate on access_events from crm_app;

create or replace function access_events_guard_update() returns trigger
  language plpgsql as $$
begin
  if (new.seq, new.occurred_at, new.employee_id, new.event,
      new.entity, new.entity_id, new.ip, new.user_agent)
     is distinct from
     (old.seq, old.occurred_at, old.employee_id, old.event,
      old.entity, old.entity_id, old.ip, old.user_agent) then
    raise exception
      'access_events is append-only except archived_at (seq %)', old.seq
      using errcode = 'insufficient_privilege';
  end if;
  return new;
end $$;

drop trigger if exists access_events_guard_update on access_events;
create trigger access_events_guard_update
  before update on access_events
  for each row execute function access_events_guard_update();

create or replace function access_events_guard_delete() returns trigger
  language plpgsql as $$
begin
  if old.archived_at is null then
    raise exception
      'refusing to delete unarchived access_events row (seq %): archive it first', old.seq
      using errcode = 'insufficient_privilege';
  end if;
  return old;
end $$;

drop trigger if exists access_events_guard_delete on access_events;
create trigger access_events_guard_delete
  before delete on access_events
  for each row execute function access_events_guard_delete();

drop trigger if exists access_events_no_truncate on access_events;
create trigger access_events_no_truncate
  before truncate on access_events
  for each statement execute function forbid_mutation();
