# Pre-Go-Live Checklist

**Applies to:** New production database or major change go-live
**Owner:** DBA Team
**Last Reviewed:** 2026-08-16

| # | Item | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Backup strategy configured and validated (`07-backup-recovery/01-rman-backup-strategy.md`) | | ☐ | |
| 2 | Latest RU/patch level applied (`02-patching/`) | | ☐ | |
| 3 | Data Guard / DR configured if required (`06-data-guard-dr/`) | | ☐ | |
| 4 | Security hardening checklist completed (`09-security-hardening/01-database-security-hardening-checklist.md`) | | ☐ | |
| 5 | Monitoring/alerting wired up (`10-monitoring-alerting/`) | | ☐ | |
| 6 | Daily health check runbook assigned to on-call rotation (`12-daily-operations/01-daily-health-check-runbook.md`) | | ☐ | |
| 7 | Capacity/sizing validated against expected growth | | ☐ | |
| 8 | Application connectivity (TNS/service names) tested from all app tiers | | ☐ | |
| 9 | Rollback/DR plan reviewed and understood by the team | | ☐ | |
| 10 | CMDB / asset inventory updated | | ☐ | |
