# Oracle Database SOPs

A single, version-controlled home for every Oracle DBA runbook and
Standard Operating Procedure (SOP): installation, patching, upgrades,
migration, Data Guard/DR setup, switchover, failover, backup & recovery,
performance tuning, security hardening, daily operations, and more.

Every SOP follows the same template (`docs/templates/SOP-TEMPLATE.md`) so
any procedure — routine or emergency — can be picked up and executed
consistently, with copy-pasteable commands, expected output **shown
inline as a screenshot right where you need it**, a validation step, and
a rollback plan.

## Why this exists

- **One stop solution.** Every database activity lives in one repo
  instead of scattered notes, chat threads, and tribal knowledge.
- **Consistent structure.** Every SOP has the same sections in the same
  order — Purpose, Prerequisites, Pre-Checks, Procedure, Validation,
  Rollback, Communication, Gotchas, References — so nothing gets skipped
  under pressure.
- **Screenshots alongside commands, not in a separate folder.** Each SOP
  embeds the expected output image directly under the command that
  produces it (see `assets/screenshots/README.md` for the convention and
  how to swap in your own environment's captures).
- **Version controlled.** Every change to a procedure is a commit with a
  reason. `git blame`/`git log` tell you who changed a step and why.

## Repository structure

```
01-installation/            Oracle software installation
02-patching/                Quarterly RU/PSU patching (single-instance, RAC)
03-upgrades/                Major version upgrades (AutoUpgrade, manual)
04-migration/                Data Pump, RMAN duplicate, cross-platform migration
05-high-availability-rac/   RAC node lifecycle, OCR/voting disk, cluvfy, OSWatcher, SCAN/VIP
06-data-guard-dr/
  setup/                    Physical standby configuration
  switchover/               Planned switchover — DGMGRL and manual SQL variants
  failover/                 Emergency/unplanned failover — DGMGRL and manual SQL variants
  troubleshooting/          Data Guard transport/apply lag diagnosis
07-backup-recovery/         RMAN backup strategy; restore/recovery for every scenario
                             (spfile, controlfile, datafile, block, full, PITR,
                             tablespace, TSPITR via auxiliary instance)
08-performance-tuning/      AWR/ASH-based performance diagnosis + how-to-read-AWR guide
09-security-hardening/      Security hardening checklist
10-monitoring-alerting/     Monitoring & alerting setup (stub — see its README)
11-troubleshooting/         Locks, deadlocks, flashback, FRA full, listener, ASH, ORA-01555, redo log
12-daily-operations/        Daily health check / shift handover runbook
13-cloud-exadata-oci/       Exadata cell/image patching, IORM, OCI Autonomous DB, DBCS,
                             cross-region OCI Data Guard, Object Storage RMAN backups
checklists/                 Standalone checklists (go-live, DR drill, ...)
scripts/                    Reusable SQL/shell helper scripts referenced by SOPs
assets/screenshots/         Inline screenshots used across the SOPs
docs/templates/             SOP and checklist templates for new documents
```

`10-monitoring-alerting/` is the one remaining stub — it has a `README.md`
with a suggested list of SOPs to write next, following the same template
and naming convention as every other (now fully populated) category.

Where a DR activity (switchover, failover) can be done two ways, this
repo documents both **as separate documents**: one driven by Data Guard
Broker/DGMGRL (the recommended default), one using manual SQL*Plus
commands (for when the Broker is unavailable or its metadata is
corrupted). Don't mix the two mid-procedure — pick one path and follow it
end to end.

## How to use this repo

1. **Find the SOP** for the activity you need under its numbered category.
2. **Read Prerequisites and Pre-Checks first** — don't skip to the
   procedure. Most production incidents caused by a "routine" SOP trace
   back to a skipped pre-check.
3. **Follow the numbered Procedure steps in order.** Screenshots are
   embedded right after the command they illustrate so you can compare
   your actual output against a known-good example at a glance.
4. **Always read the Rollback Plan before you start**, not after
   something goes wrong.
5. **After execution, replace the illustrative screenshot** with your own
   environment's capture if you want the repo to build up a real
   evidence trail over time (see `assets/screenshots/README.md`) —
   redact hostnames/IPs/SIDs first.

## Adding a new SOP

1. Copy `docs/templates/SOP-TEMPLATE.md` into the right category folder.
2. Name it `NN-short-descriptive-name.md` (next available number in that
   folder).
3. Fill in every section — an incomplete SOP is worse than none, because
   it creates false confidence.
4. Add screenshots inline where they help (see
   `assets/screenshots/README.md`).
5. Open a pull request — see `CONTRIBUTING.md`.

## Risk levels

| Level | Meaning |
|-------|---------|
| Low | Minimal blast radius, easily reversible, no outage |
| Medium | Some blast radius, reversible with effort, may need an outage |
| High | Production-impacting, outage likely, requires careful rollback planning |
| Critical | Data-loss or extended-outage risk if executed incorrectly (e.g. failover, PITR) |

## Status of this repository

61 SOPs/checklists across 13 categories, covering the full Oracle DBA
lifecycle: installation, patching (single-instance + RAC), upgrades,
migration, RAC cluster administration, Data Guard/DR (setup, switchover,
failover — each with DGMGRL and manual-SQL variants — and lag
troubleshooting), backup & recovery (every restore/recovery scenario:
spfile, controlfile, datafile, block corruption, full, PITR, tablespace,
TSPITR), performance tuning, security hardening, incident troubleshooting
(8 common production issues), daily operations, and Exadata/OCI (cell and
image patching, IORM, Autonomous Database, DBCS, cross-region Data Guard,
Object Storage backups). Command syntax in these SOPs has been checked
against docs.oracle.com, oracle-base.com, and docs.oracle.com/en-us/iaas/
(for OCI CLI) where a source is cited in each SOP's References section.
Every SOP now has at least one inline screenshot at its key checkpoint —
always re-verify against the current documentation for your exact version
before running anything in production.

`10-monitoring-alerting/` is the one remaining stub — see its `README.md`
for a starter list of topics to add next.

## References / further reading

These external resources are good supplementary reading while this repo's
own library grows (not a source of copied content — always verify against
current Oracle documentation and My Oracle Support for your specific
version):

- Oracle Support (My Oracle Support / MOS) — primary source for patch
  numbers, known issues, and certification matrices
- Oracle Database documentation (docs.oracle.com) — version-specific
  reference for every command used in these SOPs
