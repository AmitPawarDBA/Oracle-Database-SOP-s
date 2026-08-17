# SOP: Diagnosing "Archiver Stuck" / FRA Full (ORA-19809, ORA-19815)

**Category:** Troubleshooting
**Applies to:** Oracle 19c / 21c, Single Instance and RAC, Linux x86-64
**Risk Level:** Critical — an archiver-stuck condition halts all commits
database-wide; every user-facing transaction stops until resolved
**Estimated Duration:** 5–20 minutes to diagnose and apply immediate
remediation; longer if a full disk-space expansion is required
**Downtime Required:** No for remediation itself, but the database is
effectively **hung** (unable to process commits) for the duration of the
outage, which application teams will experience as a full outage
**Owner:** DBA Team
**Last Reviewed:** 2026-08-16
**Review Cadence:** Every 6 months, and after any FRA sizing/retention
policy change

---

## 1. Purpose

Provides the diagnostic and remediation steps for the "archiver stuck"
condition — the database cannot write new archived redo logs because the
Fast Recovery Area (FRA) or archive destination is full — which manifests
as a database-wide hang on commit. Speed matters here: this is a P1
Production-down condition, and the fix is usually a few minutes of work
once correctly diagnosed.

## 2. Scope

Covers `ORA-19809` (limit exceeded for recovery files) and `ORA-19815`
(FRA space warning threshold) conditions caused by the Fast Recovery Area
filling up, and the equivalent condition when `log_archive_dest_n` points
to a non-FRA filesystem that fills up. Applies to Production, Non-Prod,
and DR. Cross-references
`07-backup-recovery/01-rman-backup-strategy.md` for the backup/retention
configuration that prevents recurrence, and `10-monitoring-alerting/` for
proactive threshold alerting.

## 3. Prerequisites

- [ ] `sysdba` access
- [ ] `oracle` OS user access to check filesystem/ASM disk group free
      space
- [ ] Privilege to run `rman target /` and issue `DELETE` commands
      (destructive — restricted to DBA team)
- [ ] Awareness of current backup status before deleting anything (never
      delete archivelogs that are not confirmed backed up)

## 4. Pre-Checks

### 4.1 Recognize the symptoms

- Application teams report the database "hangs" — sessions issuing
  `COMMIT` or any DML never return.
- Alert log shows repeating archiver errors, typically:
  ```
  ORA-19809: limit exceeded for recovery files
  ORA-19804: cannot reclaim ... bytes disk space from ... limit
  ```
  or a `WARNING: ... of ... bytes is XX% used` (`ORA-19815`) message
  preceding a full outage as usage crosses 100%.
- `ARCH` background process(es) reported stuck/unable to archive in the
  alert log (`ARC0: Error 19809 Creating archive log file...`).

```sql
-- Confirm the database is genuinely blocked on log switch / archiving,
-- not ordinary lock contention
SELECT process, status, sequence#
FROM v$archive_processes;

SELECT thread#, sequence#, archived, status
FROM v$log
ORDER BY thread#, sequence#;
-- A redo log group stuck in status 'ACTIVE' or 'CURRENT' unable to be
-- reused because it hasn't been archived is the smoking gun
```

### 4.2 Confirm FRA usage

```sql
-- Overall FRA space limit vs used (works for both DB and RAC)
SELECT name, space_limit/1024/1024/1024 AS gb_limit,
       space_used/1024/1024/1024 AS gb_used,
       space_reclaimable/1024/1024/1024 AS gb_reclaimable,
       ROUND(space_used / space_limit * 100, 1) AS pct_used
FROM v$recovery_file_dest;

-- Breakdown by file type (archivelog, backup piece, etc.) and how much
-- is reclaimable vs not
SELECT file_type, percent_space_used, percent_space_reclaimable,
       number_of_files
FROM v$flash_recovery_area_usage;
```

Expected during an incident: `pct_used` at or near 100%, and
`v$flash_recovery_area_usage` showing `ARCHIVED LOG` (and/or `BACKUP
PIECE`) consuming most of the space with low `percent_space_reclaimable`
(meaning most of it is not yet eligible for deletion under the current
retention/deletion policy — this is exactly why it filled up).

## 5. Procedure

### 5.1 Immediate remediation — buy breathing room

The fastest, lowest-risk fix during an active outage is almost always to
increase the size limit temporarily — this does not require deleting
anything and takes effect immediately:

```sql
-- Check current value first
SHOW PARAMETER db_recovery_file_dest_size;

-- Increase it (assumes underlying filesystem/ASM disk group actually has
-- the free space — verify at the OS/ASM level first, see 5.1a)
ALTER SYSTEM SET db_recovery_file_dest_size = 300G SCOPE=BOTH;
```

> **Risk callout:** increasing `db_recovery_file_dest_size` only works if
> the underlying filesystem/ASM disk group genuinely has free space.
> Increasing the logical limit on a filesystem that is itself 100% full
> will not help — check OS-level free space (`df -h` for filesystem FRA,
> `asmcmd lsdg` for ASM) before assuming this alone resolves it.

#### 5.1a Verify underlying storage actually has room

```bash
# Filesystem-based FRA
df -h /u03/fra

# ASM-based FRA
asmcmd lsdg
```

If the underlying storage itself is full (not just the logical Oracle
limit), this is a storage-team escalation to add capacity — the
remediation below (deleting reclaimable archivelogs) is then the only
lever available until more disk arrives.

### 5.2 Delete backed-up, obsolete archivelogs via RMAN

If simply raising the size limit doesn't apply (storage genuinely full)
or as a durable fix rather than a temporary size bump, free space by
removing archivelogs that are already safely backed up:

```bash
export ORACLE_HOME=/u01/app/oracle/product/19.0.0/dbhome_1
export ORACLE_SID=<SID>
rman target /
```

```rman
-- Confirm what RMAN considers backed-up vs not before deleting anything
REPORT OBSOLETE;
LIST ARCHIVELOG ALL BACKED UP 1 TIMES TO DEVICE TYPE DISK;

-- Delete archivelogs already backed up at least once (safe — a copy
-- exists elsewhere), freeing FRA space immediately
DELETE ARCHIVELOG ALL BACKED UP 1 TIMES TO DEVICE TYPE DISK;

-- Also clear anything already outside the retention policy
DELETE NOPROMPT OBSOLETE;
```

> **Point of no return:** `DELETE ARCHIVELOG` physically removes files
> from disk. Only run this after confirming (via `LIST ... BACKED UP`)
> that a backup copy genuinely exists — deleting the only copy of an
> archivelog needed for recovery creates a gap in the recovery chain
> that cannot be closed. If no backup destination is currently reachable
> (e.g. the backup target is also the thing that's full), do not delete;
> resolve the storage/backup-target issue first or escalate.

If archivelogs have **not** yet been backed up (e.g. the backup job
itself failed, which is often *why* the FRA filled up), back them up to
an alternate destination first, then delete:

```rman
-- Back up to an alternate, non-FRA disk location or media manager to
-- free FRA space without losing recoverability
BACKUP ARCHIVELOG ALL FORMAT '/u04/emergency_arch/%U' DELETE INPUT;
```

### 5.3 Move the archive/FRA destination (if disk cannot be expanded quickly)

As a last resort when neither raising the limit nor deleting is viable
quickly enough (e.g. no reclaimable archivelogs and no spare disk on the
current mount):

```sql
-- Add a temporary second archive destination on a different filesystem
ALTER SYSTEM SET log_archive_dest_2 = 'LOCATION=/u05/emergency_arch'
  SCOPE=BOTH;
ALTER SYSTEM SET log_archive_dest_state_2 = ENABLE SCOPE=BOTH;
```

Once the primary FRA destination has headroom again (after Section 5.1 or
5.2), disable the temporary destination and reconcile any archivelogs
written there back into the standard backup/retention flow.

### 5.4 Confirm the hang clears

```sql
-- Sessions that were stuck on commit should resume immediately once
-- archiving succeeds — no further action needed, this self-clears
SELECT event, COUNT(*)
FROM v$session
WHERE wait_class != 'Idle'
GROUP BY event
ORDER BY 2 DESC;
```

Expect `log file switch (archiving needed)` / `log file switch
(checkpoint incomplete)` wait events to disappear from active sessions
within seconds of freeing space or raising the limit.

## 6. Validation / Post-Checks

```sql
SELECT name, ROUND(space_used / space_limit * 100, 1) AS pct_used
FROM v$recovery_file_dest;

SELECT file_type, percent_space_used, percent_space_reclaimable
FROM v$flash_recovery_area_usage;

-- Confirm ARCH process(es) healthy and current sequence archiving
SELECT process, status, sequence# FROM v$archive_processes
WHERE status != 'STOPPED';
```

- [ ] `pct_used` back under 80% (site standard threshold)
- [ ] No new `ORA-19809`/`ORA-19815` entries in the alert log since
      remediation
- [ ] Previously stuck sessions confirmed resumed (no long-running
      `log file switch` waits in `v$session`)
- [ ] Any archivelogs deleted were confirmed backed up beforehand (audit
      the RMAN log for the incident)
- [ ] Root cause identified: undersized FRA, failed backup job, or
      retention policy misconfiguration (see Section 9 for prevention)

## 7. Rollback Plan

This procedure is corrective, not destructive to the database itself
(archivelog deletion only removes files already safely backed up per
Section 5.2's checks). If remediation was applied incorrectly:

1. If `db_recovery_file_dest_size` was raised beyond what storage
   actually supports and the filesystem subsequently fills completely
   (worse than before), reduce it back and pursue Section 5.2/5.3
   instead.
2. If archivelogs were deleted in error before confirming a backup
   existed (violating the point-of-no-return check in 5.2), do not
   attempt further deletes — assess recovery exposure immediately: any
   gap in the archivelog chain limits point-in-time recovery options to
   before the gap. Escalate to a senior DBA and treat current backups as
   the last reliable recovery point until a fresh Level 0 is taken.
3. If a temporary alternate archive destination (5.3) is left enabled
   indefinitely, it will itself eventually fill — disable it once the
   primary is healthy again (Section 5.3, second paragraph).

## 8. Communication

This is a P1 — database-wide commit hang — requiring immediate incident
declaration and continuous updates to stakeholders until resolved (target:
initial diagnosis and remediation within 15 minutes given this SOP).
After resolution, a post-incident review is mandatory: FRA-full incidents
are almost always preventable via correct sizing and monitoring (Section
9) and recurrence should be treated as a process gap, not just a one-off
fix.

## 9. Known Issues / Gotchas

- The single most common root cause is a **failed or stalled backup job**
  silently leaving archivelogs un-backed-up while `DELETE INPUT`-based
  retention keeps expecting them to clear — always check backup job
  status (`v$rman_backup_job_details`, per
  `07-backup-recovery/01-rman-backup-strategy.md` Section 6) as part of
  root cause, not just FRA size.
- `db_recovery_file_dest_size` is a **logical** cap independent of actual
  disk size — it is easy to have plenty of physical disk free but still
  hit `ORA-19809` because the parameter itself is set too low; always
  check both the parameter and the underlying filesystem/ASM free space.
- `percent_space_reclaimable` in `v$flash_recovery_area_usage` is the key
  number during an incident — if it's low, deleting won't help much and
  raising the size limit or moving the destination becomes the only fast
  options.
- Guaranteed restore points (see
  `11-troubleshooting/03-flashback-database-to-restore-point.md`) prevent
  flashback logs from aging out and are a frequent, easy-to-forget cause
  of FRA filling unexpectedly — check `v$restore_point` for stale
  guaranteed restore points during root cause analysis.
- On RAC/ASM, a full FRA disk group affects **all instances**
  simultaneously — remediation (e.g. adding ASM disks) benefits the whole
  cluster, but during the incident every instance is independently stuck
  on commit.
- Proactive monitoring (see `10-monitoring-alerting/`) with an alert at
  70–80% FRA usage is the real fix — this SOP should be a rare event, not
  a routine occurrence.

## 10. References

- Verified against docs.oracle.com Error Help Center — ORA-19809 exact
  cause (`DB_RECOVERY_FILE_DEST_SIZE` limit exceeded) and the five
  recommended actions (frequent RMAN backups, retention policy change,
  archived log deletion policy change, increase
  `db_recovery_file_dest_size`, delete files via RMAN),
  https://docs.oracle.com/en/error-help/db/ora-19809/
- Verified against docs.oracle.com Error Help Center — ORA-19815 warning
  text and cause (FRA nearing capacity) and recommended actions,
  https://docs.oracle.com/en/error-help/db/ora-19815/
- Oracle Database Administrator's Guide — "Monitoring Fast Recovery Area
  Space Usage" (`V$RECOVERY_FILE_DEST`, `V$FLASH_RECOVERY_AREA_USAGE`)
- MOS Doc ID 305648.1 — Troubleshooting ORA-19809 / ORA-19815 archiver
  stuck conditions
- Internal: `07-backup-recovery/01-rman-backup-strategy.md`
- Internal: `07-backup-recovery/02-rman-restore-recovery.md`
- Internal: `10-monitoring-alerting/`
- Internal: `11-troubleshooting/03-flashback-database-to-restore-point.md`

## 11. Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-08-16 | DBA Team | Initial version |
