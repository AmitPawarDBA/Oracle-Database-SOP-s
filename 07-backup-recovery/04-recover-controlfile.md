# SOP: Recover a Lost or Corrupted Control File Using RMAN

**Category:** Backup & Recovery
**Applies to:** Oracle 19c / 21c, Single Instance and RAC, Linux x86-64
**Risk Level:** Critical — the database cannot mount without a valid
control file; recovering the wrong copy or restoring under the wrong
DBID can extend the outage significantly
**Estimated Duration:** 10 minutes (multiplexed copy failure, file copy)
to 45 minutes (full RMAN restore from autobackup)
**Downtime Required:** Yes — database must be in NOMOUNT/MOUNT during
recovery; no application access until `ALTER DATABASE OPEN`
**Owner:** DBA Team
**Last Reviewed:** 2026-08-16
**Review Cadence:** Every 6 months, and after every major recovery test

---

## 1. Purpose

Provides the procedure to recover from loss or corruption of one or more
control file copies, covering the fast path (restoring a lost multiplexed
copy from a surviving mirror) and the primary recovery path (RMAN
restore from controlfile autobackup) when all copies are lost.

## 2. Scope

Covers control file recovery for databases that multiplex `CONTROL_FILES`
across at least two locations (the mandated configuration per
`07-backup-recovery/01-rman-backup-strategy.md`) and databases using
RMAN controlfile autobackups. Applies to Production, Non-Prod, and DR.
Does **not** fully detail the manual `CREATE CONTROLFILE` trace-file
method (no-autobackup fallback) — that is cross-referenced in Section 6.4
and documented in full in `11-troubleshooting/`. Does not cover spfile
recovery (see `07-backup-recovery/03-recover-spfile.md`).

## 3. Prerequisites

- [ ] Incident ticket opened (control file loss is Sev1 for Production)
- [ ] Confirmed exactly which control file copy/copies are lost or
      corrupted (Section 4)
- [ ] `ORACLE_SID` and mirrored `CONTROL_FILES` paths confirmed from the
      last known-good spfile/pfile or `v$parameter`
- [ ] DBID available if a full RMAN restore is required and no recovery
      catalog is connected (see
      `07-backup-recovery/03-recover-spfile.md` Section 4 for how to
      determine it)
- [ ] Rollback/abort criteria understood (Section 7)
- [ ] Stakeholder communication sent (Section 8) for anything beyond a
      single-mirror file copy

## 4. Decision Tree — Which Path to Use

```
Are there 2+ multiplexed control file copies configured, and
only ONE (not all) is missing/corrupt, with the instance still
able to reference a surviving copy?
  YES -> Section 6.1 Fast path: simple file copy of a surviving
         mirror (fastest, no RMAN restore needed)
  NO  |
      v
Are ALL control file copies lost/corrupted, but an RMAN
controlfile autobackup (or regular backup) exists?
  YES -> Section 6.2/6.3 RMAN RESTORE CONTROLFILE FROM AUTOBACKUP
  NO  |
      v
No autobackup and no surviving mirror available
  -> Section 6.4 Manual CREATE CONTROLFILE trace-file method
     (cross-reference only — see 11-troubleshooting/)
```

Always prefer the narrowest, fastest recovery: a plain OS file copy of a
surviving multiplexed member is far cheaper than a full RMAN restore and
should be the default first check whenever the database is multiplexed.

## 5. Pre-Checks

```bash
export ORACLE_HOME=/u01/app/oracle/product/19.0.0/dbhome_1
export ORACLE_SID=ORCL
export PATH=$ORACLE_HOME/bin:$PATH
```

```sql
sqlplus / as sysdba

-- Confirm configured control file locations (works if instance is at
-- least NOMOUNT with a readable spfile)
SHOW PARAMETER control_files;

-- If the instance is already down and cannot even start NOMOUNT,
-- check the last known spfile/pfile directly instead:
--   strings $ORACLE_HOME/dbs/spfileORCL.ora | grep -A2 control_files
```

```bash
# Confirm which physical copies are actually present/readable on disk
ls -l /u01/oradata/ORCL/control01.ctl \
      /u02/oradata/ORCL/control02.ctl \
      /u01/app/oracle/fra/ORCL/control03.ctl
```

Typical symptom in the alert log for a lost/corrupt control file:

```
ORA-00210: cannot open the specified control file
ORA-00202: control file: '/u02/oradata/ORCL/control02.ctl'
ORA-27041: unable to open file
```

## 6. Procedure

### 6.1 Fast Path — Restore a Missing Multiplexed Copy by File Copy

Use this when the database is multiplexed across 2+ locations and only
one copy is missing/corrupt while at least one good copy survives. This
is almost always faster than an RMAN restore and involves no backup
media.

```bash
# 1. Confirm the instance is down (control file errors typically crash
#    or prevent mount) or shut it down cleanly if still limping along
sqlplus / as sysdba
```

```sql
SHUTDOWN ABORT;
```

```bash
# 2. Copy a surviving good control file copy over the lost/corrupt one,
#    preserving the exact target path/filename expected by CONTROL_FILES
cp /u01/oradata/ORCL/control01.ctl /u02/oradata/ORCL/control02.ctl
chown oracle:oinstall /u02/oradata/ORCL/control02.ctl
chmod 640 /u02/oradata/ORCL/control02.ctl
```

```sql
-- 3. Start the instance normally — all configured CONTROL_FILES
--    locations are now present and identical copies
STARTUP;
```

> **Point of no return:** none — this is a non-destructive copy of a
> known-good file. If the target path is wrong, simply remove the
> misplaced copy and retry; the source control file is untouched.

### 6.2 RMAN Restore — Control File from Autobackup (NOCATALOG)

Use when **all** multiplexed copies are lost/corrupted and a controlfile
autobackup exists. This is the primary recovery path for total control
file loss.

```bash
export ORACLE_HOME=/u01/app/oracle/product/19.0.0/dbhome_1
export ORACLE_SID=ORCL
export PATH=$ORACLE_HOME/bin:$PATH

rman target /
```

```rman
-- 1. Force NOMOUNT — no control file is required at this stage
STARTUP FORCE NOMOUNT;

-- 2. Mandatory without a recovery catalog: identify the target database
SET DBID 1234567890;

-- 3. Restore the control file from the most recent autobackup
RESTORE CONTROLFILE FROM AUTOBACKUP;

-- 4. Mount using the restored control file
ALTER DATABASE MOUNT;

-- 5. The restored control file is from backup, so datafiles are behind
--    current — restore and recover the database using it
RESTORE DATABASE;
RECOVER DATABASE;

-- 6. Open, resetting logs because the control file used for recovery
--    was itself a backup control file
ALTER DATABASE OPEN RESETLOGS;
```

If the autobackup is not in the default location/format, or you need to
bound the search:

```rman
SET CONTROLFILE AUTOBACKUP FORMAT FOR DEVICE TYPE DISK TO
  '/u01/app/oracle/fra/ORCL/autobackup/%F';

RESTORE CONTROLFILE FROM AUTOBACKUP
  MAXSEQ 100
  MAXDAYS 14
  DB_NAME ORCL;
```

- `MAXDAYS` (default 7) — how many days backward RMAN searches for an
  autobackup; raise it if the incident predates the last week's backups.
- `MAXSEQ` — caps the autobackup sequence search; use when you know the
  most recent good autobackup is older than the highest sequence number.

### 6.3 RMAN Restore — Control File from Autobackup (Recovery Catalog)

If connected to a recovery catalog, the DBID is already known to the
catalog for a registered target, so `SET DBID` can be omitted:

```bash
rman target / catalog rman_cat/<password>@rmancat
```

```rman
STARTUP FORCE NOMOUNT;
RESTORE CONTROLFILE FROM AUTOBACKUP;
ALTER DATABASE MOUNT;
RESTORE DATABASE;
RECOVER DATABASE;
ALTER DATABASE OPEN RESETLOGS;
```

Alternatively, restore from a specific backup control file (from a
regular `BACKUP DATABASE INCLUDE CURRENT CONTROLFILE`) rather than the
autobackup:

```rman
RESTORE CONTROLFILE FROM 'ctl_backup_piece_handle.bck';
```

> **Point of no return:** `ALTER DATABASE OPEN RESETLOGS` in steps 6.2/6.3
> creates a new incarnation. This is required and expected after a
> controlfile restore/recover cycle — but take a fresh Level 0 backup
> immediately afterward (Section 7), and coordinate with Data Guard
> standbys per `06-data-guard-dr/` before this step if any standby exists.

### 6.4 Fallback — Manual CREATE CONTROLFILE (No Autobackup Available)

If no controlfile autobackup and no recovery catalog copy exists, a
control file can be rebuilt manually from a saved trace
(`ALTER DATABASE BACKUP CONTROLFILE TO TRACE`) or from first principles
using `CREATE CONTROLFILE ... RESETLOGS`, listing every current datafile,
tempfile, and redo log member explicitly. This is a last-resort,
error-prone procedure — the exact trace-editing steps, `REUSE`/`NORESETLOGS`
considerations, and validation checklist are documented separately in
`11-troubleshooting/` (manual control file reconstruction). Engage DBA
lead before attempting this path; always exhaust Sections 6.1–6.3 first.

## 7. Validation / Post-Checks

```sql
-- Confirm all configured control file copies are present and identical
SHOW PARAMETER control_files;
SELECT status, name FROM v$controlfile;

-- Confirm no I/O errors against any control file copy
SELECT status, count(*) FROM v$controlfile_record_section GROUP BY status;

-- Confirm database open and current incarnation
SELECT status FROM v$instance;
SELECT db_incarnation#, resetlogs_time, status
FROM v$database_incarnation ORDER BY resetlogs_time DESC;

SELECT name, status FROM v$datafile WHERE status NOT IN ('ONLINE','SYSTEM');
```

```rman
-- Confirm control file (and everything else) reports consistent
VALIDATE DATABASE;
```

- [ ] `v$controlfile` shows all configured copies present, no `INVALID`
- [ ] Database open (`READ WRITE`) and application connectivity confirmed
- [ ] If `RESETLOGS` was issued: fresh Level 0 backup taken immediately —
      prior backups cannot recover past the new incarnation without it
- [ ] Any Data Guard standby re-synced or re-instantiated
      (`06-data-guard-dr/`) if RESETLOGS occurred
- [ ] Alert log reviewed for errors during the recovery window

## 8. Rollback Plan

- **Section 6.1 (file copy):** fully reversible — remove the newly
  copied file and retry from a different surviving mirror if the copy
  was placed at the wrong path or is itself found to be stale.
- **Before `ALTER DATABASE MOUNT` in Sections 6.2/6.3:** safe to abort;
  no committed change yet — retry `RESTORE CONTROLFILE FROM AUTOBACKUP`
  with a corrected DBID or explicit autobackup handle.
- **After `OPEN RESETLOGS`:** no forward rollback via RMAN alone. If the
  wrong autobackup was restored, repeat Section 6.2/6.3 from scratch
  using the correct autobackup piece; do not attempt to recover forward
  across a resetlogs boundary using pre-resetlogs archivelogs.
- Escalate to DBA lead before any second control file restore attempt on
  Production, and before considering Section 6.4.

## 9. Communication

Before starting (except a same-node file copy under Section 6.1):
notify application owners and the incident channel with estimated outage
window. During: status update at NOMOUNT, control file restored, MOUNT,
restore/recover complete, database open. After: confirm database open,
note whether RESETLOGS occurred (and thus a fresh backup was required),
and file a post-incident review for any Production control file loss.

## 10. Known Issues / Gotchas

- Omitting `SET DBID` before `RESTORE CONTROLFILE FROM AUTOBACKUP`
  without a recovery catalog is the most common failure —
  `RMAN-06172: no autobackup found` results because RMAN has no
  controlfile to read the DBID from yet.
- After restoring a controlfile from autobackup, the restored file is
  logically older than the datafiles — always follow with
  `RESTORE DATABASE; RECOVER DATABASE; ALTER DATABASE OPEN RESETLOGS;`
  as in Section 6.2/6.3; do **not** attempt `ALTER DATABASE OPEN` without
  `RESETLOGS` after a controlfile restore, it will fail.
- If `CONTROL_FILES` in the spfile still references the lost path after
  a file-copy recovery under a *different* filename/path, update the
  spfile (`ALTER SYSTEM SET control_files=... SCOPE=SPFILE;`) and bounce
  the instance rather than relying on Section 6.1 alone.
- Multiplexed copies on the same physical disk/LUN provide no real
  protection — verify copies are on genuinely separate storage before
  relying on Section 6.1 as a viable fast path.
- For RAC, the control file is shared (typically on ASM); restoring it
  affects all instances — perform Section 6.2/6.3 with all other
  instances of the cluster database shut down first.

## 11. References

- MOS Doc ID 1531493.1 — RMAN RESTORE SPFILE / CONTROLFILE FROM
  AUTOBACKUP examples and troubleshooting
- MOS Doc ID 736715.1 — Recovering lost/damaged control files
- Oracle Database Backup and Recovery Reference — RMAN `RESTORE`
  command: https://docs.oracle.com/en/database/oracle/oracle-database/19/rcmrf/RESTORE.html
- Internal: `07-backup-recovery/01-rman-backup-strategy.md`
- Internal: `07-backup-recovery/02-rman-restore-recovery.md`
- Internal: `07-backup-recovery/03-recover-spfile.md`
- Internal: `11-troubleshooting/` (manual `CREATE CONTROLFILE` procedure)
- Internal: `06-data-guard-dr/` (standby resync after RESETLOGS)

## 12. Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-08-16 | DBA Team | Initial version |
