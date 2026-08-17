#!/usr/bin/env python3
"""
Generates illustrative terminal-style screenshot PNGs for "Batch C" of the
Oracle DBA SOP repository (troubleshooting + RAC HA SOPs). These are
SYNTHETIC/ILLUSTRATIVE example outputs (not captured from any real system)
meant to show what a healthy (or diagnostic) command result should look
like. DBAs should replace these with real screenshots captured from their
own environment during actual SOP execution -- see README.md in this
folder for the naming convention.

This file intentionally duplicates the render()/color_for() helpers from
generate_screenshots.py verbatim so the visual style (dark terminal window,
colored title-bar dots, DejaVu Sans Mono font, color-coded lines) matches
exactly, without importing across scripts.

Usage: python3 generate_batch_c.py
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

# --- 11-troubleshooting/05-diagnosing-listener-connectivity-failures.md ---
SCREENSHOTS["11-troubleshooting-listener-tnsping.png"] = (
    "oracle@dbprod01:~ -- tnsping / lsnrctl status",
    [
        "$ tnsping PRODDB",
        "Used parameter files:",
        "/u01/app/oracle/product/19.0.0/dbhome_1/network/admin/sqlnet.ora",
        "",
        "Used TNSNAMES adapter to resolve the alias",
        "Attempting to contact",
        "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=dbprod01)(PORT=1521))",
        "(CONNECT_DATA=(SERVICE_NAME=PRODDB)))",
        "OK (20 msec)",
        "",
        "$ lsnrctl status LISTENER",
        "...",
        "STATUS of the LISTENER",
        "------------------------",
        "Alias                     LISTENER",
        "Version                   TNSLSNR for Linux: Version 19.0.0.0.0",
        "Start Date                16-AUG-2026 08:02:11",
        "Uptime                    0 days 4 hr. 12 min. 5 sec",
        "Security                  ON: Local OS Authentication",
        "Listening Endpoints Summary...",
        "  (DESCRIPTION=(ADDRESS=(PROTOCOL=tcp)(HOST=dbprod01)(PORT=1521)))",
        "Services Summary...",
        "Service \"PRODDB\" has 1 instance(s).",
        "  Instance \"PRODDB\", status READY, has 1 handler(s) for this service.",
        "The command completed successfully",
    ],
)

# --- 11-troubleshooting/06-diagnosing-cpu-io-spikes-using-ash.md ---
SCREENSHOTS["11-troubleshooting-ash-top-sql.png"] = (
    "SQL> Top SQL_ID by ASH sample count (spike window)",
    [
        "SQL> SELECT sql_id, COUNT(*) AS samples,",
        "  2         ROUND(COUNT(*)*1.0/SUM(COUNT(*)) OVER () * 100,1) AS pct",
        "  3  FROM v$active_session_history",
        "  4  WHERE sample_time BETWEEN TO_TIMESTAMP('2026-08-16 09:40:00',",
        "  5    'YYYY-MM-DD HH24:MI:SS') AND TO_TIMESTAMP('2026-08-16 09:55:00',",
        "  6    'YYYY-MM-DD HH24:MI:SS')",
        "  7  GROUP BY sql_id ORDER BY samples DESC FETCH FIRST 10 ROWS ONLY;",
        "",
        "SQL_ID           SAMPLES   PCT",
        "-------------  ---------  ----",
        "7gk3m1xqzpvbn        842  61.4",
        "1a9fh0scv2m4k        188  13.7",
        "c5x8k2wtnq7yd         94   6.8",
        "9 rows selected.",
        "",
        "-- Top wait event/class for the same window",
        "EVENT                       WAIT_CLASS      SAMPLES",
        "---------------------------  --------------  -------",
        "ON CPU                       -                   842",
        "db file sequential read      User I/O            140",
        "log file sync                Commit               52",
    ],
)

# --- 11-troubleshooting/07-diagnosing-ora-01555-snapshot-too-old.md ---
SCREENSHOTS["11-troubleshooting-undostat.png"] = (
    "SQL> v$undostat -- tuned retention / SSO pressure",
    [
        "SQL> SELECT tuned_undoretention, maxquerylen, activeblks,",
        "  2         unexpiredblks, expiredblks",
        "  3  FROM v$undostat ORDER BY end_time DESC FETCH FIRST 5 ROWS ONLY;",
        "",
        "TUNED_UNDORETENTION  MAXQUERYLEN  ACTIVEBLKS  UNEXPIREDBLKS  EXPIREDBLKS",
        "-------------------  -----------  ----------  -------------  -----------",
        "                905         3120       48210         912400         2100",
        "                892         2895       47960         905112         1980",
        "",
        "SQL> SELECT begin_time, end_time, undoblks, txncount, ssolderrcnt,",
        "  2         nospaceerrcnt FROM v$undostat",
        "  3  WHERE ssolderrcnt > 0 OR nospaceerrcnt > 0",
        "  4  ORDER BY end_time DESC FETCH FIRST 5 ROWS ONLY;",
        "",
        "BEGIN_TIME          END_TIME             UNDOBLKS  TXNCOUNT  SSOLDERRCNT  NOSPACEERRCNT",
        "-------------------  -------------------  --------  --------  -----------  -------------",
        "16-AUG-26 09.30.02   16-AUG-26 09.40.02       28410      4210            3              0",
        "1 row selected.",
    ],
)

# --- 11-troubleshooting/08-recovering-corrupted-online-redo-log.md ---
SCREENSHOTS["11-troubleshooting-redolog-v-log-status.png"] = (
    "SQL> v$log / alert log -- redo group status triage",
    [
        "SQL> SELECT group#, thread#, sequence#, bytes/1024/1024 AS mb, members,",
        "  2         archived, status",
        "  3  FROM v$log ORDER BY group#;",
        "",
        "GROUP#  THREAD#  SEQUENCE#    MB  MEMBERS  ARC  STATUS",
        "------  -------  ---------  ----  -------  ---  ----------------",
        "     1        1       4821   200        2  YES  INACTIVE",
        "     2        1       4822   200        2  YES  ACTIVE",
        "     3        1       4823   200        1  NO   CURRENT",
        "",
        "-- Alert log excerpt for the incident:",
        "ORA-00312: online log 3 thread 1: '/u02/oradata/PRODDB/redo03a.log'",
        "ORA-00313: open failed for members of log group 3 of thread 1",
        "",
        "SQL> SELECT l.group#, lf.member, lf.status FROM v$log l",
        "  2  JOIN v$logfile lf ON l.group# = lf.group# ORDER BY l.group#;",
        "",
        "GROUP#  MEMBER                                       STATUS",
        "------  -------------------------------------------  ------",
        "     1  /u02/oradata/PRODDB/redo01a.log",
        "     1  /u03/oradata/PRODDB/redo01b.log",
        "     3  /u02/oradata/PRODDB/redo03a.log",
    ],
)

# --- 05-high-availability-rac/01-add-node-to-rac-cluster.md ---
SCREENSHOTS["05-rac-add-node-cluvfy-post.png"] = (
    "$ cluvfy stage -post nodeadd -n racnode3 -verbose",
    [
        "$ $GRID_HOME/bin/cluvfy stage -post nodeadd -n racnode3 -verbose",
        "Performing post-checks for node addition",
        "",
        "Checking node reachability...",
        "Node reachability check passed from node \"racnode1\"",
        "",
        "Checking user equivalence...",
        "User equivalence check passed",
        "",
        "Checking CRS integrity...",
        "CRS integrity check passed",
        "",
        "Checking Single Client Access Name (SCAN)...",
        "SCAN Status check passed",
        "",
        "Post-check for node addition was successful.",
        "",
        "$ olsnodes -s -t",
        "racnode1  Active  Unpinned",
        "racnode2  Active  Unpinned",
        "racnode3  Active  Unpinned",
    ],
)

# --- 05-high-availability-rac/02-delete-node-from-rac-cluster.md ---
SCREENSHOTS["05-rac-delete-node-cluvfy-post.png"] = (
    "$ cluvfy stage -post nodedel -n racnode3 -verbose",
    [
        "$ $GRID_HOME/bin/cluvfy stage -post nodedel -n racnode3 -verbose",
        "Performing post-checks for node removal",
        "",
        "Checking CRS integrity...",
        "CRS integrity check passed",
        "",
        "Checking shared resources...",
        "Node removal check passed",
        "",
        "Checking node removal...",
        "racnode3 is no longer a member of the cluster",
        "",
        "Post-check for node removal was successful.",
        "",
        "$ olsnodes -s -t",
        "racnode1  Active  Unpinned",
        "racnode2  Active  Unpinned",
    ],
)

# --- 05-high-availability-rac/02b-remove-node-without-software-deletion.md ---
SCREENSHOTS["05-rac-remove-node-olsnodes-status.png"] = (
    "$ olsnodes -s -t / crsctl check cluster -all -- post-removal",
    [
        "$ olsnodes -s -t",
        "racnode1  Active  Unpinned",
        "racnode2  Active  Unpinned",
        "",
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
        "",
        "$ ls -ld /u01/app/19.0.0/grid /u01/app/oracle/product/19.0.0/dbhome_1",
        "drwxr-xr-x 74 grid   oinstall 4096 Jul 16 02:04 /u01/app/19.0.0/grid",
        "drwxr-xr-x 68 oracle oinstall 4096 Jul 16 02:11 .../dbhome_1",
    ],
)

# --- 05-high-availability-rac/03-readd-previously-deleted-node.md ---
SCREENSHOTS["05-rac-readd-node-cluvfy-post.png"] = (
    "$ cluvfy stage -post nodeadd -n racnode3 (rejoin) -verbose",
    [
        "$ $GRID_HOME/bin/cluvfy stage -post nodeadd -n racnode3 -verbose",
        "Performing post-checks for node addition",
        "",
        "Checking node reachability...",
        "Node reachability check passed from node \"racnode1\"",
        "",
        "Checking user equivalence...",
        "User equivalence check passed",
        "",
        "Checking CRS integrity...",
        "CRS integrity check passed",
        "",
        "Post-check for node addition was successful.",
        "",
        "$ olsnodes -s -t",
        "racnode1  Active  Unpinned",
        "racnode2  Active  Unpinned",
        "racnode3  Active  Unpinned",
        "",
        "$ diff /tmp/racnode3_patches.txt /tmp/racnode1_patches.txt",
        "(no differences found - patch levels match)",
    ],
)

# --- 05-high-availability-rac/04-relocate-ocr-voting-disk.md (screenshot 1 of 2: OCR) ---
SCREENSHOTS["05-rac-relocate-ocr-ocrcheck.png"] = (
    "$ ocrconfig -add +OCR_VOTE / ocrcheck",
    [
        "$ ocrconfig -add +OCR_VOTE",
        "",
        "$ ocrcheck",
        "Status of Oracle Cluster Registry is as follows :",
        "         Version                  :          4",
        "         Total space (kbytes)     :     614328",
        "         Used space (kbytes)      :      98104",
        "         Available space (kbytes) :     516224",
        "         ID                       : 1481029384",
        "         Device/File Name         :      +DATA",
        "                                    Device/File integrity check succeeded",
        "         Device/File Name         :  +OCR_VOTE",
        "                                    Device/File integrity check succeeded",
        "",
        "         Cluster registry integrity check succeeded",
        "",
        "         Logical corruption check succeeded",
    ],
)

# --- 05-high-availability-rac/04-relocate-ocr-voting-disk.md (screenshot 2 of 2: voting disk) ---
SCREENSHOTS["05-rac-relocate-votedisk-crsctl.png"] = (
    "$ crsctl replace votedisk +OCR_VOTE / crsctl query css votedisk",
    [
        "$ crsctl replace votedisk +OCR_VOTE",
        "CRS-4256: Updating the profile",
        "Successful addition of voting disk 8f3a2c91d4e05f6bffcf1a0234567890.",
        "Successful addition of voting disk 9a4b3d02e5f16077cfd02b1345678901.",
        "Successful addition of voting disk ab5c4e13f6027188d0e13c2456789012.",
        "Successful deletion of voting disk 1122334455667788990011223344556.",
        "Successful deletion of voting disk 2233445566778899001122334455667.",
        "Successful deletion of voting disk 3344556677889900112233445566778.",
        "CRS-4266: Voting file(s) successfully replaced",
        "",
        "$ crsctl query css votedisk",
        "##  STATE    File Universal Id            File Name Disk group",
        "--  -----    -----------------            --------- ---------",
        " 1. ONLINE   8f3a2c91d4e05f6bffcf1a0234567890 (o/192.168.10.11/OCR_VOTE_CD_01) [OCR_VOTE]",
        " 2. ONLINE   9a4b3d02e5f16077cfd02b1345678901 (o/192.168.10.12/OCR_VOTE_CD_02) [OCR_VOTE]",
        " 3. ONLINE   ab5c4e13f6027188d0e13c2456789012 (o/192.168.10.13/OCR_VOTE_CD_03) [OCR_VOTE]",
        "Located 3 voting disk(s).",
    ],
)

for fname, (title, lines) in SCREENSHOTS.items():
    render(fname, title, lines)

print(f"\nGenerated {len(SCREENSHOTS)} illustrative screenshots in {OUT_DIR}")
