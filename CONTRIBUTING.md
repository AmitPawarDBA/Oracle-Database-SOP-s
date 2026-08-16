# Contributing

This repo is only as useful as it is accurate and current. A few rules to
keep it that way.

## Adding or editing an SOP

1. Use `docs/templates/SOP-TEMPLATE.md` as the starting point — don't
   invent a new section structure.
2. Every command must be copy-pasteable and use realistic, consistent
   placeholders (`ORACLE_HOME=/u01/app/oracle/product/19.0.0/dbhome_1`,
   `ORACLE_SID=ORCL`, `oracle` OS user) unless the SOP is specifically
   about a different convention.
3. Every SOP needs: Prerequisites, Pre-Checks, a numbered Procedure,
   Validation/Post-Checks, and a Rollback Plan. No exceptions — even a
   "low risk" SOP should say what to do if it doesn't work.
4. Mark the **Point of no return** explicitly wherever one exists in the
   procedure.
5. Set an honest **Risk Level** (see the table in the root README) —
   under-stating risk is how outages happen.

## Adding screenshots

See `assets/screenshots/README.md` for the full convention. Short
version: embed the image inline right after the command block it
illustrates, redact anything environment-identifying, and prefer one
screenshot per meaningful checkpoint rather than one per keystroke.

## Review before merging

- [ ] Every command tested against a real environment (or clearly marked
      as illustrative/needs-testing if not yet validated)
- [ ] No real hostnames, IPs, passwords, or customer-identifying data
      anywhere in the SOP text or screenshots
- [ ] Section 11 (Change Log) updated with date, author, and a one-line
      summary of what changed
- [ ] "Last Reviewed" date updated in the header
- [ ] Cross-references to other SOPs (e.g. "see 07-backup-recovery/...")
      are correct and use relative paths

## Review cadence

Every SOP has a **Review Cadence** in its header (e.g. "every quarter,"
"every major version release"). Set a reminder — an SOP that's gone stale
against the current Oracle version is more dangerous than no SOP at all.
