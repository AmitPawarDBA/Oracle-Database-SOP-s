#!/usr/bin/env python3
"""
Generates illustrative terminal-style screenshot PNGs for Batch B of the
Oracle DBA SOP repository (07-backup-recovery recovery SOPs and
11-troubleshooting SOPs). These are SYNTHETIC/ILLUSTRATIVE example outputs
(not captured from any real system) meant to show what a healthy command
result should look like, matching the visual style established in
generate_screenshots.py. DBAs should replace these with real screenshots
captured from their own environment during actual SOP execution -- see
README.md in this folder for the naming convention.

Usage: python3 generate_batch_b.py
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

# 1. 07-backup-recovery/05-recover-datafile.md
SCREENSHOTS["07-recover-datafile-completion.png"] = (
    "RMAN> RESTORE DATAFILE 7; RECOVER DATAFILE 7;",
    [
        "RMAN> RESTORE DATAFILE 7;",
        "",
        "Starting restore at 16-AUG-2026 11:40:02",
        "using channel ORA_DISK_1",
        "channel ORA_DISK_1: restoring datafile 00007 to /u01/oradata/ORCL/users01.dbf",
        "channel ORA_DISK_1: reading from backup piece /u03/fra/ORCL/backupset/...",
        "channel ORA_DISK_1: restore complete, elapsed time: 00:02:14",
        "Finished restore at 16-AUG-2026 11:42:19",
        "",
        "RMAN> RECOVER DATAFILE 7;",
        "",
        "Starting recover at 16-AUG-2026 11:42:24",
        "starting media recovery",
        "archived log for thread 1 with sequence 1201 is already on disk",
        "archived log for thread 1 with sequence 1202 is already on disk",
        "media recovery complete, elapsed time: 00:00:38",
        "Finished recover at 16-AUG-2026 11:43:05",
    ],
)

# 2. 07-backup-recovery/06-recover-block-corruption.md
SCREENSHOTS["07-block-corruption-validation.png"] = (
    "SQL> v$database_block_corruption -- post-BMR validation",
    [
        "SQL> SELECT file#, block#, blocks, corruption_type",
        "  2  FROM v$database_block_corruption;",
        "",
        "no rows selected",
        "",
        "SQL> SELECT COUNT(*) FROM v$database_block_corruption;",
        "",
        "  COUNT(*)",
        "----------",
        "         0",
        "",
        "-- All previously corrupt blocks recovered via RECOVER CORRUPTION LIST",
    ],
)

# 3. 07-backup-recovery/07-full-database-restore-recovery.md
SCREENSHOTS["07-full-restore-recovery-completion.png"] = (
    "RMAN> RESTORE DATABASE; RECOVER DATABASE; ALTER DATABASE OPEN;",
    [
        "RMAN> RESTORE DATABASE;",
        "RMAN> RECOVER DATABASE;",
        "RMAN> ALTER DATABASE OPEN;",
        "",
        "Starting restore at 16-AUG-2026 09:18:02",
        "channel ORA_DISK_1: restoring datafile 00001 to /u02/oradata/ORCL/system01.dbf",
        "channel ORA_DISK_1: restoring datafile 00003 to /u02/oradata/ORCL/undotbs01.dbf",
        "channel ORA_DISK_1: reading from backup piece /u03/fra/ORCL/backupset/...",
        "Finished restore at 16-AUG-2026 10:30:35",
        "",
        "Starting recover at 16-AUG-2026 10:30:41",
        "media recovery complete, elapsed time: 00:18:47",
        "Finished recover at 16-AUG-2026 10:49:28",
        "",
        "Statement processed.",
        "database opened",
    ],
)

# 4. 07-backup-recovery/08-point-in-time-recovery-pitr.md
SCREENSHOTS["07-pitr-resetlogs-completion.png"] = (
    "RMAN> SET UNTIL SCN ...; RECOVER DATABASE; ALTER DATABASE OPEN RESETLOGS;",
    [
        "RMAN> RUN {",
        "  2>   SET UNTIL SCN 48213092;",
        "  3>   RESTORE DATABASE;",
        "  4>   RECOVER DATABASE;",
        "  5> }",
        "",
        "Starting restore at 16-AUG-2026 10:02:14",
        "Finished restore at 16-AUG-2026 10:44:57",
        "",
        "Starting recover at 16-AUG-2026 10:45:03",
        "media recovery complete, elapsed time: 00:06:12",
        "Finished recover at 16-AUG-2026 10:51:15",
        "",
        "RMAN> ALTER DATABASE OPEN RESETLOGS;",
        "",
        "database opened",
        "Statement processed.",
    ],
)

# 5. 07-backup-recovery/09-tablespace-restore-recovery.md
SCREENSHOTS["07-recover-tablespace-completion.png"] = (
    "RMAN> RESTORE TABLESPACE users; RECOVER TABLESPACE users;",
    [
        "RMAN> RESTORE TABLESPACE users;",
        "RMAN> RECOVER TABLESPACE users;",
        "",
        "Starting restore at 16-AUG-2026 11:02:10",
        "channel ORA_DISK_1: restoring datafile 00004 to /u02/oradata/ORCL/users01.dbf",
        "channel ORA_DISK_1: restore complete, elapsed time: 00:03:22",
        "Finished restore at 16-AUG-2026 11:05:32",
        "",
        "Starting recover at 16-AUG-2026 11:05:41",
        "starting media recovery",
        "archived log for thread 1 with sequence 1198 is already on disk",
        "archived log for thread 1 with sequence 1199 is already on disk",
        "media recovery complete, elapsed time: 00:01:47",
        "Finished recover at 16-AUG-2026 11:07:28",
    ],
)

# 6. 07-backup-recovery/10-tspitr-recovery-using-auxiliary-database.md
SCREENSHOTS["07-tspitr-auxiliary-completion.png"] = (
    "RMAN> RECOVER TABLESPACE ... AUXILIARY DESTINATION",
    [
        "RMAN> RECOVER TABLESPACE users",
        "  2>   UNTIL TIME \"TO_DATE('2026-08-16 09:45:00','YYYY-MM-DD HH24:MI:SS')\"",
        "  3>   AUXILIARY DESTINATION '/u06/tspitr_aux';",
        "",
        "Starting recover at 16-AUG-2026 12:00:04",
        "creating automatic instance, with SID='zqvt'",
        "contents of Memory Script:",
        "{",
        "   restore clone tablespace  \"USERS\";",
        "   switch clone datafile all;",
        "}",
        "executing Memory Script",
        "",
        "Finished recover at 16-AUG-2026 12:14:52",
        "Removing automatic instance",
        "Automatic instance removed",
        "recovery request accomplished",
    ],
)

# 7. 11-troubleshooting/01-diagnosing-resolving-blocking-locks.md
SCREENSHOTS["11-troubleshooting-blocking-locks-query.png"] = (
    "SQL> Blocker / Waiter Chain (v$lock join)",
    [
        "SQL> SELECT blocker.sid AS blocker_sid, blocker_sess.username AS blocker_user,",
        "  2         waiter.sid AS waiter_sid, waiter_sess.username AS waiter_user,",
        "  3         waiter.type AS lock_type, waiter_sess.seconds_in_wait",
        "  4  FROM v$lock blocker JOIN v$lock waiter ... ;",
        "",
        "BLOCKER_SID BLOCKER_USER  WAITER_SID WAITER_USER  LOCK_TYPE  SECONDS_IN_WAIT",
        "----------- ------------- ---------- ------------ ---------- ---------------",
        "        137 APP_OWNER            159 APP_OWNER    TX                     842",
        "        137 APP_OWNER            212 APP_OWNER    TX                     301",
        "",
        "2 rows selected.",
    ],
)

# 8. 11-troubleshooting/02-diagnosing-ora-00060-deadlocks.md
SCREENSHOTS["11-troubleshooting-deadlock-trace.png"] = (
    "alert_ORCL.log -- ORA-00060 deadlock excerpt",
    [
        "$ adrci exec=\"show alert -p \\\"message_text like '%ORA-00060%'\\\"\"",
        "",
        "2026-08-16T09:44:12.221+00:00",
        "ORA-00060: Deadlock detected. More info in file",
        "/u01/app/oracle/diag/rdbms/orcl/ORCL/trace/ORCL_ora_20418.trc.",
        "",
        "-- Deadlock graph excerpt from the trace file:",
        "Resource Name          process session holds waits  process session holds waits",
        "TX-000a0011-000004d2      25      137     X              31      159           X",
        "TX-0003001c-00000a19      31      159     X              25      137           X",
        "",
        "current SQL statement for this session:",
        "UPDATE orders SET status = 'SHIPPED' WHERE order_id = :b1",
    ],
)

# 9. 11-troubleshooting/03-flashback-database-to-restore-point.md
SCREENSHOTS["11-troubleshooting-flashback-success.png"] = (
    "SQL> FLASHBACK DATABASE TO RESTORE POINT",
    [
        "SQL> SHUTDOWN IMMEDIATE;",
        "Database closed.",
        "Database dismounted.",
        "ORACLE instance shut down.",
        "",
        "SQL> STARTUP MOUNT;",
        "ORACLE instance started.",
        "Database mounted.",
        "",
        "SQL> FLASHBACK DATABASE TO RESTORE POINT before_release_2026_08_16;",
        "",
        "Flashback complete.",
        "",
        "SQL> ALTER DATABASE OPEN RESETLOGS;",
        "",
        "Database altered.",
    ],
)

# 10a. 11-troubleshooting/04-diagnosing-archiver-stuck-fra-full.md (alert log excerpt)
SCREENSHOTS["11-fra-full-alert-log-excerpt.png"] = (
    "alert_ORCL.log -- FRA full / archiver stuck",
    [
        "$ tail -30 $ORACLE_BASE/diag/rdbms/orcl/ORCL/trace/alert_ORCL.log",
        "",
        "ORA-19815: WARNING: db_recovery_file_dest_size of 214748364800 bytes",
        "  is 97.32% used",
        "",
        "ARC0: Error 19809 Creating archive log file to '/u03/fra/ORCL/archivelog/...'",
        "ORA-19809: limit exceeded for recovery files",
        "ORA-19804: cannot reclaim 41943040 bytes disk space from",
        "  214748364800 limit",
        "",
        "WARNING: All online logs need archiving - could not allocate new log",
        "Thread 1 cannot allocate new log, sequence 1245",
        "Checkpoint not complete",
    ],
)

# 10b. 11-troubleshooting/04-diagnosing-archiver-stuck-fra-full.md (resolved usage)
SCREENSHOTS["11-fra-recovery-file-dest-resolved.png"] = (
    "SQL> v$recovery_file_dest -- post-remediation",
    [
        "SQL> SELECT name, ROUND(space_used/space_limit*100,1) AS pct_used",
        "  2  FROM v$recovery_file_dest;",
        "",
        "NAME                            PCT_USED",
        "------------------------------  --------",
        "/u03/fra                            62.4",
        "",
        "SQL> SELECT process, status, sequence# FROM v$archive_processes",
        "  2  WHERE status != 'STOPPED';",
        "",
        "PROCESS   STATUS     SEQUENCE#",
        "--------  ---------  ----------",
        "ARC0      ACTIVE           1246",
        "ARC1      ACTIVE           1246",
        "",
        "-- Archiving resumed, commit hang cleared",
    ],
)

for fname, (title, lines) in SCREENSHOTS.items():
    render(fname, title, lines)

print(f"\nGenerated {len(SCREENSHOTS)} illustrative screenshots in {OUT_DIR}")
