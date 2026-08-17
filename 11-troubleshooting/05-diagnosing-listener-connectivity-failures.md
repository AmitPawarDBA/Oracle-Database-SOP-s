# SOP: Diagnosing and Resolving Listener Connectivity Failures (TNS-12154 / TNS-12541)

**Category:** Troubleshooting
**Applies to:** Oracle 19c / 21c, Single Instance and RAC, Linux x86-64
**Risk Level:** Low — mostly read-only diagnostics; Medium if
`listener.ora`/`tnsnames.ora` edits or listener bounces are required on a
shared listener serving multiple databases
**Estimated Duration:** 15–45 minutes
**Downtime Required:** No, unless a listener bounce is required on a
shared listener with active connections (see Section 5.5)
**Owner:** DBA Team
**Last Reviewed:** 2026-08-16
**Review Cadence:** Every 6 months

---

## 1. Purpose

Provides a structured triage procedure to diagnose and resolve the two
most common Oracle Net connection failures reported by applications:
**TNS-12154** (connect identifier cannot be resolved — a naming/config
problem, usually client-side) and **TNS-12541** (no listener — the
listener is down, or the client is pointed at the wrong host/port).
Misdiagnosing one for the other wastes time, since the fixes are on
opposite ends of the connection path.

## 2. Scope

Covers client-side naming resolution (`tnsnames.ora`, `sqlnet.ora`,
Easy Connect, LDAP), server-side listener configuration
(`listener.ora`), listener process health, and network reachability
(firewall/port) checks. Applies to Production, Non-Prod, and DR
listeners. Does **not** cover Oracle Connection Manager (CMAN) proxy
listeners in depth, SCAN listener/VIP failover internals for RAC (see
`05-high-availability-rac/`), or TLS/mTLS certificate troubleshooting
for encrypted listener endpoints (tracked separately).

## 3. Prerequisites

- [ ] OS access to the affected client host and/or database host as the
      `oracle` OS user (or equivalent app-server account for
      client-side checks)
- [ ] Confirm `ORACLE_HOME=/u01/app/oracle/product/19.0.0/dbhome_1` and
      `TNS_ADMIN` are correctly set in the shell/environment being
      tested — a stale `TNS_ADMIN` is one of the most common root
      causes of TNS-12154
- [ ] Incident ticket capturing: exact connect string used, exact error
      text (including the trailing `ORA-`/`TNS-` code and any nested
      cause), client host, and time of first failure
- [ ] Network/firewall change window approvals if a port-open request
      is required (do not open ports ad hoc in Production)

## 4. Pre-Checks

```bash
# Confirm environment on the host reporting the error
echo "ORACLE_HOME=$ORACLE_HOME"
echo "TNS_ADMIN=$TNS_ADMIN"
which tnsping lsnrctl sqlplus

# Confirm which tnsnames.ora / sqlnet.ora is actually being read
# (TNS_ADMIN overrides $ORACLE_HOME/network/admin — verify both exist)
ls -l "${TNS_ADMIN:-$ORACLE_HOME/network/admin}"/tnsnames.ora \
      "${TNS_ADMIN:-$ORACLE_HOME/network/admin}"/sqlnet.ora \
      "${TNS_ADMIN:-$ORACLE_HOME/network/admin}"/listener.ora 2>&1
```

## 5. Procedure

### 5.1 Triage Flowchart

```
Connection fails
   |
   +-- Error contains "TNS-12154 / ORA-12154" (could not resolve
   |   connect identifier)?
   |       -> Client-side naming problem. Go to 5.2.
   |
   +-- Error contains "TNS-12541 / ORA-12541" (no listener)?
   |       -> Listener down, or wrong host/port, or network blocked.
   |          Go to 5.3.
   |
   +-- Error contains "TNS-12514" (listener does not currently know
   |   of service)? -> Listener is up but the service/instance isn't
   |   registered. Go to 5.4 (related but distinct — do not confuse
   |   with 12541).
   |
   +-- Neither pattern (e.g. TNS-12170 timeout, ORA-12170)?
           -> Likely network path / firewall problem even though the
              listener itself is healthy. Go to 5.5.
```

### 5.2 TNS-12154 — Could Not Resolve the Connect Identifier

**Verified cause (docs.oracle.com Error Messages Reference,
`ORA-12154`):** a connection was requested using a connect identifier
that could not be resolved into a connect descriptor using any of the
configured naming methods — the net service name was not found in the
naming repository in use, or the repository itself could not be
reached. This is almost always a **client-side** configuration issue,
not a database/listener problem.

1. Identify which naming method is actually active:
   ```bash
   grep -i "NAMES.DIRECTORY_PATH" "${TNS_ADMIN:-$ORACLE_HOME/network/admin}"/sqlnet.ora
   # Typical: NAMES.DIRECTORY_PATH= (TNSNAMES, EZCONNECT)
   ```
2. If **Local Naming (tnsnames.ora)** is in the path:
   - Confirm `TNSNAMES` is listed in `NAMES.DIRECTORY_PATH`.
   - Confirm the file exists at the path the client is actually
     reading — check `TNS_ADMIN` first; it overrides
     `$ORACLE_HOME/network/admin`:
     ```bash
     tnsping <net_service_name>
     -- Output line "Used TNSNAMES adapter to resolve the alias" shows
     -- exactly which tnsnames.ora and which entry was used.
     ```
   - Confirm the exact alias exists and is spelled correctly (aliases
     are case-insensitive but whitespace/typos are the #1 cause):
     ```bash
     grep -A5 -i "^<net_service_name>" \
       "${TNS_ADMIN:-$ORACLE_HOME/network/admin}"/tnsnames.ora
     ```
   - Check for syntax errors: unmatched parentheses, stray characters,
     smart/curly quotes pasted from a document, or a missing blank
     line between entries. Validate quickly:
     ```bash
     # Count open vs close parens - should match
     grep -o "(" "${TNS_ADMIN}"/tnsnames.ora | wc -l
     grep -o ")" "${TNS_ADMIN}"/tnsnames.ora | wc -l
     ```
3. If **Easy Connect** is being used (`user/pass@host:port/service`):
   - Confirm `EZCONNECT` is listed in `NAMES.DIRECTORY_PATH`.
   - Confirm host, port, and service name are correct and that the
     string is not missing a leading `//` or has a stray space.
   - Try enclosing the identifier in quotes if it contains special
     characters.
4. If **Directory Naming (LDAP/OID)** is used:
   - Confirm `LDAP` is listed in `NAMES.DIRECTORY_PATH`.
   - Confirm the LDAP directory server is reachable and the net
     service name/DN is correctly registered.
5. For a **database link** hitting TNS-12154, remember the identifier
   is resolved on the **remote** database server process, not the
   local client — check `TNS_ADMIN`, `tnsnames.ora`, and `sqlnet.ora`
   on the database host the link connects *from*, i.e. the source
   instance's environment, not the app server's.
6. Re-test after any fix:
   ```bash
   tnsping <net_service_name>
   sqlplus <user>/<password>@<net_service_name>
   ```

### 5.3 TNS-12541 — No Listener

**Verified cause (docs.oracle.com Error Messages Reference /
Net Services Administrator's Guide, `TNS-12541`/`ORA-12541`):** the
connection request could not be completed because either the database
listener process is not running on the specified host/port, an IPC
protocol connection found no listener for the specified key locally,
or an external procedure/UTL listener is not listening at the
specified address. This is almost always a **server-side** or
**network-path** issue.

1. Check listener status on the target database host:
   ```bash
   # As the oracle OS user
   export ORACLE_HOME=/u01/app/oracle/product/19.0.0/dbhome_1
   export PATH=$ORACLE_HOME/bin:$PATH
   lsnrctl status
   lsnrctl status LISTENER   # or the named listener from listener.ora
   ```
   - If `lsnrctl` returns `TNS-12541: TNS:no listener` itself when run
     **locally** on the DB host, the listener process is not running.
     Start it:
     ```bash
     lsnrctl start LISTENER
     ```
   - If `lsnrctl status` succeeds locally but the client still gets
     TNS-12541, the problem is host/port mismatch or network path
     (go to step 3).
2. Confirm the listener is bound to the host/port the client expects:
   ```bash
   lsnrctl status | grep -A3 "Listening Endpoints Summary"
   -- Compare against HOST=... PORT=... in the client's tnsnames.ora
   -- or the Easy Connect string
   ```
   Cross-check `listener.ora` on the DB host:
   ```bash
   cat "${TNS_ADMIN:-$ORACLE_HOME/network/admin}"/listener.ora
   ```
   Common mismatch: listener bound to a specific hostname/VIP while
   the client connect string uses a different hostname/IP (e.g. a
   RAC VIP vs. the physical hostname), or the listener was
   reconfigured to a non-default port (e.g. 1522) without updating
   client `tnsnames.ora`.
3. Confirm network reachability from the client to the listener
   host/port (rules out firewall/routing even when the listener is
   healthy):
   ```bash
   # From the client host
   telnet <db_host> <port>          # connection refused = host is up,
                                      # nothing listening on that port
                                      # or firewall actively rejecting
   nc -zv <db_host> <port>           # alternative to telnet
   traceroute <db_host>              # rules out routing changes
   ```
   - **Connection refused** immediately (not a timeout) usually means
     the listener process is down or bound to a different
     interface/port — go back to step 1/2.
   - **Connection times out** (no response) usually means a firewall
     is silently dropping the packets — engage network team with the
     source IP, destination IP, and port for an ACL/firewall rule
     check.
4. Confirm the service is registered with the listener once it is
   confirmed running (a running-but-empty listener produces
   TNS-12514, not 12541 — see 5.4):
   ```bash
   lsnrctl services LISTENER
   ```
5. Re-test after any fix:
   ```bash
   tnsping <net_service_name>
   sqlplus <user>/<password>@<net_service_name>
   ```

### 5.4 Related: TNS-12514 (Listener Up, Service Not Registered)

If `lsnrctl status` succeeds and shows the listener up, but
`lsnrctl services` does not list the target service/SID, the instance
has not registered with the listener (dynamic registration via
`local_listener`/PMON, or the service was never added). Do not treat
this as a TNS-12541 problem:

```sql
-- On the database, confirm registration target and force it
SHOW PARAMETER local_listener;
ALTER SYSTEM REGISTER;

-- Confirm the service exists and is started
SELECT name, network_name FROM v$active_services;
```

### 5.5 Bouncing the Listener (only if required)

> **Point of no return / caution:** bouncing a listener on a shared
> host drops **all** in-flight new connection attempts routed through
> it (existing established sessions are unaffected, but connection
> pools reconnecting mid-bounce will see transient TNS-12541 errors).
> Confirm no other databases share this listener before restarting it
> in Production, and get change approval if this listener serves
> multiple SIDs.

```bash
lsnrctl stop LISTENER
lsnrctl start LISTENER
lsnrctl status LISTENER
```

Prefer `lsnrctl reload LISTENER` (re-reads `listener.ora` without
dropping the process) over a full stop/start when only the
configuration changed and the listener process itself is healthy.

## 6. Validation / Post-Checks

```bash
tnsping <net_service_name>
# Expect: OK (<time> msec)

lsnrctl status LISTENER
# Expect: STATUS of the LISTENER = "The command completed successfully"
# and the target service listed under "Services Summary"

lsnrctl services LISTENER
# Expect: target service/instance shown with status READY
```

```sql
-- From the application/client side, confirm an actual login succeeds
sqlplus <user>/<password>@<net_service_name>
SELECT status, instance_name, host_name FROM v$instance;
```

- [ ] Application team confirms connections succeed from the affected
      tier (app server, batch job, reporting tool — not just from the
      DBA's own session)
- [ ] Root cause (naming vs. listener vs. network) documented in the
      incident ticket
- [ ] If a config file was edited, the change is captured in the
      environment's change record and a backup of the prior
      `tnsnames.ora`/`listener.ora` is retained

## 7. Rollback Plan

- **`tnsnames.ora`/`sqlnet.ora` edit:** restore from the timestamped
  backup taken before editing (always `cp tnsnames.ora
  tnsnames.ora.bak_$(date +%Y%m%d%H%M)` before any edit); re-run
  `tnsping` to confirm reversion.
- **`listener.ora` edit + reload/bounce:** restore the prior
  `listener.ora` and run `lsnrctl reload LISTENER` (or stop/start if
  reload is insufficient); confirm `lsnrctl status` matches the
  pre-change baseline captured in Section 4.
- **Firewall rule opened:** if the new rule introduces unintended
  exposure, request the network team revert the specific rule via the
  same change ticket used to open it.

## 8. Communication

For a Production-impacting outage (application cannot connect at
all): notify the incident channel and affected application owner
immediately at triage start with the working hypothesis (naming vs.
listener vs. network), and provide updates every 15–30 minutes until
resolved. For a single client/one-off connectivity issue, handle via
the standard ticket without a broader broadcast.

## 9. Known Issues / Gotchas

- `TNS_ADMIN` set in one shell/profile but not in the application's
  actual runtime environment (e.g. a systemd service with a minimal
  env, or a cron job) is one of the most common causes of "works from
  my session, fails from the app" TNS-12154 reports — always verify
  the environment the *failing* process actually runs under, not just
  the DBA's interactive shell.
- Copy-pasting `tnsnames.ora` entries from email/Word/Confluence often
  introduces smart quotes or non-breaking spaces that look identical
  visually but break parsing — regenerate the entry by typing it or
  copy from a plain-text source if syntax looks correct but resolution
  still fails.
- A listener restart re-reads `listener.ora` but does **not**
  automatically re-register dynamic services — allow up to 60 seconds
  (default `local_listener` registration interval) or force it with
  `ALTER SYSTEM REGISTER;` on each affected instance after a bounce.
- RAC/SCAN listeners resolve host/port differently (SCAN VIPs, load
  balancing across three listeners) — a TNS-12541 in a RAC/Exadata
  environment should route to `05-high-availability-rac/` triage
  rather than assuming a single-listener problem.
- `telnet`/`nc` succeeding to the port does not guarantee Oracle Net
  is healthy behind it (a stale process or non-Oracle service could be
  bound) — always confirm with `lsnrctl status` run locally on the DB
  host as the definitive source of truth.

## 10. References

- Verified against **docs.oracle.com Error Messages Reference**:
  [ORA-12154](https://docs.oracle.com/en/error-help/db/ora-12154/) —
  confirmed error text "TNS:could not resolve the connect identifier
  specified," cause (naming repository resolution failure), and
  per-naming-method actions (Local/TNSNAMES, Directory/LDAP,
  Easy Connect, DB link).
- Verified against **docs.oracle.com Error Messages Reference**:
  [TNS-12541](https://docs.oracle.com/en/error-help/db/tns-12541) and
  the [Oracle Database Net Services Administrator's Guide 23ai,
  §16.3.16 ORA-12541](https://docs.oracle.com/en/database/oracle/oracle-database/23/netag/tns-12541-or-ora-12541-tns-no-listener.html)
  — confirmed error text "Cannot connect. No listener at ...", cause
  (listener not running / wrong host-port / IPC key mismatch), and
  recommended `lsnrctl status` verification steps.
- Oracle Database Net Services Reference — `sqlnet.ora`,
  `tnsnames.ora`, `listener.ora` parameter definitions
  (docs.oracle.com Net Services Reference Guide, version 19c).
- oracle-base.com — Listener configuration and `lsnrctl` command
  reference (background/cross-check for `lsnrctl services` output
  interpretation).
- Internal: `08-performance-tuning/01-awr-based-performance-diagnosis.md`
  (for connection-storm/CPU symptoms once connectivity is restored)
- Internal: `05-high-availability-rac/` (SCAN/VIP listener specifics)

## 11. Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-08-16 | DBA Team | Initial version |
