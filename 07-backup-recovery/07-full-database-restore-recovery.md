# SOP: Full Database Restore and Recovery — Deep Dive

**Category:** Backup & Recovery
**Applies to:** Oracle 19c / 21c, Single Instance and RAC, Linux x86-64
**Risk Level:** Critical — total data-loss risk and extended-outage
window; the largest-blast-radius recovery operation in the RMAN toolkit
**Estimated Duration:** 1–8+ hours, dependent on database size,
restore-source throughput, and channel parallelism
**Downtime Required:** Yes — full outage from `NOMOUNT`/`MOUNT` until
`ALTER DATABASE OPEN` succeeds
**Owner:** DBA Team
**Last Reviewed:** 2026-08-16
**Review Cadence:** Every 6 months, and after every recovery drill

---

## 1. Purpose

Deep-dive procedure for restoring/recovering an **entire database to
the latest available point** after total loss (host/storage failure,
dropped datafiles, or a lost controlfile with no surviving copies).
`07-backup-recovery/02-rman-restore-recovery.md` Section 5.1 is the
quick decision-tree version; this document covers catalog vs.
no-catalog restores, restoring to a different location, parallel
channel tuning for large databases, and a worked walkthrough with
expected RMAN output.

## 2. Scope

Covers complete restore/recovery to the most recent consistent state,
catalog and controlfile-only, on the original host or a replacement host
with different mount points. Applies to Production, Non-Prod, DR. Does
**not** cover recovery to a past point (see
`08-point-in-time-recovery-pitr.md`), single-tablespace recovery (see
`09-tablespace-restore-recovery.md`), or auxiliary-instance recovery
(see `10-tspitr-recovery-using-auxiliary-database.md`). Start at
`02-rman-restore-recovery.md` Section 4 to confirm "full database to
latest" is the correct path before using this document.

## 3. Prerequisites

- [ ] Sev1 ticket open; DBA lead/Incident Commander assigned
- [ ] Loss/corruption scope confirmed as total (`v$datafile`, alert log)
- [ ] Latest usable backup identified (`LIST BACKUP SUMMARY`,
      `CROSSCHECK`)
- [ ] Catalog connectivity confirmed if used; otherwise `DBID` known and
      controlfile autobackup location known
- [ ] Target restore location confirmed available (original or new)
- [ ] Free space confirmed for the restore
- [ ] No archivelog gap between last backup and now (Section 4)
- [ ] Stakeholder communication sent (Section 8)
- [ ] Rollback/abort criteria understood (Section 7)

## 4. Pre-Checks

```sql
SELECT status FROM v$instance;
SELECT file#, name, status FROM v$datafile;
```

```rman
rman target /   -- or: rman target / catalog rman_cat/<password>@rmancat
LIST BACKUP SUMMARY;
CROSSCHECK BACKUP;
CROSSCHECK ARCHIVELOG ALL;
```

```sql
-- Confirm no gap between the newest usable backup and now
SELECT thread#, MIN(sequence#) min_seq, MAX(sequence#) max_seq
FROM v$archived_log GROUP BY thread#;
```

Expected: no unexpected `EXPIRED` entries; contiguous archivelog
sequence ranges per thread. A gap means "latest" recovery stops short —
decide now whether that's acceptable.

## 5. Procedure

### 5.1 Scenario A — Recovery Catalog Available

```bash
export ORACLE_SID=ORCL
export ORACLE_HOME=/u01/app/oracle/product/19.0.0/dbhome_1
$ORACLE_HOME/bin/rman target / catalog rman_cat/<password>@rmancat
```

```rman
STARTUP NOMOUNT;
RESTORE CONTROLFILE FROM AUTOBACKUP;
ALTER DATABASE MOUNT;
```

```
Expected output (abbreviated):
channel ORA_DISK_1: restoring control file from AUTOBACKUP
channel ORA_DISK_1: control file restore from AUTOBACKUP complete
database mounted
```

The catalog already knows the DBID and backup metadata, so this works
even with a completely empty/replaced controlfile. Proceed to 5.3.

### 5.2 Scenario B — No Catalog (Controlfile-Only)

Most common for single-database sites. Because the controlfile may also
be lost, RMAN needs the `DBID` and autobackup location first:

```bash
$ORACLE_HOME/bin/rman target /
```

```rman
STARTUP NOMOUNT;
SET DBID 1234567890;   -- get from DR documentation ahead of time

RUN {
  SET CONTROLFILE AUTOBACKUP FORMAT FOR DEVICE TYPE DISK TO '/u03/fra/%F';
  RESTORE CONTROLFILE FROM AUTOBACKUP;
}
ALTER DATABASE MOUNT;
```

If the autobackup can't be found automatically (e.g. a brand-new host),
use `RESTORE CONTROLFILE FROM '<explicit_backup_piece_path>';` instead.

### 5.3 Validate, Restore, and Recover (both scenarios, once mounted)

```rman
RESTORE DATABASE VALIDATE;   -- dry-run: confirms every piece is present
```

```rman
RESTORE DATABASE;
RECOVER DATABASE;
ALTER DATABASE OPEN;
```

```
Expected output (abbreviated):
Starting restore at 16-AUG-2026 09:18:02
channel ORA_DISK_1: restoring datafile 00001 to /u02/oradata/ORCL/system01.dbf
channel ORA_DISK_1: reading from backup piece /u03/fra/ORCL/backupset/...
Finished restore at 16-AUG-2026 10:30:35
media recovery complete, elapsed time: 00:18:47
database opened
```

> **Point of no return:** once `RECOVER DATABASE` starts applying
> archivelogs, the target is committed to "latest." If a different
> target turns out to be needed, re-restore and re-run with `SET UNTIL`
> (see `08-point-in-time-recovery-pitr.md`) instead of recovering
> forward.

### 5.4 Restoring to a Different Location

Use `SET NEWNAME` inside a `RUN` block, then `SWITCH DATAFILE ALL` to
repoint the controlfile before recovery:

```rman
RUN {
  SET NEWNAME FOR DATAFILE 1 TO '/u05/oradata/ORCL/system01.dbf';
  SET NEWNAME FOR DATAFILE 2 TO '/u05/oradata/ORCL/sysaux01.dbf';
  SET NEWNAME FOR DATAFILE 3 TO '/u05/oradata/ORCL/undotbs01.dbf';
  SET NEWNAME FOR DATAFILE 4 TO '/u05/oradata/ORCL/users01.dbf';
  -- For many files, SET NEWNAME FOR DATABASE TO NEW relocates every
  -- unnamed file into DB_CREATE_FILE_DEST (OMF/ASM) in one clause
  RESTORE DATABASE;
  SWITCH DATAFILE ALL;
  RECOVER DATABASE;
}
ALTER DATABASE OPEN;
```

Redo log members are not relocated automatically — the controlfile
autobackup carries the original paths:

```sql
SELECT group#, member FROM v$logfile;
ALTER DATABASE DROP LOGFILE MEMBER '/u02/oradata/ORCL/redo01a.log';
ALTER DATABASE ADD LOGFILE MEMBER '/u05/oradata/ORCL/redo01a.log' TO GROUP 1;
```

### 5.5 Parallel Channel Tuning for Large Databases

Tune channel count to the restore source's real throughput ceiling —
more channels than the backend can service adds coordination overhead
without speeding anything up.

```rman
RUN {
  ALLOCATE CHANNEL c1 DEVICE TYPE DISK;
  ALLOCATE CHANNEL c2 DEVICE TYPE DISK;
  ALLOCATE CHANNEL c3 DEVICE TYPE DISK;
  ALLOCATE CHANNEL c4 DEVICE TYPE DISK;
  -- SECTION SIZE splits a very large datafile across channels instead
  -- of bottlenecking on one channel while others sit idle
  RESTORE DATABASE SECTION SIZE 4G;
  RECOVER DATABASE PARALLEL 4;
}
```

Start with roughly one channel per 2–4 available CPU cores, capped by
observed backend throughput; `RECOVER DATABASE PARALLEL n` parallelizes
redo apply separately from restore.

```sql
-- Monitor progress live
SELECT sid, sofar, totalwork, round(sofar/totalwork*100,2) pct_complete,
       time_remaining
FROM v$session_longops
WHERE opname LIKE 'RMAN%' AND totalwork > 0 AND sofar < totalwork;
```

## 6. Validation / Post-Checks

```sql
SELECT status, database_status FROM v$instance;
SELECT name, open_mode, log_mode FROM v$database;
SELECT file#, name, status FROM v$datafile WHERE status NOT IN ('ONLINE','SYSTEM');
SELECT COUNT(*) FROM v$database_block_corruption;
```

```rman
VALIDATE DATABASE;
```

- [ ] `open_mode = READ WRITE`; no unexpected offline/recover datafiles
- [ ] `v$database_block_corruption` returns zero rows
- [ ] Application connectivity and a smoke-test transaction confirmed
- [ ] Alert log reviewed for the recovery window
- [ ] Fresh Level 0 backup scheduled once stable (not required here
      since no `RESETLOGS` occurred — this was recovery to latest)

## 7. Rollback Plan

- **Before `RECOVER DATABASE`:** safe to abort — restored datafiles can
  be discarded and the restore re-run.
- **After `RECOVER DATABASE`, before `OPEN`:** re-run `RESTORE`/`RECOVER`
  if the wrong backup set was used; no resetlogs occurs on a "to latest"
  recovery, so no incarnation branching.
- **After `OPEN`:** database is live; treat any post-open corruption
  discovery as a new incident rather than attempting to reverse the open.
- Escalate to DBA lead before any second full-database recovery attempt
  on Production.

## 8. Communication

Notify the incident channel and application owners immediately once
full-database recovery is confirmed. Give an estimated duration based on
backup size and observed throughput. Status updates at restore start,
restore % complete (every 30 min for long restores), recovery started,
database open. Final message confirms open state, validation status, and
that no data loss occurred (clean "latest" recovery).

## 9. Known Issues / Gotchas

- `SET DBID` is required before `RESTORE CONTROLFILE FROM AUTOBACKUP`
  with no controlfile and no catalog — get it from DR documentation
  ahead of time, not mid-incident.
- On a replacement host, the default autobackup search path may not
  exist — point `CONFIGURE`/`RUN`-block `CONTROLFILE AUTOBACKUP FORMAT`
  at wherever the autobackups actually are.
- `SWITCH DATAFILE ALL` only works cleanly when every restored datafile
  had a matching `SET NEWNAME` in the same `RUN` block.
- Over-allocating channels beyond backend throughput can slow a restore
  down — baseline with a smaller test restore first.
- Missing archivelogs between the last backup and now cap how far
  "latest" can reach — check `v$archived_log` before promising
  zero-data-loss recovery.
- If TDE is in use, confirm the wallet is open
  (`SELECT status FROM v$encryption_wallet;`) before `RESTORE`/`RECOVER`.

## 10. References

- MOS Doc ID 1116484.1 — RMAN Backup and Recovery best practices
- MOS Doc ID 1526597.1 — RMAN compression algorithm comparison
- Oracle Database Backup and Recovery User's Guide 19c — "Performing
  Complete Database Recovery", "Restoring the Database on a New Host",
  "Tuning RMAN Restore Operations"
  (https://docs.oracle.com/en/database/oracle/oracle-database/19/bradv/)
- Oracle Database Backup and Recovery Reference 19c — `RESTORE`,
  `RECOVER`, `SET NEWNAME`, `SWITCH` syntax, verified 2026-08-16
  (https://docs.oracle.com/en/database/oracle/oracle-database/19/rcmrf/RESTORE.html,
  https://docs.oracle.com/en/database/oracle/oracle-database/19/rcmrf/RECOVER.html,
  https://docs.oracle.com/en/database/oracle/oracle-database/19/rcmrf/SET.html)
- Internal: `07-backup-recovery/02-rman-restore-recovery.md` (quick
  decision tree — start there first)
- Internal: `07-backup-recovery/01-rman-backup-strategy.md`
- Internal: `07-backup-recovery/08-point-in-time-recovery-pitr.md`

## 11. Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-08-16 | DBA Team | Initial version |
