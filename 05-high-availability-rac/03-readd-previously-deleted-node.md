# SOP: Re-Add a Previously Deleted Node to a RAC Cluster

**Category:** High Availability / RAC
**Applies to:** Oracle 19c Grid Infrastructure + RAC, Linux x86-64 (RHEL/OEL 7/8/9), 3-node target cluster `RACCLUSTER`
**Risk Level:** High
**Estimated Duration:** 2–5 hours depending on whether software must be reinstalled
**Downtime Required:** No cluster-wide downtime; online operation against the existing cluster
**Owner:** DBA Team
**Last Reviewed:** 2026-08-16
**Review Cadence:** Every major GI version change

---

## 1. Purpose

Describes how to bring a node (`racnode3`) that was previously a member of
`RACCLUSTER` and was subsequently removed — either via full deletion with
software removal (`02-delete-node-from-rac-cluster.md`) or via a
deconfigure-only removal that left software intact
(`02b-remove-node-without-software-deletion.md`) — back into active cluster
membership, with explicit checks for stale leftover configuration from its
prior membership.

## 2. Scope

Covers re-adding a node that **was previously a member of this specific
cluster**. This is distinct from `01-add-node-to-rac-cluster.md`, which
assumes a genuinely new node with no history in the cluster — the key
addition here is the stale-configuration verification and cleanup this
history requires (leftover OCR/VIP/listener registrations, mismatched patch
levels, orphaned Oracle Inventory entries). Applies to Prod and Non-Prod.

## 3. Prerequisites

- [ ] Change ticket approved and change window confirmed
- [ ] Confirmed **which** prior removal path was used for this node:
  - If removed via `02-delete-node-from-rac-cluster.md` (software
    deinstalled) → treat this largely as a fresh add, but still run every
    stale-configuration check in Section 4 before proceeding, since OCR/DNS
    entries can outlive a software deinstall.
  - If removed via `02b-remove-node-without-software-deletion.md`
    (deconfigured only, software intact) → confirm the node's frozen GI/DB
    Home patch level (recorded at removal time) matches the current cluster
    patch level; patch the idle homes first if the cluster was patched
    while the node was out (see `02-patching/01-apply-quarterly-ru-patch.md`)
- [ ] `grid`/`oracle` OS users and group memberships on `racnode3` still
      match (or have been recreated to match) the current cluster nodes
- [ ] Passwordless SSH re-verified between `racnode3` and all current
      cluster nodes for both `grid` and `oracle` users
- [ ] Shared storage paths for `racnode3` re-verified as still correctly
      presented (device names/permissions can drift after a node has been
      out of service for a while)
- [ ] Network configuration (public/private/VIP) for `racnode3` re-verified
      as still valid — VIP or DNS entries can be reassigned to other
      purposes after a deletion if not tracked carefully
- [ ] Current OCR backup taken and confirmed restorable:
      `ocrconfig -manualbackup`
- [ ] Rollback plan reviewed (Section 7)
- [ ] Stakeholders notified of the change window (Section 8)

## 4. Pre-Checks

Run from an existing cluster node (`racnode1`) as the `grid` OS user unless
noted. These checks specifically target **stale state** that a normal
add-node flow does not need to worry about.

```bash
# Confirm racnode3 is NOT currently listed as a cluster member — a prior
# incomplete removal can leave it half-registered
olsnodes -s -t
# racnode3 must not appear here at all; if it appears in any state,
# STOP and resolve with 02-delete-node-from-rac-cluster.md Section 5/6
# before proceeding

# Confirm no stale VIP resource remains registered for racnode3 from the
# prior membership
srvctl config vip -node racnode3
# Expected: "PRCR-1119 : Failed to look up CRS resource... " or similar
# not-found error. If a VIP configuration IS returned, remove it:
srvctl stop vip -vip <stale_vip_name>
srvctl remove vip -vip <stale_vip_name>

# Confirm no stale listener registration or leftover service definitions
# reference racnode3
srvctl config listener -a
srvctl config service -d ORCL

# Confirm the Oracle Inventory on surviving nodes does not still list
# racnode3 for either home (a leftover entry from an incomplete deletion
# will break add-node's updateNodeList step)
cat /u01/app/oraInventory/ContentsXML/inventory.xml | grep -A2 racnode3
# Expected: no matches. If matches are found, clean up with:
#   runInstaller -updateNodeList ORACLE_HOME=<home> "CLUSTER_NODES=racnode1,racnode2" -silent

# Confirm DNS/hosts entries for racnode3, racnode3-priv, racnode3-vip are
# correct and not repurposed for something else
getent hosts racnode3 racnode3-priv racnode3-vip

# Confirm OCR and voting disk are healthy before adding load
ocrcheck
crsctl query css votedisk
```

If the node's software was left intact (`02b` removal path), also confirm
patch alignment:

```bash
# On racnode3
$GRID_HOME/OPatch/opatch lsinventory -detail | grep -i "Patch"

# On racnode1 (current cluster baseline)
$GRID_HOME/OPatch/opatch lsinventory -detail | grep -i "Patch"
```

Expected: patch levels match exactly. If they do not, patch `racnode3`'s
idle homes to the current cluster RU level before continuing.

Finally, run the standard pre-add-node cluster verification, which will
also catch most residual configuration issues:

```bash
$GRID_HOME/bin/cluvfy comp peer -n racnode3 -orainv oinstall -osdba asmdba -verbose
$GRID_HOME/bin/cluvfy stage -pre nodeadd -n racnode3 -verbose
```

Expected: no fatal failures, and specifically no warnings referencing
existing/duplicate cluster resources for `racnode3`.

## 5. Procedure

Once every stale-configuration check in Section 4 passes clean, the rejoin
procedure follows the same sequence as adding a brand-new node.

1. **If software was deinstalled at removal time** (`02` path), stage and
   install fresh: follow `01-add-node-to-rac-cluster.md` Steps 1–7 in full,
   substituting `racnode3` as the target — treat it exactly as a new node,
   since its binaries are gone.

2. **If software was left intact** (`02b` path) and patch levels are
   confirmed aligned (Section 4), the Grid Infrastructure stack can often
   be rejoined more directly. From an existing node, run the add-node
   wizard/CLI as usual — it re-detects the existing (but currently
   deconfigured) home on `racnode3` and reconfigures it rather than doing a
   full binary clone:
   ```bash
   cd $GRID_HOME
   ./gridSetup.sh -silent \
     -addNode \
     CLUSTER_NEW_NODES={racnode3} \
     CLUSTER_NEW_VIRTUAL_HOSTNAMES={racnode3-vip}
   ```
   If the installer does not detect the existing home cleanly (this can
   happen if the Oracle Inventory was cleaned up more thoroughly during
   removal), fall back to treating it as a fresh add per Option 1 above —
   do not attempt to hand-edit inventory XML to force detection.

3. **Run the root scripts on `racnode3` when prompted (root):**
   ```bash
   /u01/app/oraInventory/orainstRoot.sh
   /u01/app/19.0.0/grid/root.sh
   ```

   > **Point of no return:** as with the standard add-node procedure, once
   > `root.sh` completes, `racnode3` is a live CRS member again with access
   > to OCR and voting disks.

4. **Confirm the Grid Infrastructure stack is healthy on the rejoined node:**
   ```bash
   crsctl stat res -t
   olsnodes -s -t
   ```

5. **Extend/verify the RAC database Oracle Home on the node.** If the DB
   Home was deinstalled, extend it fresh:
   ```bash
   cd /u01/app/oracle/product/19.0.0/dbhome_1/addnode
   ./addnode.sh "CLUSTER_NEW_NODES={racnode3}"
   ```
   If the DB Home was left intact, confirm it is registered correctly in
   the Oracle Inventory on all nodes (`opatch lsinventory -detail`) and skip
   the clone if already present and consistent.

6. **Run the DB Home root script on `racnode3` if this was a fresh extend
   (root):**
   ```bash
   /u01/app/oracle/product/19.0.0/dbhome_1/root.sh
   ```

7. **Re-add the database instance via DBCA,** using the **same instance
   name it had before** (`ORCL3`) where practical, for consistency with any
   existing monitoring/service definitions, unless the naming has since been
   retired:
   ```bash
   dbca -silent -addInstance \
     -nodeList racnode3 \
     -gdbName ORCL \
     -instanceName ORCL3 \
     -sysDBAUserName sys -sysDBAPassword <redacted>
   ```

8. **Re-register any node-specific services that previously ran on
   `racnode3`** and were noted before the original removal:
   ```bash
   srvctl modify service -d ORCL -s <service_name> -modifyconfig -preferred racnode3
   srvctl start service -d ORCL -s <service_name> -n racnode3
   ```

## 6. Validation / Post-Checks

```bash
# Formal Oracle post-add-node verification
$GRID_HOME/bin/cluvfy stage -post nodeadd -n racnode3 -verbose

# Confirm all three nodes are active cluster members again
olsnodes -s -t

# Confirm no duplicate/orphaned resources exist for racnode3 from the
# prior membership (should be none, given Section 4 pre-checks)
crsctl stat res -t | grep -i racnode3

# Confirm the instance is open and registered
sqlplus -s / as sysdba <<'SQL'
SELECT instance_name, status, host_name FROM gv$instance ORDER BY inst_id;
SQL

srvctl status listener -n racnode3
lsnrctl status LISTENER_SCAN1

# Confirm patch levels are consistent cluster-wide (catches any missed
# stale-software issue)
$GRID_HOME/OPatch/opatch lsinventory -detail | grep -i "Patch" > /tmp/racnode3_patches.txt
diff /tmp/racnode3_patches.txt /tmp/racnode1_patches.txt   # prepared baseline
```

- [ ] `cluvfy stage -post nodeadd` reports overall result `PASSED`
- [ ] `olsnodes -s -t` lists all three nodes `Active`, no duplicates
- [ ] New/rejoined instance `ORCL3` shows `OPEN`
- [ ] No orphaned VIP, listener, or service resources referencing
      `racnode3` from the old membership remain
- [ ] Patch level on `racnode3` matches the rest of the cluster exactly

## 7. Rollback Plan

- **Failed during Section 4 stale-configuration checks:** do not proceed to
  Section 5 until every stale resource is cleaned up. Use
  `srvctl remove vip`, Oracle Inventory `-updateNodeList`, and/or a full
  pass through `02-delete-node-from-rac-cluster.md` Steps 4–6 against
  `racnode3` to fully clear any half-deleted state before retrying.

- **Failed after root.sh (Step 3) but before the DB Home/instance is added:**
  Follow `02-delete-node-from-rac-cluster.md` in full against `racnode3` to
  cleanly back it out again (deinstall + `crsctl delete node` +
  Inventory/VIP cleanup) rather than leaving it half-joined; then retry this
  SOP from Section 4 once the root cause is fixed.

- **Failed after instance add (Step 7):** use
  `dbca -silent -deleteInstance` for `ORCL3` first, then proceed with the
  GI-level rollback above if the node itself must also come back out.

- **Patch mismatch discovered after rejoin:** do not leave a
  patch-mismatched instance running in production; apply the missing RU to
  `racnode3` immediately (`02-patching/01-apply-quarterly-ru-patch.md`) or
  take the instance back down until it can be patched.

## 8. Communication

Notify application/service owners before the change window that the
previously-removed node's instance/services will return to service, and
confirm whether previous service placement/TAF configuration should be
restored exactly or adjusted. Notify network/storage teams to re-verify VIP
and storage presentation ahead of the window. Send a completion notice once
Section 6 validation passes in full.

## 9. Known Issues / Gotchas

- The single biggest source of rejoin failures is a **stale VIP or listener
  registration** left behind by an incomplete prior removal — always run
  the Section 4 stale-configuration checks even if the prior removal
  "looked clean" at the time.
- A leftover Oracle Inventory entry for `racnode3` on surviving nodes can
  cause `addnode.sh`/`gridSetup.sh -addNode` to silently skip steps it
  thinks are already done — always grep `inventory.xml` before starting,
  not just rely on installer output.
- If the node was out of the cluster through a full deinstall
  (`02` path) but its **old VIP hostname/IP** was reassigned to another
  purpose in DNS during the interim, the rejoin will register a conflicting
  resource — re-verify DNS ownership of `racnode3-vip` explicitly, don't
  assume it is still reserved.
- For the `02b` (deconfigure-only) path, forgetting to re-check patch level
  alignment is the most common post-rejoin defect — a node patched behind
  the rest of the cluster will run but is unsupported and can behave
  inconsistently under RU-specific bug fixes; always diff patch inventories
  as shown in Section 6.
- `crsctl stat res -t | grep racnode3` returning old, stopped resources
  immediately after rejoin (rather than nothing) usually means Section 4's
  Inventory/VIP cleanup was incomplete — resolve before declaring the change
  complete, do not assume they will self-clear.

## 10. References

- Oracle Database documentation — *Adding and Deleting Cluster Nodes* (19c):
  https://docs.oracle.com/en/database/oracle/oracle-database/19/cwadd/adding-and-deleting-cluster-nodes.html
- MOS Doc ID 1595570.1 — Grid Infrastructure Cluster Node Addition/Deletion
  best practices (confirm applicability to your exact patch level)
- oracle-base.com — Adding and Deleting Nodes on Oracle Grid Infrastructure
  (community reference; verify commands against docs.oracle.com above)
- Internal: `01-add-node-to-rac-cluster.md`,
  `02-delete-node-from-rac-cluster.md`,
  `02b-remove-node-without-software-deletion.md`,
  `02-patching/01-apply-quarterly-ru-patch.md`

## 11. Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-08-16 | DBA Team | Initial version |
