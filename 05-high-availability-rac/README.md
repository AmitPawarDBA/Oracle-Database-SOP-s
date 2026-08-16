# 05 — High Availability / RAC

Stub category — populate using `docs/templates/SOP-TEMPLATE.md`.

Suggested SOPs to add here (based on common RAC operational activities,
see also the "References for further reading" note in the repo root
README):

- [ ] Add a node to an existing RAC cluster
- [ ] Delete a node from a RAC cluster (with and without software removal)
- [ ] Re-add a previously deleted node
- [ ] Relocate OCR/Voting disk to a new ASM diskgroup
- [ ] Recover a lost/corrupted voting disk
- [ ] Run and interpret `cluvfy` (Cluster Verification Utility) health checks
- [ ] Configure and use OSWatcher for cluster diagnostics
- [ ] Rolling restart of Grid Infrastructure across all nodes
- [ ] SCAN listener / VIP troubleshooting

## Naming convention

`NN-short-descriptive-name.md`, e.g. `01-add-node-to-rac-cluster.md`.
