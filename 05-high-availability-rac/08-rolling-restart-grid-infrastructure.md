# SOP: Rolling Restart of Grid Infrastructure Across All Nodes

**Category:** High Availability / RAC
**Applies to:** Oracle 19c Grid Infrastructure + RAC, Linux x86-64
(RHEL/OEL 7/8/9), cluster `RACCLUSTER` (`racnode1`/`racnode2`/`racnode3`)
**Risk Level:** Medium — routine when done one node at a time with
verification between nodes; High if nodes are restarted concurrently or
verification is skipped
**Estimated Duration:** 15–30 minutes per node (45–90 minutes total for a
3-node cluster), plus verification time between nodes
**Downtime Required:** No cluster-wide outage — each node's local instance
and services are briefly unavailable during its own restart window, but the
surviving nodes continue serving the application throughout
**Owner:** DBA Team
**Last Reviewed:** 2026-08-16
**Review Cadence:** Every 6 months

---

## 1. Purpose

Provides a safe, node-by-node procedure to restart the Grid Infrastructure
stack (Clusterware, ASM, and dependent resources) across an entire RAC
cluster — needed after certain patches, OS kernel updates, configuration
changes that require a CRS restart, or to clear a stack-level issue —
without incurring a full cluster-wide outage.

## 2. Scope

Covers restarting the Grid Infrastructure stack one node at a time
(`crsctl stop crs` / `crsctl start crs`, or the node-scoped
`crsctl stop cluster -n <node>` variant) on a running, healthy cluster.
Does not cover restarting a database instance alone (that is a much lighter
operation — use `srvctl stop/start instance`), and does not cover emergency
restart during an active outage (see the voting disk recovery SOP,
`05-recover-lost-corrupted-voting-disk.md`, for that scenario). Assumes the
cluster is healthy before starting — do not begin a rolling restart against
a cluster that is already degraded; fix the underlying issue first.

## 3. Prerequisites

- [ ] Change ticket approved and change window confirmed (even though the
      cluster stays up, application connections to the node being
      restarted will need to fail over/reconnect)
- [ ] Cluster confirmed fully healthy before starting
      (`crsctl check cluster -all`, all resources `ONLINE`)
- [ ] Application/connection pool behavior confirmed to handle node-level
      failover gracefully (TAF/FAN/FCF configured, or at minimum
      connection retry logic present) — a rolling restart without proper
      client failover configuration will still cause application-visible
      errors even though the cluster itself stays up
- [ ] Root and `grid`/`oracle` OS user access on all nodes
- [ ] Current OCR backup confirmed recent and restorable
      (`ocrconfig -showbackup`)
- [ ] Order of nodes to restart agreed (typically least-loaded or
      standby-role node first)
- [ ] Rollback/escalation understanding reviewed (Section 7)
- [ ] Stakeholders notified (Section 8)

## 4. Pre-Checks

Run from any node before starting, and repeat before moving to each
subsequent node:

```bash
# Confirm cluster-wide health across all nodes
crsctl check cluster -all

# Confirm all nodes are active members
olsnodes -s -t

# Confirm no resources are already offline/failed
crsctl stat res -t | grep -iv online | grep -v '^$'

# Confirm current database/service placement (so it's clear what will move)
srvctl status database -d ORCL
srvctl status service -d ORCL
```

Expected: `crsctl check cluster -all` reports all nodes healthy; no
unexpected `OFFLINE`/`INTERMEDIATE` resources; all instances/services
running on their expected nodes.

## 5. Procedure

Perform this entire sequence for **one node**, fully verify the cluster is
healthy again (Section 6), and only then move to the next node. Do **not**
restart two nodes concurrently — that removes the redundancy that makes
this a zero-cluster-outage operation.

### 5.1 Restart One Node's Grid Infrastructure Stack

1. **Select the first node** (e.g. `racnode3`) and confirm current
   resource placement on it:
   ```bash
   crsctl stat res -t | grep -B2 racnode3
   ```

2. **Notify/drain if applicable.** If the node hosts a service with
   preferred (not just available) instances, consider relocating critical
   sessions gracefully first:
   ```bash
   srvctl relocate service -d ORCL -s ORCL_APP -oldinst ORCL3 -newinst ORCL1
   ```
   This is optional for a routine restart with proper FAN-aware clients,
   but recommended for long-running batch/reporting connections that don't
   handle failover well.

3. **Stop the Grid Infrastructure stack on the target node only**
   (root, run **on** `racnode3`, not remotely):
   ```bash
   crsctl stop crs
   ```
   This gracefully stops all resources on this node (database instance,
   ASM instance, listener, VIP — VIP relocates to a surviving node) and
   then the Clusterware stack itself. If it hangs on a resource that won't
   stop cleanly (rare on a healthy node), do not immediately force it —
   investigate first with `crsctl stat res -t` from another node. Only use
   `crsctl stop crs -f` if graceful stop is confirmed stuck, since `-f`
   skips graceful shutdown of dependent resources.

   Alternative (equivalent for a single node, can be run remotely from
   another node as root):
   ```bash
   crsctl stop cluster -n racnode3
   ```

4. **Confirm the target node is fully down** while the rest of the cluster
   stays up (from a surviving node, e.g. `racnode1`):
   ```bash
   crsctl check cluster -all
   olsnodes -s -t
   ```
   Expected: `racnode3` shows `Inactive`/down; `racnode1` and `racnode2`
   remain `Active` and fully healthy.

5. **Perform the underlying maintenance** the restart was for (OS patching,
   kernel update, configuration change) on `racnode3` now, while its GI
   stack is down.

6. **Start the Grid Infrastructure stack back up on the target node**
   (root, on `racnode3`):
   ```bash
   crsctl start crs
   ```
   Or, from another node:
   ```bash
   crsctl start cluster -n racnode3
   ```

7. **Wait for the node to fully rejoin** and confirm before moving on:
   ```bash
   crsctl check crs
   crsctl stat res -t | grep racnode3
   ```

> **Point of no return:** none — this is designed to be fully reversible
> at every step since the cluster's redundancy absorbs each node's
> downtime. The only risk is proceeding to the next node before the
> current one is confirmed fully healthy (see Section 5.2).

### 5.2 Verification Gate Before Each Subsequent Node

Before restarting the next node, **all** of the following must be true —
treat this as a hard gate, not a formality:

```bash
crsctl check cluster -all
```
Expected: every node reports healthy, including the one just restarted.

```bash
olsnodes -s -t
```
Expected: all nodes `Active`.

```bash
crsctl stat res -t
```
Expected: no resources stuck `OFFLINE`/`INTERMEDIATE`/`UNKNOWN`; the
instance/ASM/listener on the just-restarted node are back `ONLINE`.

Only once this gate passes cleanly, repeat Section 5.1 for the next node
(`racnode1`, then finally `racnode2`, or whatever order was agreed in
Section 3).

## 6. Validation / Post-Checks

After the **last** node has been restarted and verified:

```bash
# Cluster-wide health
crsctl check cluster -all
crsctl check crs

# All nodes active
olsnodes -s -t

# All resources back to their pre-maintenance placement (or explicitly
# accepted new placement, if relocated in Step 2)
crsctl stat res -t

# Database availability across all instances
sqlplus -s / as sysdba <<'SQL'
SELECT instance_name, status, host_name FROM gv$instance ORDER BY inst_id;
SQL

# Listener/SCAN health
srvctl status listener
srvctl status scan_listener
```

- [ ] All nodes report `Active` and fully healthy
- [ ] No resources left in a non-`ONLINE` state that were `ONLINE` before
      the maintenance began
- [ ] All database instances `OPEN` and registered
- [ ] Application connectivity spot-checked end-to-end (not just cluster
      resource state — confirm real client sessions can connect and
      execute)
- [ ] Any services relocated in Step 2 either relocated back to their
      preferred instance or explicitly left as-is per plan

## 7. Rollback Plan

Because each node is restarted individually with verification before
proceeding, "rollback" is scoped to the single node currently being worked
on, not the whole cluster:

- **If a node fails to stop cleanly (Step 3):** do not force (`-f`) as a
  first response — check `crsctl stat res -t` and the node's
  `alertcrsd.log` for the specific hung resource. Force stop only after
  confirming it's genuinely stuck, and document the resource that required
  forcing for follow-up.
- **If a node fails to rejoin after restart (Step 6/7):** the rest of the
  cluster remains healthy and unaffected — there is no time pressure to
  force a fix. Troubleshoot the single node in isolation
  (`crsctl start crs`, review `$GRID_HOME/log/<hostname>/alertcrsd.log` and
  `ocssd.log`), escalate to Oracle Support if not resolved within your
  standard SLA, and leave that node out of the cluster (do not proceed to
  restart the next node) until it is confirmed healthy.
- **If the underlying maintenance (Step 5) needs to be undone:** revert the
  OS/config change on that node while its GI stack is still down, then
  proceed with Step 6 as normal — this is the cleanest rollback path since
  the stack isn't yet running with the new/uncertain configuration.

## 8. Communication

Notify application teams of the rolling maintenance window in advance,
noting that brief per-node connection resets are expected as each node
cycles (typically sub-minute with proper FAN/TAF client configuration) but
no full outage is expected. Send a completion notice once Section 6
validation passes for the entire cluster. If any node required force-stop
or extended troubleshooting (Section 7), include that in the post-change
summary even if ultimately resolved within the window.

## 9. Known Issues / Gotchas

- The single biggest risk in this procedure is **operator impatience** —
  moving to the next node before the previous one is fully verified
  (Section 5.2) turns a zero-outage operation into a potential
  multi-node/cluster-wide outage. Always treat the verification gate as
  mandatory.
- `crsctl stop crs` without `-f` can occasionally hang waiting on a
  resource with an unusual dependency chain (e.g. a custom application VIP
  or third-party clusterware-managed resource) — know your cluster's full
  resource list (`crsctl stat res -t`) before starting, not just the
  standard Oracle-managed ones.
- Clients without FAN/FCF/TAF configured will see connection errors during
  each node's restart window even though the cluster overall stays
  available — this is an application configuration gap, not a Clusterware
  issue, and should be flagged separately if discovered during this
  procedure.
- If the cluster uses Leaf Nodes or Flex ASM with a small number of ASM
  instances, confirm ASM redundancy is not reduced below tolerance by
  taking one node's ASM instance down — check `asmcmd lsdg` for degraded
  diskgroup states before proceeding to the next node.
- Concurrent OS patching automation (e.g. unattended kernel updates via a
  patch management tool) can race with this manual procedure if not
  coordinated — confirm no other automated maintenance is scheduled to hit
  the same nodes during this window.

## 10. References

- Oracle Database documentation — *Starting and Stopping Oracle
  Clusterware* (19c, Administering Oracle Real Application Clusters):
  https://docs.oracle.com/en/database/oracle/oracle-database/19/racad/starting-and-stopping-oracle-clusterware.html
  — verified: `crsctl stop crs` / `crsctl start crs` and
  `crsctl stop|start cluster -n` syntax and behavior match this source.
- MOS Doc ID 1050693.1 — Rolling Patch/Restart best practices for Grid
  Infrastructure (confirm applicability to your exact patch level).
- Internal: `05-high-availability-rac/06-cluvfy-health-checks.md`
  (post-restart health verification), `02-patching/`
  (rolling patch application, which uses this same node-by-node pattern).

## 11. Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-08-16 | DBA Team | Initial version |
