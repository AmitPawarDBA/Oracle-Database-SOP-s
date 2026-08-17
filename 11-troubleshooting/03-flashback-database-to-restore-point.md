# SOP: Using Flashback Database to Restore Point (Logical Error Recovery)

**Category:** Troubleshooting / Backup & Recovery
**Applies to:** Oracle 19c / 21c, Single Instance and RAC, Linux x86-64
**Risk Level:** Critical — this operation rewinds the entire database and
requires `RESETLOGS`; it discards all transactions after the target
point, and every downstream standby/replication target is affected
**Estimated Duration:** 15–60 minutes, depending on flashback window size
and I/O throughput (time is proportional to the volume of changes being
undone, not the size of the database)
**Downtime Required:** Yes — the database must be closed
(`SHUTDOWN IMMEDIATE` / mount) for the duration of the flashback operation
**Owner:** DBA Team
**Last Reviewed:** 2026-08-16
**Review Cadence:** Every 6 months, and after any Data Guard topology
change

---

## 1. Purpose

Provides the procedure to recover a database from a logical error (bad
batch job, accidental `DROP`/mass `DELETE`/`UPDATE`, failed application
deployment that corrupted data) using Flashback Database, which is
typically dramatically faster than a full RMAN restore + recovery because
it only undoes the changes since the target point rather than restoring
every datafile from backup.

## 2. Scope

Covers configuring Flashback Database, creating and using guaranteed
restore points, and executing `FLASHBACK DATABASE TO RESTORE POINT` (or
`TO TIMESTAMP`/`TO SCN`). Applies to Production and Non-Prod databases
with Flashback Database enabled. Does **not** cover PDB-level flashback
in a multitenant environment (procedure is similar but scoped to
`ALTER SESSION SET CONTAINER`), and does **not** apply when a datafile has
been **physically lost or corrupted at the storage level** — Flashback
Database can only undo logical changes recorded in flashback logs; it
cannot recreate a datafile that no longer exists on disk. For that
scenario, use `07-backup-recovery/02-rman-restore-recovery.md` instead.

## 3. Prerequisites

- [ ] Database in `ARCHIVELOG` mode
- [ ] Flashback Database enabled (`FLASHBACK_ON = YES` in
      `v$database`) — see Section 4 to verify, Section 5.1 to enable if
      not already on
- [ ] Fast Recovery Area (`db_recovery_file_dest`) sized with enough
      headroom for flashback logs in addition to backups/archivelogs —
      undersized FRA is the most common cause of flashback logs aging out
      before they're needed
- [ ] `db_flashback_retention_target` set to cover the realistic window
      in which a logical error might be discovered (default 1440 minutes
      / 1 day — increase for slower-to-detect errors)
- [ ] A guaranteed restore point created **before** the risky operation
      (deployment, batch job, migration) whenever this is a planned
      safety net; for unplanned incidents, confirm the target
      SCN/timestamp/restore point is still within the flashback window
- [ ] Change ticket / approval for Production — this is a database-wide
      outage and data-loss-inducing operation (all changes after the
      target point are discarded for every session, not just the one
      that caused the error)
- [ ] Confirmed list of all downstream standby/Data Guard/replication
      targets and a plan for each (see Section 5.5)
- [ ] Application teams notified of the planned outage window and the
      fact that any transactions committed after the target point will
      be lost

## 4. Pre-Checks

```sql
-- Confirm archivelog mode and current flashback status
SELECT log_mode FROM v$database;
SELECT flashback_on FROM v$database;

-- Confirm flashback retention target and current oldest flashback SCN/time
SHOW PARAMETER db_flashback_retention_target;
SELECT oldest_flashback_scn, oldest_flashback_time
FROM v$flashback_database_log;

-- Confirm FRA has headroom (flashback logs live here)
SELECT name, space_limit/1024/1024/1024 AS gb_limit,
       space_used/1024/1024/1024 AS gb_used
FROM v$recovery_file_dest;

-- List available restore points
SELECT name, scn, time, guarantee_flashback_database, storage_size
FROM v$restore_point
ORDER BY scn;
```

Expected: `FLASHBACK_ON = YES`, `oldest_flashback_time` older than your
target recovery point, and a restore point (or a target SCN/timestamp
within the flashback window) available.

## 5. Procedure

### 5.1 Enable Flashback Database (if not already on)

One-time setup per database — skip if `v$database.flashback_on = YES`.

```sql
-- FRA must be configured first
ALTER SYSTEM SET db_recovery_file_dest_size = 200G SCOPE=BOTH;
ALTER SYSTEM SET db_recovery_file_dest = '/u03/fra' SCOPE=BOTH;

-- Set the retention target (minutes) — how far back flashback can go
ALTER SYSTEM SET db_flashback_retention_target = 2880 SCOPE=BOTH; -- 48h

SHUTDOWN IMMEDIATE;
STARTUP MOUNT;
ALTER DATABASE FLASHBACK ON;
ALTER DATABASE OPEN;
```

### 5.2 Create a guaranteed restore point before a risky operation

Use this proactively before deployments, migrations, or batch jobs with a
meaningful risk of a logical error, so recovery is a fast flashback
rather than a full restore:

```sql
CREATE RESTORE POINT before_release_2026_08_16
  GUARANTEE FLASHBACK DATABASE;

-- Confirm it was created
SELECT name, scn, time, guarantee_flashback_database
FROM v$restore_point;
```

> **Risk callout:** a guaranteed restore point retains flashback/redo
> data indefinitely until explicitly dropped — it does **not** age out
> like the normal flashback retention window and will consume FRA space
> continuously. Drop it as soon as it is no longer needed
> (`DROP RESTORE POINT before_release_2026_08_16;`) once the deployment is
> confirmed successful.

### 5.3 Perform the flashback (incident response)

```bash
# oracle OS user
export ORACLE_HOME=/u01/app/oracle/product/19.0.0/dbhome_1
export ORACLE_SID=<SID>
```

```sql
-- 1. Take the database down cleanly
SHUTDOWN IMMEDIATE;

-- 2. Mount (flashback requires MOUNT, not OPEN)
STARTUP MOUNT;

-- 3a. Flash back to a named restore point (preferred — explicit, safe)
FLASHBACK DATABASE TO RESTORE POINT before_release_2026_08_16;

-- 3b. Or flash back to a specific SCN identified from the incident
-- timeline (e.g. via LogMiner/audit trail investigation)
FLASHBACK DATABASE TO SCN 123456789;

-- 3c. Or flash back to a timestamp (least precise — Oracle rounds to
-- the nearest available flashback log boundary; prefer SCN or restore
-- point when precision matters)
FLASHBACK DATABASE TO TIMESTAMP
  TO_TIMESTAMP('2026-08-16 08:55:00', 'YYYY-MM-DD HH24:MI:SS');
```

> **Point of no return:** the following step, `OPEN RESETLOGS`, commits
> you to the flashback outcome. Before opening, verify the flashback
> landed at the correct point (Section 6) — if it's wrong, you can
> `FLASHBACK DATABASE` again (further back or forward, as long as still
> within the flashback window and no `RESETLOGS` has occurred yet)
> without needing a restore. Once you open resetlogs, a new incarnation
> begins and returning to a point *after* the flashback target (i.e.
> "undoing the flashback") requires restoring from backup, not another
> flashback.

```sql
-- 4. Open read-only first to validate data before committing to resetlogs
ALTER DATABASE OPEN READ ONLY;
-- ... run validation queries here (Section 6) ...

-- 5. Once validated, mount again and open with resetlogs to commit
SHUTDOWN IMMEDIATE;
STARTUP MOUNT;
ALTER DATABASE OPEN RESETLOGS;
```

### 5.4 Post-flashback cleanup

```sql
-- Drop the guaranteed restore point once recovery is confirmed
-- successful (it is no longer valid as a flashback target after
-- resetlogs regardless, but should be dropped to release FRA space)
DROP RESTORE POINT before_release_2026_08_16;

-- Take a fresh Level 0 backup immediately — prior backups now belong to
-- a superseded incarnation and are not usable for point-in-time recovery
-- past this point without incarnation-aware RMAN handling
RMAN> BACKUP INCREMENTAL LEVEL 0 DATABASE PLUS ARCHIVELOG;
```

### 5.5 Downstream standby / Data Guard impact

> **Risk callout:** flashing back a primary database breaks redo
> continuity with every physical standby unless the standby is also
> flashed back to the same point (or rebuilt). Do not skip this step —
> an out-of-sync standby will fail managed recovery or, worse, silently
> diverge.

For each physical standby:

```sql
-- On the standby: if Flashback Database is enabled there too, flash it
-- back to the SAME restore point/SCN as the primary
SHUTDOWN IMMEDIATE;
STARTUP MOUNT;
FLASHBACK DATABASE TO RESTORE POINT before_release_2026_08_16;
STARTUP; -- mount, then resume managed recovery once primary resetlogs
```

If the standby does **not** have Flashback Database enabled, or has
already applied redo past the flashback point in a way that cannot be
reconciled, it must be **rebuilt from a fresh backup of the primary**
(post-resetlogs) — do not attempt to nurse a diverged standby back into
sync. Logical standby and downstream replication (GoldenGate, etc.)
targets generally cannot be "flashed back" at all and require a full
resync/re-instantiation after a primary flashback.

## 6. Validation / Post-Checks

```sql
-- Confirm the database opened in the new (post-flashback) incarnation
SELECT current_scn, resetlogs_time FROM v$database;
SELECT incarnation#, resetlogs_change#, status
FROM v$database_incarnation
ORDER BY incarnation# DESC;

-- Validate the specific data that was corrupted — application/table
-- specific, but always confirm the erroneous change is gone AND that
-- legitimate transactions before the target point are intact
SELECT COUNT(*) FROM <affected_table> WHERE <condition_from_incident>;
```

- [ ] `resetlogs_time` matches the expected flashback target window
- [ ] The specific logical error (bad rows/dropped data) is confirmed
      resolved via application/table-level spot checks
- [ ] No unexpected data loss beyond the intended rollback window
      confirmed with the application team
- [ ] All physical standbys flashed back or rebuilt and managed recovery
      resumed and current
- [ ] Fresh Level 0 backup taken post-resetlogs
- [ ] Guaranteed restore point dropped (unless intentionally retained for
      a follow-up window)

## 7. Rollback Plan

1. **Before `OPEN RESETLOGS`:** if validation (read-only open) shows the
   flashback target was wrong, simply re-run
   `FLASHBACK DATABASE TO ...` with a different SCN/timestamp/restore
   point from mount — no data has been committed to a new incarnation
   yet, so this is fully reversible.
2. **After `OPEN RESETLOGS`:** the flashback is committed. To undo it
   (return to the state just before the flashback, i.e. re-apply the
   transactions that were rolled back), you must restore from a backup
   taken before the flashback and perform point-in-time recovery to just
   before the flashback SCN — the guaranteed restore point itself (if
   still present, retained data up to `RESETLOGS`) or standard RMAN
   restore both work; follow
   `07-backup-recovery/02-rman-restore-recovery.md`.
3. If a downstream standby fails to reconcile per Section 5.5, do not
   attempt ad hoc redo application — rebuild it from a post-resetlogs
   primary backup.

## 8. Communication

This is a Production outage with guaranteed data loss for any
transaction after the target point — requires change approval and a
defined maintenance window before execution (except in an active-incident
emergency, where verbal/ticket approval from the incident commander
suffices, followed by a retroactive change record). Notify all
application teams before starting (what will be lost) and immediately
after `OPEN RESETLOGS` completes (database back online, confirm what data
was restored to). Data Guard/DR team must be looped in before starting so
standby remediation (Section 5.5) is planned, not discovered afterward.

## 9. Known Issues / Gotchas

- Flashback Database **cannot** undo a datafile that was physically
  dropped, deleted, or lost (shrink/drop tablespace, storage-level
  corruption, deleted OS file) — only the controlfile entry can be
  handled by flashback in some drop-tablespace edge cases; a genuinely
  missing datafile requires RMAN restore
  (`07-backup-recovery/02-rman-restore-recovery.md`).
- Flashback Database cannot be used across a `NOLOGGING` operation
  boundary safely — data changed by `NOLOGGING` operations within the
  flashback window may not be recoverable/consistent; verify no
  `NOLOGGING` direct-path loads occurred in the window before relying on
  flashback for that period.
- Guaranteed restore points prevent flashback logs from aging out, which
  means FRA space consumption is effectively unbounded until the restore
  point is dropped — monitor FRA usage closely while one exists (cross
  reference `11-troubleshooting/04-diagnosing-archiver-stuck-fra-full.md`
  if the FRA fills up as a result).
- On a standby with a guaranteed restore point, an RVWR I/O error causes
  the **instance to fail** (rather than degrade); without a guaranteed
  restore point, RVWR retries and managed recovery may simply suspend —
  know which mode you're in before troubleshooting a stalled standby.
- `FLASHBACK DATABASE TO TIMESTAMP` rounds to the nearest flashback log
  boundary, not the exact second — for a precise cutover, identify the
  exact SCN first (e.g. via LogMiner on the point of the incident) and
  use `TO SCN`.

## 10. References

- Verified against docs.oracle.com Backup and Recovery User's Guide
  (19c), "Using Flashback Database and Restore Points" — `CREATE RESTORE
  POINT ... GUARANTEE FLASHBACK DATABASE` syntax, `FLASHBACK DATABASE TO
  RESTORE POINT`/`TO SCN`/`TO TIMESTAMP` syntax, enable procedure
  (`db_recovery_file_dest`, `db_flashback_retention_target`, mount,
  `ALTER DATABASE FLASHBACK ON`), and standby RVWR I/O error behavior with
  and without guaranteed restore points,
  https://docs.oracle.com/en/database/oracle/oracle-database/19/bradv/using-flasback-database-restore-points.html
- Verified against docs.oracle.com SQL Language Reference — `FLASHBACK
  DATABASE` statement syntax,
  https://docs.oracle.com/en/database/oracle/oracle-database/18/sqlrf/FLASHBACK-DATABASE.html
- Verified against docs.oracle.com Reference — `DB_FLASHBACK_RETENTION_TARGET`
  parameter (default 1440 minutes),
  https://docs.oracle.com/en/database/oracle/oracle-database/21/refrn/DB_FLASHBACK_RETENTION_TARGET.html
- Oracle Database Reference — `V$FLASHBACK_DATABASE_LOG`,
  `V$RESTORE_POINT`, `V$DATABASE_INCARNATION`
- Internal: `07-backup-recovery/01-rman-backup-strategy.md`
- Internal: `07-backup-recovery/02-rman-restore-recovery.md`

## 11. Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-08-16 | DBA Team | Initial version |
