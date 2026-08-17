# SOP: Delete a Node from a RAC Cluster (Full Removal, Including Software)

**Category:** High Availability / RAC
**Applies to:** Oracle 19c Grid Infrastructure + RAC, Linux x86-64 (RHEL/OEL 7/8/9), 3-node cluster `RACCLUSTER`
**Risk Level:** Critical
**Estimated Duration:** 2–4 hours
**Downtime Required:** No cluster-wide downtime — remaining nodes stay online; the target node's instance and services become unavailable during and after
**Owner:** DBA Team
**Last Reviewed:** 2026-08-16
**Review Cadence:** Every major GI version change

---

## 1. Purpose

Provides the definitive, permanent procedure for removing a node
(`racnode3`) from an Oracle 19c RAC cluster (`RACCLUSTER`) — stopping the
database instance, deinstalling the Grid Infrastructure and database software
from the target node, deleting it from cluster membership, and cleaning up
its VIP — when that node is being decommissioned or repurposed and will
**not** rejoin the cluster in its current form.

## 2. Scope

Covers the full permanent removal of a cluster node, including software
deinstallation, for Linux, node-local (non-shared) GI and DB homes. Does
**not** cover: temporarily removing a node from active membership while
leaving the software installed for planned maintenance (see
`02b-remove-node-without-software-deletion.md` — use that SOP instead if the
node will rejoin later); re-adding a node after full deletion (see
`03-readd-previously-deleted-node.md`). Applies to Prod and Non-Prod.

## 3. Prerequisites

- [ ] Change ticket approved and change window confirmed
- [ ] Confirmed with application/service owners that the target node's
      instance and any services pinned to it can be stopped/relocated
- [ ] Current OCR backup taken and confirmed restorable:
      `ocrconfig -manualbackup` (verify with `ocrconfig -showbackup`)
- [ ] Voting disk and OCR locations documented (`crsctl query css votedisk`,
      `ocrcheck`) in case of unexpected cluster instability during removal
- [ ] Confirmed the node being deleted is genuinely being decommissioned —
      if there is any chance it will return, use
      `02b-remove-node-without-software-deletion.md` instead, since
      deinstallation here is not trivially reversible
- [ ] Backups of the database (RMAN) are current and unaffected by removing
      one instance (this procedure does not touch database files, only the
      instance/thread on the removed node)
- [ ] Root/sudo access confirmed on a **surviving** node for the
      `crsctl delete node` step
- [ ] Rollback plan reviewed (Section 7) — understand that rollback here
      means re-adding the node via the full add-node procedure, not a quick
      undo
- [ ] Stakeholders notified of the change window (Section 8)

## 4. Pre-Checks

Run from a **surviving** node (`racnode1`) as the `grid` OS user unless noted.

```bash
# Confirm current membership and pin status of the node to be deleted
olsnodes -s -t
# Example expected output:
#   racnode1  Active  Unpinned
#   racnode2  Active  Unpinned
#   racnode3  Active  Unpinned   <- node to be deleted

# Confirm overall cluster health before making any change
crsctl check cluster -all
crsctl stat res -t

# Confirm what is currently running on the node to be deleted
crsctl stat res -t -w "NAME co racnode3"
srvctl status database -d ORCL

# Confirm the database instance name/thread mapped to the target node
srvctl config database -d ORCL | grep -i instance
```

Expected: cluster healthy, all nodes `Active`, and a clear, confirmed mapping
of which DB instance (e.g. `ORCL3`) runs on `racnode3`.

## 5. Procedure

Follow this sequence precisely — order matters, and several steps must run
from a specific node.

1. **Unpin the node if pinned.** Dynamic RAC nodes are typically already
   `Unpinned`; check first and only unpin if needed **(root, from any node)**:
   ```bash
   olsnodes -s -t
   crsctl unpin css -n racnode3   # only if listed as pinned
   ```

2. **Stop the database instance(s) on the node being deleted.** From any
   node, as `oracle` (or `grid` if using `srvctl` with cluster credentials):
   ```bash
   srvctl stop instance -d ORCL -n racnode3
   srvctl status instance -d ORCL -i ORCL3
   ```
   Also stop and, if desired, remove any node-specific services pinned to
   `racnode3` before proceeding:
   ```bash
   srvctl config service -d ORCL
   srvctl stop service -d ORCL -s <service_name> -n racnode3
   ```

3. **Deinstall the Oracle software from the target node itself,** logged in
   **on `racnode3`**. Run the database Oracle Home deinstall first, then the
   Grid Infrastructure deinstall. For node-local (non-shared) homes:
   ```bash
   # As oracle, on racnode3 — remove the DB Oracle Home from this node only
   $ORACLE_HOME/deinstall/deinstall -local

   # As grid, on racnode3 — remove the Grid Infrastructure home from this node only
   $GRID_HOME/deinstall/deinstall -local
   ```
   If the GI home is instead a **shared** home (not the convention used in
   this repo, but covered for completeness), do not use `deinstall -local`;
   instead run, on the target node **(root)**:
   ```bash
   $GRID_HOME/crs/install/rootcrs.sh -deconfig -force
   ```
   followed by, from any surviving node:
   ```bash
   $GRID_HOME/oui/bin/runInstaller -detachHome ORACLE_HOME=$GRID_HOME -silent -local
   ```

   > **Point of no return:** once `deinstall -local` completes on
   > `racnode3`, the Oracle software is gone from that host. From here,
   > bringing `racnode3` back requires a fresh install/add-node, not a
   > restart of services.

4. **Delete the node from cluster configuration.** From a **surviving** node
   (`racnode1`), **as root**:
   ```bash
   crsctl delete node -n racnode3
   ```

5. **Update the Oracle Inventory on the remaining nodes** to remove
   `racnode3` from the node list for both homes, run from a surviving node
   **as the respective software owner**:
   ```bash
   # Grid home, as grid
   $GRID_HOME/oui/bin/runInstaller -updateNodeList \
     ORACLE_HOME=$GRID_HOME "CLUSTER_NODES=racnode1,racnode2" CRS=true -silent

   # DB home, as oracle
   $ORACLE_HOME/oui/bin/runInstaller -updateNodeList \
     ORACLE_HOME=$ORACLE_HOME "CLUSTER_NODES=racnode1,racnode2" -silent
   ```

6. **Clean up the VIP for the deleted node,** from a surviving node **as
   root** (or `grid` with the appropriate privilege):
   ```bash
   srvctl config vip -node racnode3
   srvctl stop vip -vip <racnode3_vip_name>
   srvctl remove vip -vip <racnode3_vip_name>
   ```

7. **Remove the instance's redo thread and undo tablespace if not already
   cleared automatically** — normally `srvctl` instance removal via DBCA
   handles this, but if the instance was stopped/deconfigured manually,
   confirm via DBCA or manually:
   ```sql
   -- Connect to a surviving instance
   ALTER DATABASE DISABLE THREAD 3;
   -- Drop the now-unused undo tablespace for instance 3 if dedicated
   DROP TABLESPACE UNDOTBS3 INCLUDING CONTENTS AND DATAFILES;
   ```
   Prefer running `dbca -silent -deleteInstance` **before** Step 3 if the
   instance and its thread/undo tablespace still need clean, tool-driven
   removal — sequence this ahead of the software deinstall in your change
   plan if so.

## 6. Validation / Post-Checks

```bash
# Formal Oracle post-delete verification
$GRID_HOME/bin/cluvfy stage -post nodedel -n racnode3 -verbose

# Confirm the node no longer appears in cluster membership
olsnodes -s -t
# racnode3 must NOT appear

# Confirm remaining cluster resources are healthy
crsctl stat res -t
crsctl check cluster -all

# Confirm the database no longer expects an instance on the deleted node
srvctl config database -d ORCL
sqlplus -s / as sysdba <<'SQL'
SELECT instance_name, host_name FROM gv$instance ORDER BY inst_id;
SQL

# Confirm the VIP resource is gone
srvctl config vip -node racnode3
# Expected: error / resource not found
```

- [ ] `cluvfy stage -post nodedel` reports overall result `PASSED`
- [ ] `olsnodes -s -t` no longer lists `racnode3`
- [ ] Remaining instances (`ORCL1`, `ORCL2`) are `OPEN` and unaffected
- [ ] VIP and any node-specific services for `racnode3` no longer exist
- [ ] Oracle Inventory (`opatch lsinventory -detail`) on `racnode1`/`racnode2`
      no longer lists `racnode3` in the node list for either home

## 7. Rollback Plan

There is no single-command rollback for this procedure — deinstalling
software and deleting cluster membership are deliberately hard to reverse to
prevent accidental data loss. Recovery path depends on where the failure
occurred:

- **Failed before Step 3 (software still on target node, instance stopped):**
  Simply restart the instance (`srvctl start instance -d ORCL -n racnode3`)
  and investigate; no cluster state was changed.

- **Failed during/after Step 3 (software deinstalled) but before Step 4
  (node not yet deleted from cluster):** The node is now a broken cluster
  member with no software. Complete Step 4 (`crsctl delete node`) to
  formally remove it from cluster configuration rather than leaving it in a
  half-deleted state, then treat full restoration as a fresh add-node using
  `01-add-node-to-rac-cluster.md`.

- **Failed after Step 4 (node deleted from cluster):** The only path back is
  the full add-node procedure (`01-add-node-to-rac-cluster.md`) treating
  `racnode3` as a brand-new node — reinstall OS packages if needed,
  reinstall Grid Infrastructure and DB homes, re-add the instance via DBCA.
  If the node was previously a cluster member and is being re-added, use
  `03-readd-previously-deleted-node.md` instead, which includes the
  stale-configuration cleanup checks this scenario requires.

- **If OCR or voting disk issues appear mid-procedure:** Stop immediately,
  do not proceed further, and restore OCR from the pre-change backup taken
  in Section 3 if corruption is confirmed:
  ```bash
  ocrconfig -restore <backup_file>
  ```
  Escalate to Oracle Support before restoring OCR in a production cluster —
  this is a high-impact action affecting all nodes.

## 8. Communication

Notify application/service owners at least one change-window cycle in
advance that the target node's instance will be permanently removed and any
connections/services pinned to it must fail over. Notify the network/storage
teams so the VIP and any dedicated storage paths for the decommissioned node
can be reclaimed after Section 6 passes. Send a completion notice confirming
`cluvfy stage -post nodedel` passed and remaining instances are healthy.

## 9. Known Issues / Gotchas

- Always confirm `olsnodes -s -t` pin status **before** attempting
  `crsctl unpin css` — running it against an already-unpinned node is
  harmless but noisy; confirm the actual state first.
- If `srvctl stop instance` fails because the instance is already down
  (e.g. host already crashed), proceed directly to Step 3 — do not treat
  this as a blocker.
- Deinstalling the GI home without first properly stopping/removing the DB
  Home on the same node can leave orphaned entries in the Oracle Inventory;
  always deinstall the DB Home before the GI Home on the target node.
- `crsctl delete node` must run from a **surviving** node, never from the
  node being deleted — it manages cluster-wide OCR state and requires an
  active member's CRS stack.
- If the target node is unreachable/dead (hardware failure) and Step 3
  cannot be run interactively there, skip the local deinstall and proceed
  directly to `crsctl delete node -n racnode3` from a surviving node; the
  dead node's software will simply never be reachable to clean up — document
  this deviation in the change record.
- After deletion, stale entries can sometimes linger in
  `$GRID_HOME/network/admin/listener.ora` or `tnsnames.ora` on surviving
  nodes if manually edited previously — always regenerate/verify listener
  configuration through `srvctl`, not hand-edited files.

## 10. References

- Oracle Database documentation — *Adding and Deleting Cluster Nodes* (19c):
  https://docs.oracle.com/en/database/oracle/oracle-database/19/cwadd/adding-and-deleting-cluster-nodes.html
- MOS Doc ID 1595570.1 — Grid Infrastructure Cluster Node Addition/Deletion
  best practices (confirm applicability to your exact patch level)
- MOS Doc ID 269320.1 — OCR/OLR backup and recovery reference
- oracle-base.com — Adding and Deleting Nodes on Oracle Grid Infrastructure
  (community reference; verify commands against docs.oracle.com above)
- Internal: `02b-remove-node-without-software-deletion.md`,
  `03-readd-previously-deleted-node.md`,
  `01-add-node-to-rac-cluster.md`

## 11. Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-08-16 | DBA Team | Initial version |
