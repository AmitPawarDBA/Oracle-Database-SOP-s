# 11 — Troubleshooting

Incident-driven troubleshooting SOPs for the most common production
issues a DBA is paged for.

| SOP | Covers |
|-----|--------|
| [01-diagnosing-resolving-blocking-locks.md](01-diagnosing-resolving-blocking-locks.md) | Blocking locks / session contention |
| [02-diagnosing-ora-00060-deadlocks.md](02-diagnosing-ora-00060-deadlocks.md) | ORA-00060 deadlock trace analysis |
| [03-flashback-database-to-restore-point.md](03-flashback-database-to-restore-point.md) | Undo a logical error without a full RMAN restore |
| [04-diagnosing-archiver-stuck-fra-full.md](04-diagnosing-archiver-stuck-fra-full.md) | ORA-19809/ORA-19815 archiver stuck / FRA full |
| [05-diagnosing-listener-connectivity-failures.md](05-diagnosing-listener-connectivity-failures.md) | TNS-12154 / TNS-12541 connectivity failures |
| [06-diagnosing-cpu-io-spikes-using-ash.md](06-diagnosing-cpu-io-spikes-using-ash.md) | Sudden CPU/IO spikes via Active Session History |
| [07-diagnosing-ora-01555-snapshot-too-old.md](07-diagnosing-ora-01555-snapshot-too-old.md) | ORA-01555 snapshot too old |
| [08-recovering-corrupted-online-redo-log.md](08-recovering-corrupted-online-redo-log.md) | Corrupted online redo log recovery |

See also `06-data-guard-dr/troubleshooting/` for Data Guard-specific lag
troubleshooting.

## Naming convention

`NN-short-descriptive-name.md`, e.g. `01-diagnosing-resolving-blocking-locks.md`.
