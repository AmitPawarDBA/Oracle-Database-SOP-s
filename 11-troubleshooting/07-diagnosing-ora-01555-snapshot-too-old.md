# SOP: Diagnosing and Resolving ORA-01555 (Snapshot Too Old)

**Category:** Troubleshooting
**Applies to:** Oracle 19c / 21c, Automatic Undo Management (AUM),
Single Instance and RAC
**Risk Level:** Medium — increasing undo retention/size is low-risk;
misdiagnosing the root cause and only increasing undo size without
addressing an unindexed long-running query wastes storage and delays
the real fix
**Estimated Duration:** 30–60 minutes for diagnosis; sizing/parameter
changes take effect immediately but query tuning follow-up may take
longer
**Downtime Required:** No
**Owner:** DBA Team
**Last Reviewed:** 2026-08-16
**Review Cadence:** Every 6 months

---

## 1. Purpose

Provides a structured method to diagnose the root cause of
ORA-01555 ("snapshot too old") — distinguishing an undo-sizing/
retention problem from a query-duration problem from a delayed-block-
cleanout problem — and apply the correct short-term and long-term
fix rather than reflexively growing the undo tablespace.

## 2. Scope

Covers Automatic Undo Management (AUM) environments only. Covers
diagnosis via `v$undostat`, `undo_retention`, `undo_tablespace`
sizing, and correlation with the failing query/session. Does **not**
cover manual rollback-segment-based undo management (deprecated,
should not exist in any 19c/21c environment covered by this repo), nor
Flashback-specific ORA-01555 variants raised by `DBMS_FLASHBACK`/AS OF
queries beyond the general root-cause triage in Section 5.

## 3. Prerequisites

- [ ] `sysdba` or an account with `SELECT_CATALOG_ROLE`
- [ ] Incident details: exact error text (including the rollback
      segment number/name Oracle reports), the SQL_ID or job that
      failed, and the approximate time of failure
- [ ] Confirm Automatic Undo Management is in use before proceeding
      (this SOP assumes AUM; manual rollback segments require a
      different approach):
      ```sql
      SELECT value FROM v$parameter WHERE name = 'undo_management';
      -- Expect: AUTO
      ```
- [ ] Storage headroom check on the undo tablespace's tablespace
      group/ASM diskgroup before considering a size increase

## 4. Pre-Checks

```sql
-- Confirm current undo configuration
SELECT name, value FROM v$parameter
WHERE name IN ('undo_management','undo_tablespace','undo_retention');

-- Confirm undo tablespace size, autoextend, and current usage
SELECT tablespace_name, file_name, bytes/1024/1024 AS mb,
       autoextensible, maxbytes/1024/1024 AS max_mb
FROM dba_data_files
WHERE tablespace_name = (SELECT value FROM v$parameter
                          WHERE name = 'undo_tablespace');

-- Confirm whether retention guarantee is enabled
SELECT tablespace_name, retention FROM dba_tablespaces
WHERE tablespace_name = (SELECT value FROM v$parameter
                          WHERE name = 'undo_tablespace');
```

## 5. Procedure

### 5.1 Confirm the Exact Error and Identify the Failing Statement

**Verified error text and cause (docs.oracle.com Error Messages
Reference, `ORA-01555`):** *"snapshot too old: rollback segment
number `<n>` with name `"<name>"` too small."* Cause: rollback/undo
records needed by a reader to construct a consistent-read image were
overwritten by other writers before the read completed. Action per
Oracle: if using Automatic Undo Management, increase
`UNDO_RETENTION`; if using manual rollback segments, use larger
rollback segments.

```sql
-- Find the failing SQL_ID from the alert log timestamp / app report,
-- or from a still-connected session if it's currently reproducing
SELECT sql_id, sql_text FROM v$sql WHERE sql_id = '&sql_id';

-- Check ASH for what the session was doing right before the error
-- (if within retention window)
SELECT sample_time, sql_id, event, wait_class
FROM v$active_session_history
WHERE session_id = &sid
ORDER BY sample_time DESC
FETCH FIRST 50 ROWS ONLY;
```

### 5.2 Root Cause Triage

ORA-01555 has four distinct root causes. Work through them in this
order — the fix differs materially for each:

```
ORA-01555 raised
   |
   +-- Was undo_retention recently lowered, or is undo tablespace
   |   undersized relative to DML volume + query duration?
   |       -> Root cause: undo retention/size too short.
   |          Go to 5.2.1.
   |
   +-- Is the failing query itself long-running (minutes to hours),
   |   e.g. a report, batch extract, or unindexed full-table-scan
   |   join against a heavily-updated table?
   |       -> Root cause: query duration exceeds undo retention
   |          under normal-sized undo. Go to 5.2.2.
   |
   +-- Does the query use a bind variable / cursor held open across
   |   a long session (e.g. a fetch-across-commit pattern, or a
   |   cursor opened before a long batch loop that also commits)?
   |       -> Root cause: application design - reading with an old
   |          SCN while the same session or others commit heavily
   |          against the same blocks. Go to 5.2.3.
   |
   +-- Is the table rarely queried after bulk load/direct-path
   |   insert, and does the error occur on the FIRST query against
   |   recently-loaded blocks?
           -> Root cause: delayed block cleanout - go to 5.2.4.
```

#### 5.2.1 Undo Retention / Size Too Short

```sql
-- Check actual tuned retention Oracle is achieving vs. configured
SELECT tuned_undoretention, maxquerylen, activeblks, unexpiredblks,
       expiredblks
FROM v$undostat
ORDER BY end_time DESC
FETCH FIRST 10 ROWS ONLY;

-- Check for recent "no space" or short-retention pressure - a nonzero
-- ssolderrcnt (snapshot-too-old count) or nospaceerrcnt confirms undo
-- pressure was a factor in this window
SELECT begin_time, end_time, undoblks, txncount, maxquerylen,
       ssolderrcnt, nospaceerrcnt, expiredblks
FROM v$undostat
WHERE ssolderrcnt > 0 OR nospaceerrcnt > 0
ORDER BY end_time DESC
FETCH FIRST 20 ROWS ONLY;

-- Confirm configured retention vs. default (900s / 15 min per
-- docs.oracle.com parameter reference)
SHOW PARAMETER undo_retention;
```

If `ssolderrcnt` or `nospaceerrcnt` is nonzero for the incident
window, undo pressure is confirmed as (at least) a contributing
factor.

#### 5.2.2 Long-Running Query Exceeding Retention

```sql
-- Confirm the query's actual runtime against v$sqlstats
SELECT sql_id, executions,
       ROUND(elapsed_time/DECODE(executions,0,1,executions)/1e6, 1)
         AS avg_elapsed_sec
FROM v$sqlstats
WHERE sql_id = '&sql_id';

-- Compare against tuned undo retention from 5.2.1 - if avg_elapsed_sec
-- approaches or exceeds tuned_undoretention, the query itself is the
-- problem, not (only) undo sizing
```

If the query is unindexed and doing a full scan / expensive join over
a table with concurrent heavy DML, tuning the query (adding an index,
rewriting the join, adding a `WHERE` predicate to reduce scanned rows)
is the durable fix — increasing undo retention only buys time, it
does not fix a query that takes longer than any reasonable retention
window under sustained DML.

#### 5.2.3 Application Pattern (Long-Open Cursor / Fetch-Across-Commit)

Check whether the failing session itself was committing (or another
session heavily updating the same rows) while a cursor stayed open
across the read:

```sql
SELECT s.sid, s.serial#, s.sql_id, s.program, s.module, s.logon_time
FROM v$session s
WHERE s.sid = &sid;
```

This is a coding pattern problem — a batch job that opens a cursor,
loops, and commits periodically while continuing to fetch from the
same cursor is a classic ORA-01555 trigger even with generous undo
retention (`_row cache_`/consistent-read image for the open cursor
still needs undo that a same-session commit can age out). Fix at the
application level: commit less frequently, or re-open the cursor after
each commit batch, or use `SELECT ... FOR UPDATE` where semantics
allow — application code changes are outside DBA remediation scope
but must be flagged to the development team.

#### 5.2.4 Delayed Block Cleanout

After a large bulk load (`INSERT /*+ APPEND */`, direct-path load,
`CREATE TABLE ... AS SELECT`), Oracle defers transaction cleanout of
the block headers for performance. The **first** query to touch those
blocks afterward may need to consult undo to determine
committed/uncommitted status for every row — if that undo has already
aged out (common right after a big load, since the load itself
generated a lot of undo/redo churn), ORA-01555 can occur even on a
short, well-tuned query against a table nobody else is modifying.

```sql
-- Corroborate: was there a recent large load on the object involved?
SELECT segment_name, bytes/1024/1024 AS mb, last_analyzed
FROM dba_segments s JOIN dba_tables t
  ON s.segment_name = t.table_name AND s.owner = t.owner
WHERE s.segment_name = '&table_name';
```

Fix: run a `SELECT COUNT(*)` (or equivalent full scan) against the
table immediately after the bulk load, before it is opened up to
general query traffic — this forces cleanout while undo for the load
transaction is still available, and prevents the first "real" query
from hitting ORA-01555.

### 5.3 Short-Term Remediation

Apply immediately to stop active incident recurrence while the
long-term fix (Section 5.4) is implemented:

```sql
-- Increase undo_retention (dynamic, no restart required)
ALTER SYSTEM SET undo_retention = 3600 SCOPE=BOTH;  -- example: 1 hour

-- Confirm undo tablespace has enough space to actually honor the new
-- retention - AUTOEXTEND tablespaces respect undo_retention, but only
-- if there is room to grow (or space to autoextend into)
SELECT tablespace_name, autoextensible, maxbytes/1024/1024 AS max_mb
FROM dba_data_files
WHERE tablespace_name = (SELECT value FROM v$parameter
                          WHERE name = 'undo_tablespace');
```

If the undo tablespace is fixed-size and too small to support the
needed retention, grow it:

```sql
ALTER DATABASE DATAFILE '<undo_datafile_path>'
  RESIZE <new_size>M;

-- Or add a datafile
ALTER TABLESPACE UNDOTBS1 ADD DATAFILE
  '/u01/app/oracle/oradata/<db>/undotbs02.dbf' SIZE 5G AUTOEXTEND ON
  NEXT 500M MAXSIZE 20G;
```

Sizing guidance: undo tablespace size should be at least
`UNDO_RETENTION (seconds) x undo generation rate (bytes/sec) x
1.x safety margin`. Estimate undo generation rate from
`v$undostat.undoblks` over a representative period, or use the
formula-based advisor:

```sql
SELECT (SUM(undoblks) * (SELECT block_size FROM dba_tablespaces
        WHERE tablespace_name = (SELECT value FROM v$parameter
                                  WHERE name = 'undo_tablespace')))
       / SUM(activeblks + unexpiredblks + expiredblks + 1) -- avoid /0
FROM v$undostat;
-- Simpler in practice: use the Undo Advisor in Enterprise Manager, or
-- size = (undo_retention_seconds * avg undoblks/sec * block_size) * 1.2
```

> **Note:** enabling `RETENTION GUARANTEE` on the undo tablespace
> forces Oracle to preserve undo for the full retention period even
> at the cost of failing DML with "out of space" (ORA-30036) rather
> than silently overwriting undo. Only enable this after confirming
> the tablespace is sized to handle sustained peak DML volume — it
> trades ORA-01555 risk for ORA-30036 risk if undersized:
> ```sql
> ALTER TABLESPACE UNDOTBS1 RETENTION GUARANTEE;
> ```

### 5.4 Long-Term Remediation

Choose based on the root cause identified in Section 5.2:

- **5.2.1 (retention/size):** permanently size the undo tablespace per
  the guidance above and set `undo_retention` to comfortably exceed
  the longest legitimate query/report runtime, with headroom for peak
  DML periods (month-end batch, etc.).
- **5.2.2 (long-running/unindexed query):** tune the query — add a
  missing index, rewrite to reduce scanned rows, or route the report
  to a read-only standby / offload database if the underlying primary
  cannot tolerate report-length consistent reads at all. Hand off to
  `08-performance-tuning/01-awr-based-performance-diagnosis.md`
  Section 5.6 for SQL Tuning Advisor.
- **5.2.3 (application cursor pattern):** file a defect against the
  application/batch job to commit less frequently or re-fetch after
  each commit; DBA-side undo tuning is a mitigation, not a fix, for
  this root cause.
- **5.2.4 (delayed block cleanout):** add a post-load `SELECT
  COUNT(*)` (or `DBMS_STATS.GATHER_TABLE_STATS`, which also touches
  every block) as a standard step in the bulk-load runbook so cleanout
  happens while load undo is still live.

## 6. Validation / Post-Checks

```sql
-- Confirm new retention took effect
SHOW PARAMETER undo_retention;
SELECT tuned_undoretention FROM v$undostat
ORDER BY end_time DESC FETCH FIRST 1 ROWS ONLY;

-- Confirm no new snapshot-too-old / no-space pressure since the fix
SELECT begin_time, end_time, ssolderrcnt, nospaceerrcnt
FROM v$undostat
WHERE begin_time > SYSTIMESTAMP - INTERVAL '1' DAY
  AND (ssolderrcnt > 0 OR nospaceerrcnt > 0);
```

- [ ] Previously failing query/job re-run successfully end-to-end
- [ ] `v$undostat.ssolderrcnt`/`nospaceerrcnt` show no new
      occurrences since the fix was applied
- [ ] Root cause category (5.2.1–5.2.4) documented in the incident
      ticket, along with which remediation (short-term and/or
      long-term) was applied
- [ ] If a long-term application/query fix was identified but not yet
      implemented, a follow-up ticket is opened with the dev team

## 7. Rollback Plan

- **`undo_retention` increased:** revert via
  `ALTER SYSTEM SET undo_retention = <prior_value> SCOPE=BOTH;` if the
  new value causes undo tablespace space pressure elsewhere (monitor
  `v$undostat.nospaceerrcnt` after the change).
- **Undo datafile resized/added:** a resize down is generally unsafe
  while blocks are in use; if space must be reclaimed, do so only
  after confirming via `dba_free_space`/undo advisor that the added
  space is unused, and treat as a separate, deliberate change rather
  than an emergency rollback.
- **`RETENTION GUARANTEE` enabled:** revert with
  `ALTER TABLESPACE UNDOTBS1 RETENTION NOGUARANTEE;` if it begins
  causing ORA-30036 (out of undo space) failures for legitimate DML
  and the tablespace cannot be grown immediately.

## 8. Communication

For a Production batch/report failure due to ORA-01555: notify the
job/report owner with the root cause category and expected fix ETA.
If the fix requires an application-side change (Section 5.2.3), open
a ticket with the development team and reference it in the DBA
incident ticket — do not close the DBA-side ticket until either the
long-term fix lands or a durable mitigation (adequate undo sizing) is
confirmed stable across at least one full peak-DML cycle.

## 9. Known Issues / Gotchas

- Increasing `undo_retention` alone does not help if the undo
  tablespace lacks the physical space to honor it — always check
  `v$undostat.tuned_undoretention` after the change, not just the
  parameter value, since Oracle silently caps actual retention to
  what current space allows unless `RETENTION GUARANTEE` is set.
- `RETENTION GUARANTEE` trades one error for another — undersized
  guaranteed-retention undo will start failing DML with ORA-30036
  instead of failing reads with ORA-01555. Size before enabling, don't
  enable and hope.
- A single very long-running report can make ORA-01555 effectively
  unavoidable at any reasonable undo size — if `avg_elapsed_sec` from
  Section 5.2.2 is measured in hours, the durable fix is almost always
  query tuning or moving the workload off the primary, not undo
  sizing.
- Delayed block cleanout (5.2.4) is easy to misdiagnose as a sizing
  issue because it often follows shortly after a large load — check
  `dba_segments`/load timing before assuming retention is the cause.
- ORA-01555 raised during Flashback Query / `AS OF` operations follows
  the same underlying undo-retention mechanics but is bounded by
  `undo_retention` regardless of guarantee settings for the *query*
  itself unless `RETENTION GUARANTEE` is explicitly set — flashback
  queries beyond the tuned retention window will fail even on a
  healthy system; this is expected behavior, not a bug.

## 10. References

- Verified against **docs.oracle.com Error Messages Reference**:
  [ORA-01555](https://docs.oracle.com/en/error-help/db/ora-01555/) —
  confirmed exact error text "snapshot too old: rollback segment
  number `<n>` with name `<name>` too small," cause (undo records
  needed for consistent read overwritten by other writers), and
  Oracle's documented action (increase `undo_retention` under AUM, or
  use larger rollback segments under manual undo management).
- Verified against **docs.oracle.com Database Reference 19c**:
  [UNDO_RETENTION](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/UNDO_RETENTION.html)
  — confirmed default value (900 seconds / 15 minutes) and
  version-specific AUTOEXTEND vs. fixed-size tablespace retention
  behavior (19.7+ honors `UNDO_RETENTION` as a minimum for both
  tablespace types; earlier releases differ for fixed-size without
  guarantee).
- Oracle Database Reference — `V$UNDOSTAT` column definitions
  (`tuned_undoretention`, `ssolderrcnt`, `nospaceerrcnt`, `undoblks`).
- Oracle Database Administrator's Guide (19c), "Managing Undo."
- Internal: `08-performance-tuning/01-awr-based-performance-diagnosis.md`
- Internal: `11-troubleshooting/06-diagnosing-cpu-io-spikes-using-ash.md`
  (for correlating undo-generation spikes with a specific job/session)

## 11. Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-08-16 | DBA Team | Initial version |
