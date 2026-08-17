# SOP: Relocate OCR and Voting Disks to a New ASM Diskgroup

**Category:** High Availability / RAC
**Applies to:** Oracle 19c Grid Infrastructure + RAC, Linux x86-64 (RHEL/OEL 7/8/9), 3-node cluster `RACCLUSTER`
**Risk Level:** Critical
**Estimated Duration:** 1–2 hours
**Downtime Required:** No — both OCR and voting disk relocation are online operations when done correctly, but treat as a change-controlled maintenance window given the blast radius
**Owner:** DBA Team
**Last Reviewed:** 2026-08-16
**Review Cadence:** Every major GI version change, or whenever storage is re-architected

---

## 1. Purpose

Describes how to relocate the Oracle Cluster Registry (OCR) and/or the
Cluster Synchronization Services (CSS) voting disks from an existing ASM
diskgroup (e.g. `+DATA`) to a new, dedicated ASM diskgroup (e.g.
`+OCR_VOTE`) in the `RACCLUSTER` Grid Infrastructure, without an outage.

## 2. Scope

Covers online relocation of OCR and voting disks between ASM diskgroups on
Linux Grid Infrastructure 19c. Does **not** cover: recovering from the loss
of all voting disks or a corrupted OCR (a distinct, outage-driven recovery
scenario requiring `crsctl start crs -excl` and is out of scope here — treat
that as a separate incident-response SOP); relocating OCR/voting disks to
raw devices or a clustered filesystem instead of ASM (commands differ).
Applies to Prod and Non-Prod.

## 3. Prerequisites

- [ ] Change ticket approved and change window confirmed
- [ ] New target ASM diskgroup (`+OCR_VOTE`) created in advance, sized and
      redundancy-configured appropriately:
  - **Voting disks** require an **odd number** of failure groups for
    reliable majority-vote arithmetic; diskgroup redundancy (EXTERNAL,
    NORMAL, HIGH) determines how many voting files are created (1, 3, or 5
    respectively) — plan physical failure group placement accordingly
  - **OCR** requires the target diskgroup to have `COMPATIBLE.ASM` and
    `COMPATIBLE.RDBMS` attributes at a minimum level compatible with 19c GI
    (`19.0.0.0.0` or higher recommended)
- [ ] Diskgroup confirmed mounted on **all** cluster nodes:
      `srvctl status diskgroup -g OCR_VOTE`
- [ ] Current OCR manual backup taken and confirmed restorable:
      `ocrconfig -manualbackup` / `ocrconfig -showbackup`
- [ ] Current voting disk configuration documented in full:
      `crsctl query css votedisk`
- [ ] Confirmed sufficient free space in the target diskgroup for OCR
      (typically < 500MB per copy, but Oracle recommends generous headroom)
      and voting files (small, but redundancy-dependent copy count)
- [ ] Rollback plan reviewed (Section 7)
- [ ] Stakeholders notified of the change window (Section 8)

## 4. Pre-Checks

Run from any cluster node as the `grid` OS user unless noted.

```bash
# Confirm current OCR location(s) and integrity
ocrcheck

# Confirm current voting disk location(s)
crsctl query css votedisk

# Confirm the new target diskgroup exists, is mounted everywhere, and has
# sufficient free space
asmcmd lsdg
srvctl status diskgroup -g OCR_VOTE

# Confirm diskgroup compatibility attributes support OCR storage
asmcmd lsattr -G OCR_VOTE -l

# Confirm overall cluster health before touching OCR/voting disk config —
# never attempt this on a cluster with existing CRS instability
crsctl check cluster -all
crsctl stat res -t
```

Expected: `ocrcheck` reports no logical corruption; `crsctl query css
votedisk` lists all existing voting files healthy; the target diskgroup is
`MOUNTED` on every node; cluster health checks show no pre-existing
failures. Do not proceed if any of these are not clean — resolve first.

## 5. Procedure

OCR and voting disk relocation are independent operations; you can do either
or both in the same window. Order does not matter between them, but complete
one fully (including validation) before starting the other to simplify
troubleshooting if something goes wrong.

### 5a. Relocate OCR

1. **Add the new diskgroup as an additional OCR location** (OCR supports up
   to 5 simultaneous locations, so adding does not remove the existing
   copy):
   ```bash
   ocrconfig -add +OCR_VOTE
   ```
2. **Verify the new copy is active and synchronized:**
   ```bash
   ocrcheck
   ```
   Confirm the output now lists both `+DATA` and `+OCR_VOTE` as OCR
   locations, with matching device/consistency status.
3. **Remove the old OCR location** once the new copy is confirmed healthy:
   ```bash
   ocrconfig -delete +DATA
   ```

   > **Point of no return:** once the old location is deleted and the new
   > one is the sole/primary copy, reverting means repeating this same
   > add/delete sequence in reverse — there is no "undo" command. Do not
   > run the delete step until Step 2's verification is unambiguous.

### 5b. Relocate Voting Disks

Voting disk relocation in ASM is a single-command replace operation — ASM
handles distributing the correct number of voting files across failure
groups in the target diskgroup based on its redundancy level.

1. **Replace the voting disk diskgroup:**
   ```bash
   crsctl replace votedisk +OCR_VOTE
   ```
2. **Observe the command output directly** — it reports each voting file
   added/removed as part of the operation and will error immediately if the
   target diskgroup cannot support the required failure group count for the
   current redundancy level.

   > **Point of no return:** `crsctl replace votedisk` completes the
   > relocation in one atomic operation (unlike OCR's two-step add/delete);
   > there is no separate "old location still present" checkpoint to pause
   > at. Confirm the target diskgroup fully meets the prerequisites in
   > Section 3 before running this command, not after.

## 6. Validation / Post-Checks

```bash
# Confirm OCR is now hosted in the new diskgroup only, with no corruption
ocrcheck

# Confirm voting disks are now hosted in the new diskgroup
crsctl query css votedisk

# Confirm cluster-wide health remains stable after the change
crsctl check cluster -all
crsctl stat res -t

# Confirm OCR backups continue to run correctly against the new location
ocrconfig -showbackup
```

- [ ] `ocrcheck` shows the OCR device location(s) as `+OCR_VOTE` only, with
      status `OK`/no logical corruption reported
- [ ] `crsctl query css votedisk` lists voting files in `+OCR_VOTE` only,
      matching the expected count for the diskgroup's redundancy level
- [ ] `crsctl check cluster -all` reports all nodes healthy
- [ ] No CRS alerts/errors logged in `$GRID_HOME/log/<hostname>/alert*.log`
      during or immediately after the change
- [ ] Automatic OCR backups (`ocrconfig -showbackup`) continue on schedule
      against the relocated OCR

## 7. Rollback Plan

- **OCR relocation failed after Step 5a.1 (new location added) but before
  Step 5a.3 (old location deleted):** simply remove the newly added,
  problematic location and retain the original:
  ```bash
  ocrconfig -delete +OCR_VOTE
  ```
  No data loss risk — the original `+DATA` copy was never removed.

- **OCR relocation failed after Step 5a.3 (old location already deleted):**
  add the original diskgroup back as a location, then remove the
  problematic new one:
  ```bash
  ocrconfig -add +DATA
  ocrcheck   # confirm sync before proceeding
  ocrconfig -delete +OCR_VOTE
  ```
  If OCR itself is reporting corruption at this point (not just a
  misconfigured location), stop and restore from the pre-change backup
  instead of attempting further location changes:
  ```bash
  ocrconfig -restore <backup_file>
  ```
  Escalate to Oracle Support before restoring OCR in production — this
  affects the entire cluster.

- **Voting disk relocation failed or the target diskgroup proves unsuitable
  after `crsctl replace votedisk`:** re-run the same command pointing back
  at the original diskgroup:
  ```bash
  crsctl replace votedisk +DATA
  ```
  This is safe as long as the original diskgroup is still mounted and has
  not been repurposed. If CSS itself becomes unstable (nodes evicted,
  cluster fails to form) after a voting disk change, this becomes an
  incident-response scenario requiring `crsctl start crs -excl` on a
  surviving node to restore quorum manually — treat that as outside this
  SOP's online-relocation scope and escalate immediately per the incident
  process.

## 8. Communication

Notify the DBA on-call/duty team before starting, since OCR and voting disk
operations affect cluster-wide availability if something goes wrong — this
is not a change to run without a second pair of eyes aware. No application
downtime is expected, so end-user/application team notification can be
informational rather than a change-window request, but should still be
sent. Send a completion notice confirming Section 6 validation passed and
the new diskgroup is now the OCR/voting disk location of record; update
the DR runbook and any storage documentation that references OCR/voting
disk diskgroup names.

## 9. Known Issues / Gotchas

- Voting disk **redundancy is derived from the diskgroup's ASM redundancy
  attribute**, not something you choose per-relocation — EXTERNAL yields 1
  voting file, NORMAL yields 3, HIGH yields 5. Confirm the target
  diskgroup's redundancy matches your intended fault tolerance **before**
  relocating, since changing ASM diskgroup redundancy after creation is
  disruptive.
- `ocrconfig -add`/`-delete` operate one location at a time — do not batch
  multiple diskgroup changes in a single command; always verify with
  `ocrcheck` between each add and delete.
- Attempting `crsctl replace votedisk` against a diskgroup that is not
  mounted on all nodes will fail (or worse, partially succeed) — always
  confirm `srvctl status diskgroup -g <name>` shows `MOUNTED` everywhere
  first.
- If OCR and voting disks currently share the same diskgroup and you are
  relocating both to a new shared diskgroup, complete and validate one
  fully before starting the other (Section 5 sequencing) — troubleshooting
  a combined failure is significantly harder than isolating which
  operation caused an issue.
- After relocating OCR, immediately trigger a fresh manual backup
  (`ocrconfig -manualbackup`) against the new location rather than relying
  solely on the next automatic 4-hour backup cycle — this closes the gap
  between the relocation and a verified-recoverable backup.
- Voting disk relocation does not require stopping CRS on any node when the
  cluster is healthy; if you find yourself needing `crsctl stop crs`
  anywhere in this process, you have likely drifted into recovery-scenario
  territory (loss of majority voting disks) rather than a routine
  relocation — stop and treat it as an incident instead.

## 10. References

- Oracle Database documentation — *Adding and Deleting Cluster Nodes* (19c) —
  cited here for the shared Grid Infrastructure administration context and
  cross-reference to node lifecycle operations that also touch OCR/voting
  disk state:
  https://docs.oracle.com/en/database/oracle/oracle-database/19/cwadd/adding-and-deleting-cluster-nodes.html
- Oracle Clusterware Administration and Deployment Guide (19c) — OCR and
  voting disk administration chapters (`ocrconfig`, `crsctl replace
  votedisk` reference)
- MOS Doc ID 1053147.1 — OCR / Voting disk maintenance operations reference
- MOS Doc ID 269320.1 — OCR/OLR backup and recovery reference
- oracle-base.com — Managing OCR and Voting Disks in ASM (community
  reference; verify commands against docs.oracle.com above)
- Internal: `02-delete-node-from-rac-cluster.md`,
  `01-add-node-to-rac-cluster.md`

## 11. Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-08-16 | DBA Team | Initial version |
