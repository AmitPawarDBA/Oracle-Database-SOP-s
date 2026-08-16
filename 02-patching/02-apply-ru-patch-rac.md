# SOP: Apply Quarterly RU Patch to RAC Cluster (Rolling, OPatchAuto)

**Category:** Patching
**Applies to:** Oracle 19c / 21c, RAC (2+ nodes), Grid Infrastructure +
Database homes, Linux x86-64 (RHEL/OEL 7/8/9)
**Risk Level:** High
**Estimated Duration:** 2–4 hours for a 2-node cluster (scales with node
count); rolling mode keeps the database available throughout
**Downtime Required:** No cluster-wide outage if run in rolling mode
(each node briefly leaves the cluster in turn); full outage required only
if run non-rolling
**Owner:** DBA Team
**Last Reviewed:** 2026-08-16
**Review Cadence:** Every quarter (aligned to Oracle RU release cadence)

---

## 1. Purpose

Provides a repeatable, auditable procedure for applying a quarterly
Release Update (RU) to both the Grid Infrastructure (GI) home and the
Database (DB) home across all nodes of an Oracle RAC cluster, using
`opatchauto` in rolling mode so the cluster remains available to
application connections throughout the patch window.

## 2. Scope

Covers rolling patching of GI + RDBMS homes on a RAC cluster using
`opatchauto apply`. Does **not** cover single-instance patching (see
`02-patching/01-apply-quarterly-ru-patch.md`), Grid Infrastructure major
version upgrades (see `03-upgrades/`), or Exadata cell/image patching
(see `13-cloud-exadata-oci/`).

## 3. Prerequisites

- [ ] Change ticket approved and rolling-patch window confirmed
- [ ] Target RU and combo/GI RU patch numbers identified from the release
      schedule (MOS Doc ID 2118136.2) — for RAC, download the **combo
      patch for GI + DB RU** where available to simplify the apply
- [ ] Patch zip checksum verified on all nodes (stage centrally on shared
      storage or copy identically to each node's local staging area)
- [ ] OPatch and OPatchAuto both current on **every node** (patch
      6880880) — version mismatch across nodes is a common failure cause
- [ ] Conflict check run on every node against both GI home and DB home
- [ ] Cluster health confirmed green (`crsctl check cluster`, `cluster
      resource status`) before starting
- [ ] Sufficient free space on every node for both homes
      (`$GRID_HOME`, `$ORACLE_HOME`, `/tmp`)
- [ ] Full RMAN backup and OCR/voting disk backup taken and validated
- [ ] `root` (or `sudo`) access confirmed on every node — OPatchAuto
      requires root privileges to orchestrate CRS stop/start
- [ ] SCAN listener and node VIP failover behavior understood by the app
      team (connections will fail over node-by-node during the rolling
      window)
- [ ] Rollback plan reviewed (Section 7) and agreed with change approver

## 4. Pre-Checks

```bash
# As grid/oracle OS user on each node, and as root where noted
export GRID_HOME=/u01/app/19.0.0/grid
export ORACLE_HOME=/u01/app/oracle/product/19.0.0/dbhome_1
export PATH=$GRID_HOME/OPatch:$ORACLE_HOME/OPatch:$PATH

# 1. Confirm OPatch/OPatchAuto version on EVERY node
opatch version
$GRID_HOME/OPatch/opatchauto version

# 2. Confirm current RU level in each home
$GRID_HOME/OPatch/opatch lsinventory -bugs_fixed | grep -i "DATABASE RU"
$ORACLE_HOME/OPatch/opatch lsinventory -bugs_fixed | grep -i "DATABASE RU"

# 3. Confirm cluster health from any one node
crsctl check cluster -all
crsctl stat res -t

# 4. Stage and unzip the combo/GI+DB RU on each node (or shared location
#    visible to all nodes)
mkdir -p /u01/software/patches/${RU_PATCH_NUM}
cd /u01/software/patches/${RU_PATCH_NUM}
unzip -q p${RU_PATCH_NUM}_190000_Linux-x86-64.zip

# 5. Run conflict check against BOTH homes, on each node, as root
#    (opatchauto orchestrates this; can also be run manually per-home)
opatch prereq CheckConflictAgainstOHWithDetail -ph ./${RU_PATCH_NUM} \
  -oh $GRID_HOME
opatch prereq CheckConflictAgainstOHWithDetail -ph ./${RU_PATCH_NUM} \
  -oh $ORACLE_HOME

# 6. Confirm space on each node
df -h $GRID_HOME $ORACLE_HOME /tmp

# 7. Capture pre-patch baseline from the database
sqlplus -s / as sysdba <<'EOF'
SET LINES 200 PAGES 100
SELECT inst_id, status FROM gv$instance ORDER BY inst_id;
SELECT patch_id, version, status, action, action_time
FROM dba_registry_sqlpatch ORDER BY action_time;
EOF
```

Expected: matching OPatch/OPatchAuto versions on all nodes; conflict
checks pass clean against both homes on every node; cluster fully up
(`crsctl check cluster -all` reports all components online); all
instances `OPEN` in `gv$instance`.

## 5. Procedure

OPatchAuto rolling mode patches one node at a time: it stops CRS on the
target node (relocating/failing over services to surviving nodes),
applies the patch to both GI and DB homes on that node, restarts CRS,
runs `datapatch` once the last node completes, and moves to the next
node. Run these steps from **each node in turn**, or invoke a single
`opatchauto` command from one node with `-oh` scoped appropriately per
Oracle's guidance for the patch being applied — confirm the exact
invocation in the patch README, as syntax varies slightly by RU.

1. Take a full RMAN backup and an OCR/voting disk backup if not already
   current for this window:
   ```bash
   ocrconfig -manualbackup
   ```
2. On **node 1**, as `root`, run OPatchAuto in rolling mode against both
   homes:
   ```bash
   cd /u01/software/patches/${RU_PATCH_NUM}/${RU_PATCH_NUM}
   $GRID_HOME/OPatch/opatchauto apply \
     /u01/software/patches/${RU_PATCH_NUM}/${RU_PATCH_NUM} \
     -oh $GRID_HOME,$ORACLE_HOME
   ```
   OPatchAuto will:
   - Detect the node is part of a RAC cluster and default to rolling mode
   - Stop CRS-managed resources and CRS itself on this node only
   - Apply the RU to the GI home, then the DB home
   - Restart CRS and validate resources come back online on this node
3. Monitor the OPatchAuto session log in real time:
   ```bash
   tail -f $GRID_HOME/cfgtoollogs/opatchauto/opatchauto<timestamp>.log
   ```
   Confirm `OPatchAuto successful` for node 1 before proceeding.
4. Confirm node 1's resources rejoined the cluster cleanly:
   ```bash
   crsctl stat res -t -w "TARGET = ONLINE"
   ```
5. Repeat steps 2–4 on **node 2**, then each subsequent node in turn,
   waiting for each node to fully rejoin before moving to the next. Do
   not patch two nodes simultaneously — this defeats the purpose of
   rolling mode and risks a full cluster outage.
6. OPatchAuto runs `datapatch` automatically after the **last** node
   completes (GI/DB RU applies are node-local; the SQL dictionary change
   is cluster-wide and only needs to run once). Confirm it ran, or run it
   manually from any one node if it did not:
   ```bash
   cd $ORACLE_HOME/OPatch
   ./datapatch -verbose
   ```
7. If an OJVM RU is required, apply it after the base RU has completed on
   all nodes, again via `opatchauto apply` in rolling mode, one node at a
   time.
8. Recompile invalid objects from any one instance:
   ```sql
   @$ORACLE_HOME/rdbms/admin/utlrp.sql
   ```

> **Point of no return:** once `opatchauto apply` completes on the first
> node and that node has rejoined the cluster on the patched binaries,
> the cluster is running mixed patch levels until all nodes complete.
> This is an expected and supported transient state during rolling
> patching, but do not leave the cluster in this mixed state longer than
> the change window — complete all nodes in the same window.

## 6. Validation / Post-Checks

```bash
# Confirm patch level matches on EVERY node
for node in node1 node2; do
  ssh $node "$GRID_HOME/OPatch/opatch lsinventory -bugs_fixed | grep -i 'DATABASE RU'"
  ssh $node "$ORACLE_HOME/OPatch/opatch lsinventory -bugs_fixed | grep -i 'DATABASE RU'"
done

# Confirm cluster and all instances healthy
crsctl check cluster -all
crsctl stat res -t
```

```sql
-- Confirm all instances open post-patch
SELECT inst_id, status, version_full FROM gv$instance ORDER BY inst_id;

-- Confirm datapatch success (cluster-wide, single row set applies to all instances)
SELECT patch_id, patch_type, version, status, action, action_time
FROM dba_registry_sqlpatch ORDER BY action_time DESC;

SELECT * FROM dba_registry_sqlpatch WHERE status NOT IN ('SUCCESS');

-- Confirm invalid objects at or below baseline
SELECT count(*) FROM dba_objects WHERE status = 'INVALID';
```

- [ ] Identical RU level reported by `opatch lsinventory` on every node,
      for both GI home and DB home
- [ ] `crsctl check cluster -all` reports all nodes/components online
- [ ] All instances `OPEN` in `gv$instance`
- [ ] `dba_registry_sqlpatch` shows `STATUS = SUCCESS` for the new RU
      (and OJVM RU, if applied)
- [ ] Invalid object count at or below pre-patch baseline
- [ ] SCAN listener and all node listeners accepting connections;
      application failover/reconnect validated during the window

## 7. Rollback Plan

Rolling rollback follows the same node-by-node principle, in reverse:

1. On the node to be rolled back, as `root`:
   ```bash
   $GRID_HOME/OPatch/opatchauto rollback \
     /u01/software/patches/${RU_PATCH_NUM}/${RU_PATCH_NUM} \
     -oh $GRID_HOME,$ORACLE_HOME
   ```
2. Confirm the node's CRS resources rejoin cleanly at the prior patch
   level before rolling back the next node:
   ```bash
   crsctl stat res -t -w "TARGET = ONLINE"
   ```
3. Repeat for every node that received the patch, working through them
   one at a time.
4. Once all nodes are rolled back at the OPatch level, run `datapatch
   -verbose` from any one instance to reconcile the dictionary back to
   the pre-patch SQL state.
5. If `opatchauto rollback` fails on a node or leaves CRS in an
   inconsistent state, engage Oracle Support with the OPatchAuto session
   log (`$GRID_HOME/cfgtoollogs/opatchauto/`) — do not attempt manual
   binary-level fixes against a GI home without guidance, as this risks
   cluster-wide outage.
6. As a last resort for a severely broken node, restore that node's
   Oracle Homes from a pre-patch filesystem backup/snapshot and re-add it
   to the cluster per Grid Infrastructure node addition procedures.
7. Restore OCR from the manual backup taken in Procedure step 1 only if
   OCR corruption is confirmed — this is a cluster-wide action and should
   not be taken lightly:
   ```bash
   ocrconfig -restore <backup_file>
   ```

## 8. Communication

- **Before:** Notify application owners of the rolling-patch window;
  emphasize that individual node failovers may cause brief connection
  blips but the service as a whole remains available. Confirm window in
  the change ticket, including estimated per-node duration × node count.
- **During:** Post an update after each node completes and rejoins the
  cluster (e.g. "Node 1 of 3 complete, cluster healthy, proceeding to
  node 2").
- **After:** Confirm all nodes at the new patch level, cluster health
  green, and application validation complete in the change ticket; send
  closure notice with the new patch level to stakeholders.

## 9. Known Issues / Gotchas

- **Mismatched OPatch/OPatchAuto versions across nodes** cause
  unpredictable failures mid-rollout — verify identical versions on every
  node before starting, not just the node you begin on.
- **OJVM patch conflicts:** as with single-instance, the OJVM RU can
  conflict with the DB RU; run conflict checks for both against both
  homes on every node before the window, and apply the base RU across
  all nodes before starting the OJVM RU rollout.
- **datapatch runs cluster-wide, not per-node:** it only needs to
  execute once after the last node completes; running it prematurely
  (before all nodes are on the new binaries) can leave the dictionary
  patched while some instances still run old binaries — always wait
  until every node has completed the OPatchAuto apply.
- **CRS fails to stop cleanly on a node:** usually caused by resources
  with `AUTO_START` dependencies or application VIPs not relocating in
  time; check `crsctl stat res -t` for resources stuck in
  `INTERMEDIATE` state before forcing anything.
- **Invalid objects after patch:** compare against the pre-patch
  baseline; a small number of transient invalids is expected and
  resolved by `utlrp.sql`.
- **Mixed patch-level windows left open too long:** if the rolling patch
  window is interrupted (e.g. only 1 of 3 nodes completed), do not leave
  the cluster in that state across a business day — either complete the
  rollout or roll the patched node(s) back before ending the window.
- **Shared vs. per-node staging:** if patch files are staged on shared
  storage visible to all nodes, confirm file locking/permissions don't
  cause a node to read a partially-written file if staging happens
  concurrently with patching.
- Always review the RU's README `opatchauto` section — exact command
  syntax (single combined invocation vs. separate GI/DB invocations)
  varies by release and patch type.

## 10. References

- MOS Doc ID 2118136.2 — Primary Note for Database Proactive Patch
  Program (RU/RUR quarterly schedule and patch numbers)
- MOS Doc ID 1585822.1 — Database Patch Set Update (PSU)/RU FAQ
- MOS Doc ID 6880880 — Latest OPatch version download
- MOS Doc ID 1929745.1 — OJVM patching FAQ and conflict guidance
- MOS Doc ID 2419319.1 — OPatchAuto rolling patch procedure for RAC
- MOS Doc ID 12332676.8 — Known issues index for OPatchAuto
- Oracle Grid Infrastructure Patching Guide (version-specific)
- Internal: `07-backup-recovery/` for RMAN and OCR/voting disk backup
  procedures
- Internal: `02-patching/01-apply-quarterly-ru-patch.md` for
  single-instance patch procedure
- Internal: `05-high-availability-rac/` for cluster health and CRS
  operations reference

## 11. Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-08-16 | DBA Team | Initial version |
