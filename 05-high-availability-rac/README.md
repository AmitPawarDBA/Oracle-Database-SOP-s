# 05 — High Availability / RAC

RAC cluster administration SOPs — node lifecycle, OCR/voting disk
management, cluster health verification, and connectivity troubleshooting.

| SOP | Covers |
|-----|--------|
| [01-add-node-to-rac-cluster.md](01-add-node-to-rac-cluster.md) | Add a new node to an existing cluster (gridSetup.sh, addnode.sh) |
| [02-delete-node-from-rac-cluster.md](02-delete-node-from-rac-cluster.md) | Full node removal, including software deinstall |
| [02b-remove-node-without-software-deletion.md](02b-remove-node-without-software-deletion.md) | Temporary node removal, leaving Oracle software in place |
| [03-readd-previously-deleted-node.md](03-readd-previously-deleted-node.md) | Re-add a node that was previously fully deleted |
| [04-relocate-ocr-voting-disk.md](04-relocate-ocr-voting-disk.md) | Move OCR/voting disks to a new ASM diskgroup |
| [05-recover-lost-corrupted-voting-disk.md](05-recover-lost-corrupted-voting-disk.md) | Partial and total voting disk loss recovery (CRITICAL) |
| [06-cluvfy-health-checks.md](06-cluvfy-health-checks.md) | Running/interpreting Cluster Verification Utility checks |
| [07-configure-oswatcher.md](07-configure-oswatcher.md) | OS Watcher setup for cluster-wide OS diagnostics |
| [08-rolling-restart-grid-infrastructure.md](08-rolling-restart-grid-infrastructure.md) | Zero-outage rolling GI restart across nodes |
| [09-scan-listener-vip-troubleshooting.md](09-scan-listener-vip-troubleshooting.md) | SCAN listener / VIP diagnosis and resolution |

## Naming convention

`NN-short-descriptive-name.md`, e.g. `01-add-node-to-rac-cluster.md`.
