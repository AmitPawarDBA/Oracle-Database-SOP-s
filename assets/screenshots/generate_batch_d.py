#!/usr/bin/env python3
"""
Generates illustrative terminal-style screenshot PNGs for batch D of the
Oracle DBA SOP repository (05-high-availability-rac and
13-cloud-exadata-oci categories). These are SYNTHETIC/ILLUSTRATIVE example
outputs (not captured from any real system) meant to show what a healthy
command result should look like. DBAs should replace these with real
screenshots captured from their own environment during actual SOP
execution -- see README.md in this folder for the naming convention.

This file defines its own copy of the render() function (copied verbatim
from generate_screenshots.py) so the visual style matches exactly.

Usage: python3 generate_batch_d.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_SIZE = 15
PAD_X = 24
PAD_TOP = 44
PAD_BOTTOM = 20
LINE_SPACING = 6
BG = (30, 32, 38)
TITLEBAR = (44, 46, 54)
FG = (223, 227, 232)
GREEN = (98, 209, 150)
YELLOW = (233, 196, 106)
CYAN = (110, 197, 232)
RED = (235, 111, 111)
GRAY = (140, 146, 156)
DOTS = [(235, 111, 111), (233, 196, 106), (98, 209, 150)]

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
font_bold = ImageFont.truetype(FONT_BOLD_PATH, FONT_SIZE)


def color_for(line):
    s = line.strip()
    if s.startswith("$") or s.startswith("SQL>") or s.startswith("RMAN>") or s.startswith("DGMGRL>"):
        return CYAN
    if any(k in s for k in ["ERROR", "ORA-", "FAILED", "CRITICAL", "invalid"]) and not s.startswith("--"):
        return RED
    if any(k in s for k in ["SUCCESS", "success", "APPLIED", "Succeeded", "VALID", "COMPLETE", "OK", "Normal", "SYNCHRONIZED"]):
        return GREEN
    if any(k in s for k in ["WARNING", "WARN"]):
        return YELLOW
    if s.startswith("--") or s.startswith("#") or s.startswith("//"):
        return GRAY
    return FG


def render(filename, title, lines, width=980):
    n = len(lines)
    height = PAD_TOP + PAD_BOTTOM + n * (FONT_SIZE + LINE_SPACING)
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    # title bar
    draw.rectangle([0, 0, width, 34], fill=TITLEBAR)
    for i, c in enumerate(DOTS):
        draw.ellipse([16 + i * 22, 12, 26 + i * 22, 22], fill=c)
    draw.text((width / 2, 17), title, font=font_bold, fill=GRAY, anchor="mm")

    y = PAD_TOP
    for line in lines:
        c = color_for(line)
        draw.text((PAD_X, y), line, font=font, fill=c)
        y += FONT_SIZE + LINE_SPACING

    # illustrative watermark bottom-right
    draw.text((width - 14, height - 16), "illustrative sample output",
               font=ImageFont.truetype(FONT_PATH, 11), fill=(90, 94, 102), anchor="rs")

    img.save(os.path.join(OUT_DIR, filename))
    print("wrote", filename)


SCREENSHOTS = {}

# ---------------------------------------------------------------------
# 05-high-availability-rac/05-recover-lost-corrupted-voting-disk.md
# ---------------------------------------------------------------------

SCREENSHOTS["05-rac-voting-disk-total-loss.png"] = (
    "root@racnode1:~ -- crsctl query css votedisk",
    [
        "# crsctl query css votedisk",
        "",
        "Located 0 voting disk(s).",
        "",
        "# crsctl check cluster -all",
        "CRS-4535: Cannot communicate with Cluster Ready Services",
        "CRS-4530: Communications failure contacting Cluster Synchronization Services daemon",
        "CRS-4534: Cannot communicate with Event Manager",
        "",
        "-- Confirms total loss: no voting disk copies located anywhere.",
        "-- Proceeding to Path B (Section 5B): exclusive-mode recovery.",
    ],
)

SCREENSHOTS["05-rac-voting-disk-replace-success.png"] = (
    "root@racnode1:~ -- crsctl replace votedisk +VOTEDG",
    [
        "# crsctl replace votedisk +VOTEDG",
        "",
        "Successful addition of voting disk 8b3f2a1c9e1c4f6dbf1a2e3d4c5b6a7f.",
        "Successful addition of voting disk 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d.",
        "Successful addition of voting disk 9f8e7d6c5b4a3928176023910f0e0d0c.",
        "Successful replacement of voting disk group with +VOTEDG.",
        "CRS-4266: Voting file(s) successfully replaced",
        "",
        "# crsctl query css votedisk",
        "##  STATE    File Universal Id                File Name Disk group",
        "--  -----    -----------------                --------- ---------",
        " 1. ONLINE   8b3f2a1c9e1c4f6dbf1a2e3d4c5b6a7f (VOTEDG_0001) [VOTEDG]",
        " 2. ONLINE   1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d (VOTEDG_0002) [VOTEDG]",
        " 3. ONLINE   9f8e7d6c5b4a3928176023910f0e0d0c (VOTEDG_0003) [VOTEDG]",
        "Located 3 voting disk(s).",
    ],
)

# ---------------------------------------------------------------------
# 05-high-availability-rac/06-cluvfy-health-checks.md
# ---------------------------------------------------------------------

SCREENSHOTS["05-rac-cluvfy-post-crsinst-passed.png"] = (
    "grid@racnode1:~ -- cluvfy stage -post crsinst",
    [
        "$ cluvfy stage -post crsinst -n racnode1,racnode2,racnode3 -verbose",
        "",
        "Performing post-checks for cluster services setup",
        "",
        "Checking node reachability...PASSED",
        "Checking user equivalence...PASSED",
        "Checking CRS integrity...PASSED",
        "Checking Cluster manager integrity...PASSED",
        "Checking OCR integrity...PASSED",
        "Checking Voting Disk integrity...PASSED",
        "Checking cluster network configuration...PASSED",
        "",
        "CVU operation performed:      stage -post crsinst",
        "Date:                         Aug 16, 2026 3:12:04 PM",
        "CVU home:                     /u01/app/19.0.0/grid",
        "User:                         grid",
        "",
        "Verification Result: PASSED",
    ],
)

# ---------------------------------------------------------------------
# 05-high-availability-rac/07-configure-oswatcher.md
# ---------------------------------------------------------------------

SCREENSHOTS["05-rac-oswatcher-startup-confirmed.png"] = (
    "oracle@racnode1:~/oswbb -- startOSWbb.sh 30 72 gzip",
    [
        "$ nohup ./startOSWbb.sh 30 72 gzip > startosw.log 2>&1 &",
        "[1] 24187",
        "",
        "$ cat startosw.log",
        "OSWatcher Version 8.3.3",
        "Starting OSWatcher v8.3.3 on racnode1 ...",
        "Data collection interval set to 30 seconds",
        "Archive retention period set to 72 hours",
        "Using compression option gzip",
        "OSWatcher - Written by Oracle Center of Expertise",
        "Data is stored in directory: /u01/app/oracle/oswbb/archive",
        "",
        "$ ps -elf | grep -i oswbb | grep -v grep",
        "oracle   24187     1  0 09:14 pts/0  ./OSWatcher.sh 30 72 gzip",
        "oracle   24203 24187  0 09:14 pts/0  ./OSWatcherFM.sh 72 /u01/.../archive",
        "oracle   24219 24187  0 09:14 pts/0  oswvmstat racnode1 09_14_2026",
        "oracle   24221 24187  0 09:14 pts/0  oswiostat racnode1 09_14_2026",
        "oracle   24225 24187  0 09:14 pts/0  oswmeminfo racnode1 09_14_2026",
        "oracle   24229 24187  0 09:14 pts/0  oswprvtnet racnode1 09_14_2026",
        "",
        "-- Collector processes confirmed running on racnode1.",
    ],
)

# ---------------------------------------------------------------------
# 05-high-availability-rac/08-rolling-restart-grid-infrastructure.md
# ---------------------------------------------------------------------

SCREENSHOTS["05-rac-rolling-restart-cluster-check.png"] = (
    "grid@racnode1:~ -- crsctl check cluster -all (verification gate)",
    [
        "$ crsctl check cluster -all",
        "**************************************************************",
        "racnode1:",
        "CRS-4537: Cluster Ready Services is online",
        "CRS-4529: Cluster Synchronization Services is online",
        "CRS-4533: Event Manager is online",
        "**************************************************************",
        "racnode2:",
        "CRS-4537: Cluster Ready Services is online",
        "CRS-4529: Cluster Synchronization Services is online",
        "CRS-4533: Event Manager is online",
        "**************************************************************",
        "racnode3:",
        "CRS-4537: Cluster Ready Services is online",
        "CRS-4529: Cluster Synchronization Services is online",
        "CRS-4533: Event Manager is online",
        "**************************************************************",
        "",
        "$ olsnodes -s -t",
        "racnode1        Active  Unpinned",
        "racnode2        Active  Unpinned",
        "racnode3        Active  Unpinned",
        "",
        "-- racnode3 rejoined cleanly; gate passed, safe to proceed to racnode1.",
    ],
)

# ---------------------------------------------------------------------
# 05-high-availability-rac/09-scan-listener-vip-troubleshooting.md
# ---------------------------------------------------------------------

SCREENSHOTS["05-rac-scan-listener-status.png"] = (
    "grid@racnode1:~ -- srvctl status scan_listener",
    [
        "$ srvctl status scan_listener",
        "SCAN Listener LISTENER_SCAN1 is enabled",
        "SCAN listener LISTENER_SCAN1 is running on node racnode2",
        "SCAN Listener LISTENER_SCAN2 is enabled",
        "SCAN listener LISTENER_SCAN2 is running on node racnode1",
        "SCAN Listener LISTENER_SCAN3 is enabled",
        "SCAN listener LISTENER_SCAN3 is running on node racnode3",
        "",
        "$ dig +short rac-scan.example.com",
        "10.20.30.11",
        "10.20.30.12",
        "10.20.30.13",
        "",
        "-- 3 SCAN listeners running, 3 IPs resolved: matches srvctl config scan.",
    ],
)

# ---------------------------------------------------------------------
# 13-cloud-exadata-oci/01-exadata-storage-cell-patching.md
# ---------------------------------------------------------------------

SCREENSHOTS["13-exadata-cell-patchmgr-summary.png"] = (
    "root@racnode1:~/patch_23.1.x -- patchmgr --patch --rolling",
    [
        "$ ./patchmgr --cells ~/cell_group --patch --rolling --log_dir auto",
        "",
        "2026-08-17 01:02:11 -0500 :Working: DO: Check cells have ssh equivalence...",
        "2026-08-17 01:02:44 -0500 :SUCCESS: DONE: Check cells have ssh equivalence",
        "2026-08-17 01:05:10 -0500 :Working: DO: cel01: Inactivating grid disks...",
        "2026-08-17 01:11:52 -0500 :SUCCESS: DONE: cel01: Grid disks inactive, ASM synced",
        "2026-08-17 01:12:03 -0500 :Working: DO: cel01: Applying patch, rebooting...",
        "2026-08-17 01:47:29 -0500 :SUCCESS: DONE: cel01: Patch applied, cell rebooted",
        "2026-08-17 01:50:16 -0500 :SUCCESS: DONE: cel01: Grid disks active, ASM SYNCED",
        "2026-08-17 01:50:20 -0500 :Working: DO: cel02: Inactivating grid disks...",
        "2026-08-17 02:33:41 -0500 :SUCCESS: DONE: cel02: Grid disks active, ASM SYNCED",
        "2026-08-17 02:33:45 -0500 :Working: DO: cel03: Inactivating grid disks...",
        "2026-08-17 03:16:58 -0500 :SUCCESS: DONE: cel03: Grid disks active, ASM SYNCED",
        "",
        "---------------- patchmgr rolling patch summary ----------------",
        "cel01  SUCCESS   23.1.13.0.0.240612  Imaging status: success",
        "cel02  SUCCESS   23.1.13.0.0.240612  Imaging status: success",
        "cel03  SUCCESS   23.1.13.0.0.240612  Imaging status: success",
        "------------------------------------------------------------------",
        "SUCCESS: DONE: Patch cells.",
    ],
)

# ---------------------------------------------------------------------
# 13-cloud-exadata-oci/02-exadata-image-firmware-upgrade.md
# ---------------------------------------------------------------------

SCREENSHOTS["13-exadata-compute-imageinfo.png"] = (
    "root@racnode1:~ -- dcli -g dbs_group imageinfo -ver",
    [
        "$ dcli -g ~/dbs_group -l root \"imageinfo -ver\"",
        "racnode1: 23.1.13.0.0.240612",
        "racnode2: 23.1.13.0.0.240612",
        "racnode3: 23.1.13.0.0.240612",
        "",
        "$ dcli -g ~/dbs_group -l root \"imageinfo -status\"",
        "racnode1: Active image status: success",
        "racnode2: Active image status: success",
        "racnode3: Active image status: success",
        "",
        "$ dcli -g ~/dbs_group -l root \"imagehistory\" | tail -12",
        "racnode1: Image version: 23.1.13.0.0.240612",
        "racnode1: Imaging mode: out of partition upgrade",
        "racnode1: Imaging status: success",
        "racnode2: Image version: 23.1.13.0.0.240612",
        "racnode2: Imaging mode: out of partition upgrade",
        "racnode2: Imaging status: success",
        "racnode3: Image version: 23.1.13.0.0.240612",
        "racnode3: Imaging mode: out of partition upgrade",
        "racnode3: Imaging status: success",
        "",
        "-- All 3 compute nodes on identical target image version.",
    ],
)

# ---------------------------------------------------------------------
# 13-cloud-exadata-oci/03-oci-autonomous-database-lifecycle.md
# ---------------------------------------------------------------------

SCREENSHOTS["13-oci-adb-lifecycle-state.png"] = (
    "$ oci db autonomous-database get --autonomous-database-id <adb-ocid>",
    [
        "$ oci db autonomous-database get \\",
        "    --autonomous-database-id ocid1.autonomousdatabase.oc1..aaaa...xyz \\",
        "    --query 'data.{state:\"lifecycle-state\",name:\"db-name\",",
        "             compute:\"compute-count\",storageTB:\"data-storage-size-in-tbs\"}'",
        "{",
        "  \"compute\": 8.0,",
        "  \"name\": \"APPDBP1\",",
        "  \"state\": \"AVAILABLE\",",
        "  \"storageTB\": 1.0",
        "}",
        "",
        "-- lifecycle-state = AVAILABLE confirms provisioning/scaling succeeded.",
        "-- compute-count and storage match the requested create/update values.",
    ],
)

# ---------------------------------------------------------------------
# 13-cloud-exadata-oci/04-oci-dbcs-provisioning-patching.md
# ---------------------------------------------------------------------

SCREENSHOTS["13-oci-dbcs-patch-history.png"] = (
    "$ oci db patch-history list --db-system-id <db-system-ocid>",
    [
        "$ oci db patch-history list --db-system-id ocid1.dbsystem.oc1..aaaa...xyz \\",
        "    --query \"data[?\\\"patch-id\\\"=='ocid1.dbpatch.oc1..bbbb...123'].",
        "             {action:action,state:\\\"lifecycle-state\\\",time:\\\"time-ended\\\"}\"",
        "[",
        "  {",
        "    \"action\": \"PRECHECK\",",
        "    \"state\": \"SUCCEEDED\",",
        "    \"time\": \"2026-08-17T01:10:44.201000+00:00\"",
        "  },",
        "  {",
        "    \"action\": \"APPLY\",",
        "    \"state\": \"SUCCEEDED\",",
        "    \"time\": \"2026-08-17T02:47:12.884000+00:00\"",
        "  }",
        "]",
        "",
        "-- Both nodes patched rolling; APPLY state SUCCEEDED confirms completion.",
    ],
)

for fname, (title, lines) in SCREENSHOTS.items():
    render(fname, title, lines)

print(f"\nGenerated {len(SCREENSHOTS)} illustrative screenshots in {OUT_DIR}")
