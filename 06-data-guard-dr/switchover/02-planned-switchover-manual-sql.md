# SOP: Planned Switchover (Primary ↔ Physical Standby) — Manual SQL*Plus (No Broker)

**Category:** Data Guard / Disaster Recovery — Switchover

**Applies to:** Oracle 19c / 21c, Single-instance or RAC, physical
standby in either a Data Guard Broker or non-Broker configuration,
Linux x86-64

**Risk Level:** High — role reversal of production database; incorrect
execution can cause a full outage or data loss if health checks are
skipped.

**Estimated Duration:** 30–60 minutes (execution) + agreed application
quiesce window

**Downtime Required:** Yes — brief application write-outage during the
role transition, typically 2–10 minutes depending on redo apply state and
number of application connections to drain.

**Owner:** DBA Team

**Last Reviewed:** 2026-08-16

**Review Cadence:** Every 6 months, and after any DR test cycle

---

## 1. Purpose

Defines the controlled, zero-data-loss procedure to switch the primary
and standby roles of a Data Guard configuration using direct SQL*Plus
commands, for use when the Data Guard Broker is not configured, is
temporarily unavailable, or when specific tooling/scripting requires the
legacy two-step commit sequence rather than a single Broker command.

## 2. Scope

Covers **planned** switchover of a two-member configuration (one
primary, one physical standby) using SQL*Plus, in either the modern
single-command form (`ALTER DATABASE SWITCHOVER TO`, 12c+, recommended)
or the legacy two-step `COMMIT TO SWITCHOVER` form (still valid; used as
a fallback for older tooling or specific version requirements). Does
**not** cover unplanned/emergency failover (see
`06-data-guard-dr/failover/02-emergency-failover-manual-sql.md`) or
logical standby switchover. If the Data Guard Broker is configured and
reachable, prefer
`06-data-guard-dr/switchover/01-planned-switchover-dgmgrl.md` instead —
it is simpler, self-validating, and handles instance startup/shutdown
automatically. Assumes the standby was built per
`06-data-guard-dr/setup/01-configure-physical-standby.md`.

## 3. Prerequisites

- [ ] Change ticket approved and maintenance window agreed with
      application owners
- [ ] Both databases confirmed healthy and reachable via SQL*Plus (SYS)
- [ ] Apply lag and transport lag confirmed near zero for a sustained
      period leading up to the window (not just at the instant of check)
- [ ] No unresolved archive gaps (`v$archive_gap` empty on standby)
- [ ] Backups current on the primary (pre-switchover safety net)
- [ ] Application connection strategy confirmed: TNS alias/SCAN
      listener/service using role-based routing, or manual
      cutover/DNS change plan documented
- [ ] Application team ready to quiesce/drain connections at the agreed
      time, or confirmed use of Fast Application Notification/TAF/
      Application Continuity so no manual drain is required
- [ ] Rollback (switch-back) criteria and decision owner agreed in
      advance — who calls it, and at what elapsed time/error condition
- [ ] Communication sent to stakeholders with start time and expected
      duration
- [ ] Decided in advance which method (modern single-command vs. legacy
      two-step) will be used, and why, if not the default modern method

## 4. Pre-Checks

Connect to the current primary and standby directly:

```bash
export ORACLE_HOME=/u01/app/oracle/product/19.0.0/dbhome_1
export ORACLE_SID=ORCLPRD
sqlplus / as sysdba
```

```sql
-- On primary: confirm role and switchover readiness
SELECT database_role, open_mode, switchover_status FROM v$database;
-- Expect: PRIMARY / READ WRITE / TO STANDBY (or SESSIONS ACTIVE)
```

```sql
-- On standby (ORCLPRD_DR): confirm role, lag, and readiness
SELECT database_role, open_mode, switchover_status FROM v$database;
-- Expect: PHYSICAL STANDBY / MOUNTED / TO PRIMARY (or SESSIONS ACTIVE)

SELECT name, value, unit FROM v$dataguard_stats
WHERE name IN ('apply lag','transport lag');

-- Confirm no archive gap
SELECT * FROM v$archive_gap;

-- Confirm managed recovery is active
SELECT process, status, sequence# FROM v$managed_standby WHERE process LIKE 'MRP%';

-- On primary: confirm no long-running/uncommitted distributed transactions
SELECT COUNT(*) FROM dba_2pc_pending;
```

Expected: `switchover_status` of `TO STANDBY` (primary) / `TO PRIMARY`
(standby) — either value, or `SESSIONS ACTIVE` (which requires the
`WITH SESSION SHUTDOWN` clause on the legacy method, or is handled
automatically by the modern single-command method), confirms the
database believes a switchover is currently possible. Any other value
(e.g. `NOT ALLOWED`, `RESOLVABLE GAP`) means switchover will fail —
resolve first (see Section 9). Apply/transport lag must be `0` or
trivially small and not growing; `v$archive_gap` must return no rows.

## 5. Procedure

Choose **one** of the two methods below. The modern single-command
method (5.1) is recommended for all 12c+ databases; the legacy two-step
method (5.2) remains valid and is documented as a fallback.

### 5.1 Modern Method — Single-Command Switchover (12c+, recommended)

Introduced in Oracle Database 12c, `ALTER DATABASE SWITCHOVER TO`
orchestrates the entire role transition — final log shipping, role
reversal on both databases, and completion — from a single command
issued on the **current primary**. It internally performs the
equivalent of the legacy two-step sequence, but Oracle manages the
coordination and reduces the chance of an operator error stranding the
pair mid-transition.

1. Final confirmation with application team that the agreed quiesce
   window has started. If the application does not use transparent
   role-based reconnect (FAN/TAF/Application Continuity), have the app
   team stop new connections/jobs against the primary now.
2. Re-run the readiness check immediately before executing, since state
   can change between pre-checks and execution (repeat the queries in
   Section 4 on both databases).
3. On the **current primary**, execute the switchover, specifying the
   target standby's `db_unique_name` (or `DB_NAME` per the Oracle SQL
   reference, depending on version — `db_unique_name` is the safe choice
   in a Data Guard configuration):
   ```sql
   ALTER DATABASE SWITCHOVER TO ORCLPRD_DR;
   ```
   > **Point of no return:** once this command is accepted and begins
   > executing, the current primary starts final redo shipping and
   > begins converting to a standby role. Do not interrupt the session
   > or kill either instance mid-command — let it complete. If the
   > session is disconnected mid-switchover, reconnect and check
   > `v$database.switchover_status` on both sides before taking any
   > further action; do not blindly reissue the command.
4. The command will, in most 12c+ releases, leave the former primary in
   `MOUNTED` standby role once complete (the instance may need a
   restart to be fully consistent — check the alert log). Confirm and,
   if needed, restart the former primary instance cleanly:
   ```sql
   SHUTDOWN IMMEDIATE;
   STARTUP MOUNT;
   ```
5. On the new primary (`ORCLPRD_DR`), open it for read/write if it did
   not open automatically:
   ```sql
   SELECT database_role, open_mode FROM v$database;
   -- If still MOUNTED:
   ALTER DATABASE OPEN;
   ```

### 5.2 Legacy Method — Two-Step Commit (fallback, older versions/tooling)

Still valid and supported, and required by some older scripting or
version-specific edge cases. Issued as two separate commands, one on
each database, coordinated manually by the DBA.

1. Final confirmation with application team that the agreed quiesce
   window has started, as in 5.1.
2. Re-run the readiness check immediately before executing (Section 4
   queries on both databases).
3. On the **current primary**, commit to switch over to a physical
   standby role. Use `WITH SESSION SHUTDOWN` if `switchover_status`
   showed `SESSIONS ACTIVE` (active sessions need to be disconnected as
   part of the role change):
   ```sql
   ALTER DATABASE COMMIT TO SWITCHOVER TO PHYSICAL STANDBY WITH SESSION SHUTDOWN;
   ```
   > **Point of no return:** once this completes, the former primary is
   > a physical standby and can no longer accept writes. The
   > transition is not complete until Step 4 executes on the target —
   > do not leave the configuration in this intermediate state longer
   > than necessary.
4. Restart the former primary instance and mount it as standby:
   ```sql
   SHUTDOWN IMMEDIATE;
   STARTUP MOUNT;
   ```
5. On the **target standby** (`ORCLPRD_DR`), commit to switch over to
   the primary role:
   ```sql
   ALTER DATABASE COMMIT TO SWITCHOVER TO PRIMARY;
   ```
6. Open the new primary for read/write:
   ```sql
   ALTER DATABASE OPEN;
   ```

### 5.3 Common Steps (Both Methods)

7. If DGMGRL / a Broker configuration exists (even if not used for this
   switchover), reconcile it now so it reflects the actual roles:
   ```
   DGMGRL> SHOW CONFIGURATION;
   ```
   Resolve any warnings before relying on Broker for future operations.
8. Redirect application traffic to the new primary (`ORCLPRD_DR`'s
   listener/service). If using role-based services
   (`ACTIVE_STANDBY`/`PRIMARY` role option on `srvctl add service`),
   confirm this took effect automatically on role change; otherwise
   update the load balancer/DNS/TNS alias now to point at the new
   primary host.
9. Release the application quiesce and allow new connections/writes
   against the new primary.
10. Confirm the new standby (`ORCLPRD`) resumes managed recovery; start
    it manually if it did not:
    ```sql
    ALTER DATABASE RECOVER MANAGED STANDBY DATABASE USING CURRENT LOGFILE DISCONNECT;
    ```

## 6. Validation / Post-Checks

```sql
-- On new primary (ORCLPRD_DR): confirm role and open mode
SELECT database_role, open_mode, db_unique_name FROM v$database;
-- Expect: PRIMARY / READ WRITE / ORCLPRD_DR

-- On new standby (ORCLPRD): confirm role and apply
SELECT database_role, open_mode, db_unique_name FROM v$database;
-- Expect: PHYSICAL STANDBY / MOUNTED / ORCLPRD

SELECT process, status, sequence# FROM v$managed_standby WHERE process LIKE 'MRP%';

-- Confirm redo transport lag on new standby
SELECT name, value, unit FROM v$dataguard_stats WHERE name IN ('apply lag','transport lag');
```

- [ ] `ORCLPRD_DR` reports `database_role = PRIMARY`,
      `open_mode = READ WRITE`
- [ ] `ORCLPRD` reports `database_role = PHYSICAL STANDBY`,
      `open_mode = MOUNTED`, MRP process `APPLYING_LOG`
- [ ] If Broker is configured, `DGMGRL> SHOW CONFIGURATION` returns
      `SUCCESS` with no warnings
- [ ] Application successfully connects, performs a test write, and read
      replicas (if any) resolve to the new primary
- [ ] Monitoring/alerting endpoints updated to point at the new primary's
      identity for backup jobs, AWR/health checks, and paging thresholds
- [ ] Generate a small amount of transaction volume on the new primary
      and confirm it applies on the new standby (`v$dataguard_stats`
      apply lag stays near zero)

## 7. Rollback Plan

Switchover is designed to be reversible — the safest "rollback" is
almost always to **switch back** rather than attempt to force roles
manually.

- **If the switchover command fails before either instance changes
  role** (e.g. `ORA-16405` or similar `switchover_status` errors
  surfaced immediately): no role change has occurred. Resolve the
  underlying issue (Section 9) and re-run from Step 2/Step 2 of the
  chosen method.
- **If the command hangs or fails mid-transition** (one database
  converted, the other did not complete): do not manually issue
  further `ALTER DATABASE` role-change commands against either instance
  until you have checked `v$database.switchover_status` and
  `database_role` on both sides to determine actual state. Then either:
  - Complete the stalled step manually (e.g. `STARTUP MOUNT` the
    instance still down, in the role Oracle expects), or
  - If the new primary is open and healthy but the old primary failed to
    restart as standby, bring it up manually as physical standby
    (`STARTUP MOUNT` then
    `ALTER DATABASE RECOVER MANAGED STANDBY DATABASE USING CURRENT LOGFILE DISCONNECT;`).
- **If the switchover completed successfully but the new primary
  exhibits an application-impacting issue**: perform a second planned
  switchover back to the original primary using this same procedure
  (either method). This is safe because switchover is a symmetric,
  zero-data-loss operation when both databases are healthy.
- **Escalation trigger:** if the configuration cannot be brought back to
  a clean, agreed state (one confirmed primary, one confirmed mounted
  standby applying redo) within 30 minutes of a failed/stalled
  switchover, escalate to the on-call DBA lead and treat as a potential
  failover scenario — do not continue trial-and-error against a
  production database.

## 8. Communication

Send a pre-window notice (T-24h and T-30min) to application owners,
NOC/on-call, and the business stakeholder list with the exact quiesce
window, noting the manual (non-Broker) method is being used and why if
Broker is normally available. Send a completion notice immediately after
Section 6 validation passes, including the new primary's connection
identity. If rollback (switch-back) is invoked, notify the same list
immediately with revised timing.

## 9. Known Issues / Gotchas

- `switchover_status` returning `SESSIONS ACTIVE` on the legacy method
  requires `WITH SESSION SHUTDOWN` on the
  `COMMIT TO SWITCHOVER TO PHYSICAL STANDBY` command, or the command
  will fail — the modern single-command method handles this
  automatically.
- `switchover_status` returning `RESOLVABLE GAP` or `NOT ALLOWED` is
  almost always due to non-zero apply lag, an open RMAN backup job
  holding locks, or a standby redo log sizing mismatch — check
  `v$dataguard_stats` and `v$managed_standby` before retrying.
- Sessions with open transactions on the primary at switchover time are
  forcibly terminated by the role transition; always confirm the
  application quiesce actually stopped write activity, not just new
  connections.
- RAC primaries: only one instance needs to run for switchover, but
  ensure all other instances of the primary RAC database are shut down
  first, or the switchover will not complete cleanly.
- If a Broker configuration exists alongside manual administration,
  reconcile it (`DGMGRL> SHOW CONFIGURATION`) immediately after a manual
  switchover — mixed manual/Broker administration is a common source of
  drift and confusing state on the next operation.
- Do not run switchover during an active RMAN backup or online patching
  window on either database.
- The legacy two-step method leaves a longer window where neither
  database is fully in its final role — prefer the modern single-command
  method unless a specific version/tooling constraint requires the
  legacy path.

## 10. References

- Oracle Data Guard SQL statements reference (19c) —
  https://docs.oracle.com/en/database/oracle/oracle-database/19/sbydb/sql-statements-used-by-oracle-data-guard.html
  — documents both the modern `ALTER DATABASE SWITCHOVER TO` single
  command and the legacy `COMMIT TO SWITCHOVER TO PHYSICAL STANDBY` /
  `COMMIT TO SWITCHOVER TO PRIMARY` two-step sequence.
- MOS Doc ID 1265700.1 — Data Guard switchover best practices
- MOS Doc ID 736755.1 — Data Guard switchover/failover troubleshooting
- Internal: `06-data-guard-dr/switchover/01-planned-switchover-dgmgrl.md`
  (preferred, Broker-based path — use this one whenever DGMGRL is
  reachable)
- Internal: `06-data-guard-dr/setup/01-configure-physical-standby.md`
- Internal: `06-data-guard-dr/failover/02-emergency-failover-manual-sql.md`

## 11. Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-08-16 | DBA Team | Initial version |
