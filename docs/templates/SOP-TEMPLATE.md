# SOP / Runbook Template

> Copy this file into the relevant category folder, rename it using the
> naming convention `NN-short-descriptive-name.md`, and fill in every
> section. Delete this instruction block once done.

---

**Title:** <Clear, action-oriented title, e.g. "Apply Quarterly RU Patch to Single-Instance Database">

**Category:** <e.g. Patching>

**Applies to:** <Oracle versions, e.g. 19c, 21c / Single-instance, RAC, Exadata / OS>

**Risk Level:** <Low / Medium / High / Critical — impact if this SOP is executed incorrectly>

**Estimated Duration:** <e.g. 45–90 minutes>

**Downtime Required:** <Yes/No — and expected outage window>

**Owner:** <Name / Team>

**Last Reviewed:** <YYYY-MM-DD>

**Review Cadence:** <e.g. Every 6 months, or after every major version change>

---

## 1. Purpose

Why this procedure exists and what it accomplishes. One or two sentences.

## 2. Scope

What this SOP covers and, just as importantly, what it does **not** cover.
Environments it applies to (Prod / Non-Prod / DR).

## 3. Prerequisites

- [ ] Required access / roles (e.g. sysdba, root, sudo)
- [ ] Required approvals (CAB ticket, change window)
- [ ] Backups verified and recoverable
- [ ] Required tools / patches downloaded and checksummed
- [ ] Communication sent to stakeholders
- [ ] Rollback plan reviewed and understood

## 4. Pre-Checks

Concrete commands/queries to run before starting, with expected output.

```sql
-- Example: confirm database is open and archivelog mode
SELECT status FROM v$instance;
SELECT log_mode FROM v$database;
```

## 5. Procedure

Numbered, step-by-step, copy-pasteable. Each step should state the *why*
briefly if it isn't obvious. Mark points of no return clearly.

1. Step one.
2. Step two.
3. ...

> **Point of no return:** call out explicitly where rollback becomes
> difficult or impossible.

## 6. Validation / Post-Checks

How to confirm the change succeeded. Include exact commands and expected
output/values.

```sql
SELECT ... ;
```

## 7. Rollback Plan

Explicit steps to revert if something goes wrong at each stage of the
procedure above. Reference which step in Section 5 each rollback action
corresponds to.

## 8. Communication

Who to notify before/after (app teams, business stakeholders), and the
message template to use.

## 9. Known Issues / Gotchas

Common pitfalls, MOS notes, bugs encountered previously, environment
quirks.

## 10. References

- MOS Notes:
- Oracle Documentation:
- Related internal SOPs:

## 11. Change Log

| Date | Author | Change |
|------|--------|--------|
| YYYY-MM-DD | Name | Initial version |
