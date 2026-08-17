# SOP: Recover a Lost or Corrupted Voting Disk

**Category:** High Availability / RAC
**Applies to:** Oracle 19c Grid Infrastructure + RAC (11.2.0.2+ exclusive-mode
behavior applies), Linux x86-64 (RHEL/OEL 7/8/9), 3-node cluster `RACCLUSTER`
(`racnode1`/`racnode2`/`racnode3`), voting disks in ASM diskgroup
**Risk Level:** Critical — incorrect action here can take the entire cluster
down or lose cluster configuration permanently
**Estimated Duration:** 15–30 minutes (partial loss) / 45–90 minutes (total
loss, longer if a diskgroup must be rebuilt)
**Downtime Required:** No for partial loss (Clusterware keeps running). Yes
for total loss — full cluster outage until exclusive-mode recovery completes
**Owner:** DBA Team
**Last Reviewed:** 2026-08-16
**Review Cadence:** Every 6 months, and after every Grid Infrastructure
version change

---

## 1. Purpose

Provides a decision-driven, copy-pasteable procedure for recovering Oracle
Clusterware voting disks (voting files) after loss or corruption of one, some,
or all copies, so the cluster's node-membership arbitration mechanism is
restored to full redundancy without unnecessary downtime.

## 2. Scope

Covers voting disks stored in an Oracle ASM diskgroup (the standard 19c
layout — Oracle Clusterware manages voting file placement automatically
across ASM failgroups and this SOP does not cover the legacy non-ASM raw
device layout). Covers two distinct scenarios with different risk profiles
and different recovery paths:

- **Partial loss** — some, but not all, voting disk copies are
  lost/corrupted; the cluster is still up because a surviving quorum of
  copies exists.
- **Total loss** — all voting disk copies are lost/corrupted, or the
  surviving copies have dropped below what Clusterware needs to determine
  a quorum, and Clusterware/CSSD can no longer start normally.

Does **not** cover OCR (Oracle Cluster Registry) recovery — OCR and voting
disks often share the same ASM diskgroup, but their recovery procedures are
independent (see references). Does not cover non-ASM (raw/block device or
NFS) voting disk configurations, which are legacy and out of scope.

## 3. Prerequisites

- [ ] Root and `grid` OS user access on all cluster nodes
- [ ] Current, verified OCR backup exists and is restorable
      (`ocrconfig -showbackup`) — required regardless of scenario, because
      voting disk recovery in exclusive mode depends on a healthy OCR
- [ ] Change ticket / incident ticket opened (this is normally an
      unplanned/emergency SOP, but still requires the standard approval and
      communication trail — see Section 8)
- [ ] Confirmed identity of which ASM diskgroup holds the voting disks:
      `crsctl query css votedisk`
- [ ] For total-loss scenarios: confirmed whether the underlying ASM
      diskgroup itself is intact, degraded, or also lost — this determines
      whether Step 4 of the total-loss path (diskgroup rebuild) is needed
- [ ] Rollback/escalation plan reviewed (Section 7) — for total loss there is
      no "rollback," only forward recovery, so this step is about knowing
      the Oracle Support escalation path (Sev 1 SR) if exclusive-mode
      recovery does not proceed as expected
- [ ] Stakeholders notified per Section 8 before starting (or immediately
      after stabilizing, if this is an active outage)

## 4. Pre-Checks — Decision Point

Run this from any surviving node as the `grid` OS user (or root, if CRS is
fully down and `grid` cannot log in via SSH) to determine which recovery
path applies:

```bash
# Attempt to query voting disk status
crsctl query css votedisk
```

Interpret the output:

| Output | Meaning | Path |
|---|---|---|
| Lists 1 or more `MISSING`/inaccessible copies, but still returns a full list with a majority of copies `ONLINE`/valid, and `crsctl check cluster -all` shows the cluster up | **Partial loss** — Clusterware auto-recovered using the surviving quorum | **Path A** (Section 5A) |
| Returns `Located 0 voting disk(s)` or the command fails entirely because CSSD/CRS will not start on any node | **Total loss** — no quorum available, cluster is down | **Path B** (Section 5B) |

Also confirm cluster-wide status before deciding:

```bash
# From a node where CRS is still up
crsctl check cluster -all
crsctl check crs

# If CRS won't even start locally
crsctl check has
```

> If you are unsure which path applies, treat it as **total loss (Path B)**
> only if `crsctl query css votedisk` cannot be run successfully on any node
> and the cluster is confirmed down on all nodes. Do not run exclusive-mode
> recovery (Path B) against a cluster that is still up on a surviving
> quorum — it is unnecessary and disruptive.

## 5. Procedure

### 5A. Partial Loss (Cluster Still Up, Surviving Quorum)

This is the common case: a storage array LUN backing one voting disk copy
fails, or one failgroup becomes unavailable, while the rest of the ASM
diskgroup and its other voting disk copies remain healthy. Oracle
Clusterware continues operating using the surviving copies — no CRS
restart or downtime is required. The goal is simply to restore full
voting-disk redundancy.

1. **Confirm the cluster is genuinely healthy** despite the missing copy:
   ```bash
   crsctl check cluster -all
   crsctl stat res -t | grep -i offline
   ```
   Expected: all nodes report `CRS-4537`/`CRS-4529`/`CRS-4533` healthy
   lines; no unexpected resources OFFLINE due to the voting disk issue.

2. **Identify the storage-level root cause** of the missing/corrupted copy
   (failed disk, dropped ASM disk, storage array LUN issue, multipath
   failure) and resolve it at the storage layer first — replacing/repairing
   the underlying disk before touching Clusterware voting file
   configuration. Confirm with ASM:
   ```bash
   asmcmd lsdg
   asmcmd lsdsk -G <diskgroup_name>
   ```

3. **Restore full voting disk redundancy** once the underlying storage is
   healthy again. In the common ASM case, Clusterware automatically manages
   voting file count/placement based on diskgroup redundancy, so simply
   re-adding/repairing the failed ASM disk into its diskgroup and letting
   the rebalance complete is usually sufficient. Confirm ASM rebalance is
   complete:
   ```bash
   SELECT * FROM v$asm_operation;
   -- Expect no rows once rebalance is complete
   ```

4. **If the voting disk count does not self-correct** after storage repair
   (rare — normally only needed if you explicitly relocated voting disks to
   a different diskgroup), force Clusterware to re-evaluate voting file
   placement in the target diskgroup:
   ```bash
   crsctl replace votedisk +DISKGROUP_NAME
   ```
   This is safe to run against a healthy, running cluster — it recomputes
   and redistributes voting files across the diskgroup's failgroups without
   requiring exclusive mode or any downtime.

> **Point of no return:** none in this path under normal conditions — every
> step here is reversible and non-disruptive. The only truly disruptive
> action would be forcing CRS restarts, which this path does not require.

### 5B. Total Loss (All Voting Disks Lost, Cluster Down)

Use this path only when **all** voting disk copies are lost or corrupted and
Clusterware cannot establish quorum on any node (confirmed in Section 4).
This procedure has been cross-checked against Oracle Clusterware
documentation and community RAC references (see Section 10).

1. **Stop Clusterware on every node** (root, on each node in turn):
   ```bash
   crsctl stop crs -f
   ```
   `-f` forces the stop even if resources fail to stop cleanly — expected
   and necessary here since the cluster is already non-functional.

2. **Start Clusterware in exclusive mode on exactly ONE node** (root, pick
   one surviving node, e.g. `racnode1`):
   ```bash
   crsctl start crs -excl -nocrs
   ```
   `-excl` starts the stack in exclusive mode without requiring voting
   files to be present. `-nocrs` additionally prevents the CRSD process
   (and therefore OCR-dependent resources) from starting, which is required
   when the OCR-holding diskgroup is also unavailable — it brings up only
   ASM/CSSD, enough to mount diskgroups and manage voting files. Do **not**
   run this on more than one node.

3. **Confirm total loss is genuine** before proceeding further:
   ```bash
   crsctl query css votedisk
   ```
   Expected output: `Located 0 voting disk(s).` This confirms there is
   nothing to repair in place and a full replace is required.

4. **If the ASM diskgroup that held the voting disks is also gone**,
   create and mount a replacement diskgroup with sufficient failgroups
   (normal redundancy needs 3 failgroups for voting disks; high redundancy
   needs 5) before proceeding. Example (adjust disks/redundancy to your
   environment):
   ```sql
   -- Connect as sysasm on the exclusive-mode node
   CREATE DISKGROUP VOTEDG NORMAL REDUNDANCY
     FAILGROUP FG1 DISK '/dev/oracleasm/disks/VOTE1'
     FAILGROUP FG2 DISK '/dev/oracleasm/disks/VOTE2'
     FAILGROUP FG3 DISK '/dev/oracleasm/disks/VOTE3'
     ATTRIBUTE 'compatible.asm' = '19.0.0.0.0';
   ```
   If the original diskgroup and its disks are intact and only the voting
   files themselves were corrupted, skip this step — just mount the
   existing diskgroup:
   ```bash
   asmcmd mount VOTEDG
   ```

5. **Recreate the voting files** in the target diskgroup:
   ```bash
   crsctl replace votedisk +VOTEDG
   ```
   Expected output includes a line similar to:
   ```
   Successful addition of voting disk ...
   Successful replacement of voting disk group with +VOTEDG.
   CRS-4266: Voting file(s) successfully replaced
   ```
   Confirm:
   ```bash
   crsctl query css votedisk
   ```
   Expected: the correct number of voting disk copies now listed as valid
   (3 for normal redundancy, 5 for high redundancy, 1 for external).

> **Point of no return:** `crsctl replace votedisk` in exclusive mode
> commits the new voting file layout immediately — there is no separate
> "commit" step. Once it reports success, the old (lost) voting disk
> configuration is gone and cannot be un-replaced; this is expected and is
> the goal of the recovery, but do not run it a second time against a
> different diskgroup by mistake.

6. **Leave exclusive mode and restart Clusterware normally** (root, on the
   exclusive-mode node first, then all other nodes):
   ```bash
   crsctl stop crs -f
   crsctl start crs
   ```
   Then, on every remaining node (root):
   ```bash
   crsctl start crs
   ```
   If OCR was also affected and `-nocrs` was used, OCR must be restored
   from backup (`ocrconfig -restore`) before or during this step — see the
   separate OCR recovery procedure; this SOP assumes OCR is otherwise
   intact.

7. **Verify cluster-wide health** on every node:
   ```bash
   crsctl check crs
   crsctl stat res -t
   ```

## 6. Validation / Post-Checks

Run on every node:

```bash
# Confirm voting disk count/location matches expected redundancy
crsctl query css votedisk

# Confirm every node's Clusterware stack is fully up
crsctl check crs

# Confirm all cluster resources are back online
crsctl stat res -t

# Confirm cluster-wide health
crsctl check cluster -all

# Formal Oracle-recommended health check after any voting file change
cluvfy comp vdisk -n racnode1,racnode2,racnode3 -verbose
```

- [ ] `crsctl query css votedisk` shows the expected number of copies, all
      valid, spread across the correct failgroups
- [ ] `crsctl check crs` reports all four daemons (CRS, CSS, EVM, and — if
      applicable — CRSD) online on every node
- [ ] All previously running databases, listeners, and services are back
      `ONLINE` in `crsctl stat res -t`
- [ ] `cluvfy comp vdisk` reports no fatal errors
- [ ] Application connectivity confirmed restored end-to-end

## 7. Rollback Plan

Voting disk recovery is itself a recovery action; there is no "rollback" in
the traditional sense once `crsctl replace votedisk` succeeds — the new
voting file layout **is** the current state of the cluster.

- **If exclusive-mode start (Step 2, Path B) fails:** do not force further
  action manually. Capture `$GRID_HOME/log/<hostname>/cssd/ocssd.log` and
  `crsctl` command output, and escalate to Oracle Support (Sev 1 SR) with
  MOS Doc ID 1364971.1 referenced — this is one of the few scenarios in this
  repository where a live Oracle Support engagement is the safer path if
  the standard procedure does not proceed cleanly.
- **If `crsctl replace votedisk` fails partway (Step 5, Path B):** re-run
  `crsctl query css votedisk` to check current state before retrying; it is
  generally safe to re-run `crsctl replace votedisk` against the same
  diskgroup while still in exclusive mode.
- **If normal restart (Step 6/7) fails on a subset of nodes:** leave healthy
  nodes running; troubleshoot the failing node individually with
  `crsctl start crs` and review `alertcrsd.log` on that node — this does not
  require repeating the exclusive-mode recovery.
- **If the wrong diskgroup was targeted in Path B Step 5:** this is not
  reversible via a "rollback" — you must repeat Steps 4–5 against the
  correct diskgroup while still in exclusive mode, before leaving exclusive
  mode in Step 6.

## 8. Communication

Total loss of all voting disks is a full cluster (and typically full
database) outage — notify the incident management / NOC channel and
application stakeholders immediately per your incident process, before or
in parallel with starting recovery (do not delay recovery to write a
perfect notification). For partial loss, notify the storage/infrastructure
team of the underlying disk/LUN failure (Section 5A Step 2) since this SOP
only restores voting disk redundancy, not the physical storage fault, and
send a routine (non-urgent) status update to the DBA team distribution
list once redundancy is confirmed restored (Section 6).

## 9. Known Issues / Gotchas

- Confusing **partial loss** with **total loss** is the most common
  mistake — running exclusive-mode recovery (Path B) against a cluster that
  is still up unnecessarily brings down every other node. Always confirm
  with `crsctl check cluster -all` before choosing a path.
- `crsctl start crs -excl -nocrs` must be run on **only one** node. Running
  it on a second node concurrently causes split-brain-like conflicts in
  exclusive mode.
- `-nocrs` is only needed when the OCR-holding diskgroup is also
  unavailable. If OCR is intact and mountable, `crsctl start crs -excl`
  (without `-nocrs`) is sufficient and lets CRSD start, simplifying
  subsequent steps — use `-nocrs` only when you have confirmed OCR is also
  affected.
- Voting disks and OCR are commonly co-located in the same ASM diskgroup by
  design (Oracle's recommended layout) — a diskgroup-level failure often
  means both need recovery; always check `ocrcheck` alongside
  `crsctl query css votedisk` at the start of any incident.
- After `crsctl replace votedisk`, always re-run `crsctl query css
  votedisk` to positively confirm the count and status — do not assume
  success from the absence of an error alone.
- ASM disk header corruption on the surviving diskgroup can masquerade as
  "total loss" of voting disks when it is actually a storage-layer issue;
  rule this out with `kfed read` on the underlying devices before assuming
  a full diskgroup rebuild is required.

## 10. References

- Oracle Database documentation — *Managing Oracle Cluster Registry and
  Voting Files* (19c):
  https://docs.oracle.com/en/database/oracle/oracle-database/19/cwadd/managing-oracle-cluster-registry-and-voting-files.html
  — verified: exclusive-mode start syntax, `crsctl replace votedisk`
  syntax, and the general recovery sequence in this SOP match this source.
- MOS Doc ID 1364971.1 — Cluster Startup and Voting Disk/OCR Reconfiguration
  troubleshooting reference (confirm exact title/applicability for your
  patch level via My Oracle Support search)
- MOS Doc ID 294430.1 — Voting Disk / Vote File in Oracle Clusterware
- br8dba.com — *Restore loss of all VOTE disks* (community reference,
  11.2.0.3-based walkthrough): https://www.br8dba.com/restore-loss-of-all-vote-disks/
  — used for topic/structure ideas only; commands verified against
  docs.oracle.com above, not copied from this source.
- Internal: `05-high-availability-rac/06-cluvfy-health-checks.md`,
  `07-backup-recovery/` (OCR backup/restore procedures)

## 11. Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-08-16 | DBA Team | Initial version |
