# 11 — Troubleshooting

Stub category — populate using `docs/templates/SOP-TEMPLATE.md`.

Suggested SOPs to add here:

- [ ] Diagnosing and resolving blocking locks / session contention
- [ ] Diagnosing ORA-00060 deadlocks from the alert log/trace
- [ ] Flashback Database to a restore point (recovering from a logical
      error without a full RMAN restore)
- [ ] Diagnosing archiver stuck / FRA full ("ORA-19809/ORA-19815")
- [ ] Diagnosing and resolving listener connectivity failures
      (TNS-12154, TNS-12541)
- [ ] Diagnosing sudden CPU/IO spikes using ASH (`v$active_session_history`)
- [ ] Diagnosing and resolving ORA-01555 (snapshot too old)
- [ ] Recovering from a corrupted online redo log

## Naming convention

`NN-short-descriptive-name.md`, e.g. `01-resolve-blocking-locks.md`.
