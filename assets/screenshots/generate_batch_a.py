#!/usr/bin/env python3
"""
Batch A: additional illustrative terminal-style screenshot PNGs for the
Oracle DBA SOP repository, generated for the 10 SOPs listed in the task
(RAC patching, catctl.pl upgrade, RMAN duplicate migration, Data Guard
failover/switchover/troubleshooting, AWR interpretation guide, and RMAN
spfile/controlfile recovery). These are SYNTHETIC/ILLUSTRATIVE example
outputs (not captured from any real system) meant to show what a healthy
(or diagnostically useful) command result should look like. DBAs should
replace these with real screenshots captured from their own environment
during actual SOP execution -- see README.md in this folder for the
naming convention.

The render() function below is copied verbatim from generate_screenshots.py
so the visual style (dark terminal window, colored title-bar dots,
DejaVu Sans Mono font, color-coded lines) matches exactly.

Usage: python3 generate_batch_a.py
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

SCREENSHOTS["02-patching-rac-opatchauto-summary.png"] = (
    "root@dbprod01:~ -- opatchauto apply (rolling, node1)",
    [
        "# opatchauto apply /u01/software/patches/36414788/36414788 \\",
        "    -oh $GRID_HOME,$ORACLE_HOME",
        "",
        "OPatchauto session is initiated at Wed Aug 12 02:10:44 2026",
        "Session log file location:",
        "  /u01/app/19.0.0/grid/cfgtoollogs/opatchauto/opatchauto2026-08-12_02-11-02AM.log",
        "",
        "Configuration Validation: Successful",
        "Patching validation: Successful",
        "",
        "Bringing down CRS service on home /u01/app/19.0.0/grid",
        "CRS service brought down successfully on home /u01/app/19.0.0/grid",
        "",
        "Start applying binary patches on home /u01/app/19.0.0/grid",
        "Binary patching applied successfully on home /u01/app/19.0.0/grid",
        "",
        "Starting CRS service on home /u01/app/19.0.0/grid",
        "CRS service started successfully on home /u01/app/19.0.0/grid",
        "",
        "OPatchAuto successful.",
        "",
        "Summary of OPatchAuto session:",
        "RAC home: /u01/app/oracle/product/19.0.0/dbhome_1  Summary: SUCCESS",
        "CRS home: /u01/app/19.0.0/grid                     Summary: SUCCESS",
        "",
        "OPatchauto session completed at Wed Aug 12 02:52:19 2026",
        "Time taken to complete the session 41 minutes, 35 seconds",
    ],
)

SCREENSHOTS["03-upgrade-catctl-completion.png"] = (
    "oracle@dbprod01:~ -- catctl.pl catupgrd.sql",
    [
        "$ $ORACLE_HOME/perl/bin/perl catctl.pl -n 4 -l /u01/software/upgrade/logs \\",
        "    -d $ORACLE_HOME/rdbms/admin catupgrd.sql",
        "",
        "Analyzing file catupgrd.sql",
        "Container Database detected.",
        "Number of Cpus         = 4",
        "Total Phases            = 109",
        "",
        "Serial   Phase #:0     <Files> ... Executing Serial Actions",
        "Parallel Phase #:74    <Files> ... Executing Parallel Actions",
        "Serial   Phase #:109   <catcon>: Executing Serial Actions",
        "",
        "------------------------------------------------------",
        "Phases [0-109]        End Time:[2026-08-16 03:41:52]",
        "------------------------------------------------------",
        "",
        "Grand Total Time: 4123 seconds [ORCL]",
        "LOG FILES: (catupgrd*.log)",
        "",
        "Number of Errors: 0",
        "Number of Warnings: 3",
        "Upgrade completed successfully.",
    ],
)

SCREENSHOTS["04-migration-rman-duplicate-finished.png"] = (
    "RMAN> DUPLICATE TARGET DATABASE TO ORCLNEW",
    [
        "RMAN> DUPLICATE TARGET DATABASE TO ORCLNEW FROM ACTIVE DATABASE ...",
        "",
        "Starting Duplicate Db at 16-AUG-2026 04:02:11",
        "using target database control file instead of recovery catalog",
        "allocated channel: aux1",
        "allocated channel: aux2",
        "allocated channel: aux3",
        "allocated channel: aux4",
        "",
        "contents of Memory Script:",
        "{",
        "   sql clone \"alter system set db_name = ''ORCL'' scope=spfile\";",
        "}",
        "executing Memory Script",
        "",
        "Starting backup at 16-AUG-2026 04:02:15",
        "channel aux1: starting datafile copy",
        "channel aux4: finished piece 1 at 16-AUG-2026 04:47:19",
        "Finished backup at 16-AUG-2026 04:47:32",
        "",
        "contents of Memory Script:",
        "{",
        "   Alter clone database open resetlogs;",
        "}",
        "executing Memory Script",
        "",
        "database opened",
        "Finished Duplicate Db at 16-AUG-2026 04:49:03",
    ],
)

SCREENSHOTS["06-dg-failover-dgmgrl-success.png"] = (
    "DGMGRL> FAILOVER TO 'ORCLPRD_DR'",
    [
        "DGMGRL> VALIDATE DATABASE 'ORCLPRD_DR';",
        "",
        "  Database Role:     Physical standby database",
        "  Primary Database:  ORCLPRD",
        "",
        "  Ready for Switchover:  Yes",
        "  Ready for Failover:    Yes (Primary Running)",
        "",
        "DGMGRL> FAILOVER TO 'ORCLPRD_DR';",
        "Performing failover NOW, please wait...",
        "Failover succeeded, new primary is \"ORCLPRD_DR\"",
        "",
        "DGMGRL> SHOW CONFIGURATION;",
        "",
        "Configuration - DGCONFIG_PROD",
        "",
        "  Protection Mode: MaxPerformance",
        "  Members:",
        "  ORCLPRD_DR - Primary database",
        "    ORCLPRD  - Physical standby database (disabled)",
        "               ORA-16661: the standby database needs to be reinstated",
        "",
        "Configuration Status:",
        "SUCCESS",
    ],
)

SCREENSHOTS["06-dg-failover-manual-sql-success.png"] = (
    "SQL> Manual failover -- RECOVER ... FINISH / OPEN",
    [
        "SQL> ALTER DATABASE RECOVER MANAGED STANDBY DATABASE FINISH;",
        "",
        "Database altered.",
        "",
        "SQL> ALTER DATABASE OPEN;",
        "",
        "Database altered.",
        "",
        "SQL> SELECT database_role, open_mode, db_unique_name FROM v$database;",
        "",
        "DATABASE_ROLE    OPEN_MODE            DB_UNIQUE_NAME",
        "---------------- -------------------- ------------------------------",
        "PRIMARY          READ WRITE           ORCLPRD_DR",
    ],
)

SCREENSHOTS["06-dg-switchover-manual-sql-success.png"] = (
    "SQL> ALTER DATABASE SWITCHOVER TO ORCLPRD_DR",
    [
        "SQL> ALTER DATABASE SWITCHOVER TO ORCLPRD_DR;",
        "",
        "Database altered.",
        "",
        "SQL> -- on the new primary",
        "SQL> SELECT database_role, open_mode FROM v$database;",
        "",
        "DATABASE_ROLE    OPEN_MODE",
        "---------------- --------------------",
        "PRIMARY          READ WRITE",
        "",
        "SQL> -- on the former primary, now standby",
        "SQL> SELECT database_role, open_mode, db_unique_name FROM v$database;",
        "",
        "DATABASE_ROLE    OPEN_MODE  DB_UNIQUE_NAME",
        "---------------- ---------- ------------------------------",
        "PHYSICAL STANDBY MOUNTED    ORCLPRD",
    ],
)

SCREENSHOTS["06-dg-lag-troubleshooting-stats.png"] = (
    "SQL> v$dataguard_stats -- transport/apply lag",
    [
        "SQL> SELECT name, value, unit, time_computed, datum_time",
        "  2  FROM v$dataguard_stats",
        "  3  WHERE name IN ('transport lag','apply lag','apply finish time',",
        "  4                  'estimated startup time');",
        "",
        "NAME                      VALUE           UNIT",
        "------------------------- --------------- ------------------------------",
        "transport lag             +00 00:00:02    day(2) to second(0) interval",
        "apply lag                 +00 00:04:18    day(2) to second(0) interval",
        "apply finish time         +00 00:00:41    day(2) to second(3) interval",
        "estimated startup time    23              second",
        "",
        "4 rows selected.",
    ],
)

SCREENSHOTS["08-awr-load-profile-worked-example.png"] = (
    "AWR report -- Report Summary / Load Profile",
    [
        "              Snap Id      Snap Time      Sessions Curs/Sess",
        "            --------- ------------------- -------- ---------",
        "Begin Snap:     18422 16-Aug-26 09:00:00       142       8.1",
        "  End Snap:     18423 16-Aug-26 10:00:00       156       8.4",
        "   Elapsed:               60.00 (mins)",
        "   DB Time:              487.32 (mins)",
        "",
        "Load Profile             Per Second    Per Transaction  Per Exec  Per Call",
        "------------------------ ------------  ----------------  --------  --------",
        "DB Time(s):                      8.1                                  0.02",
        "DB CPU(s):                       3.4                                  0.01",
        "Redo size (bytes):         842,311.2",
        "Logical read (blocks):      48,920.7",
        "Executes (SQL):              3,102.4",
    ],
)

SCREENSHOTS["07-recover-spfile-restore-success.png"] = (
    "RMAN> RESTORE SPFILE FROM AUTOBACKUP",
    [
        "RMAN> STARTUP FORCE NOMOUNT;",
        "",
        "Oracle instance started",
        "",
        "RMAN> SET DBID 1234567890;",
        "",
        "executing command: SET DBID",
        "",
        "RMAN> RESTORE SPFILE FROM AUTOBACKUP;",
        "",
        "Starting restore at 16-AUG-2026 14:02:11",
        "allocated channel: ORA_DISK_1",
        "channel ORA_DISK_1: AUTOBACKUP",
        "  /u01/app/oracle/fra/ORCL/autobackup/2026_08_16/o1_mf_s_..._.bkp found",
        "channel ORA_DISK_1: SPFILE restore from AUTOBACKUP complete",
        "Finished restore at 16-AUG-2026 14:02:19",
        "",
        "RMAN> STARTUP FORCE;",
        "",
        "Oracle instance started",
        "Database mounted.",
        "Database opened.",
    ],
)

SCREENSHOTS["07-recover-controlfile-restore-success.png"] = (
    "RMAN> RESTORE CONTROLFILE FROM AUTOBACKUP",
    [
        "RMAN> RESTORE CONTROLFILE FROM AUTOBACKUP;",
        "",
        "Starting restore at 16-AUG-2026 15:11:04",
        "allocated channel: ORA_DISK_1",
        "channel ORA_DISK_1: restoring control file from AUTOBACKUP",
        "channel ORA_DISK_1: control file restore from AUTOBACKUP complete",
        "output file name=/u01/oradata/ORCL/control01.ctl",
        "output file name=/u02/oradata/ORCL/control02.ctl",
        "output file name=/u01/app/oracle/fra/ORCL/control03.ctl",
        "Finished restore at 16-AUG-2026 15:11:22",
        "",
        "RMAN> ALTER DATABASE MOUNT;",
        "",
        "database mounted",
        "released channel: ORA_DISK_1",
        "",
        "RMAN> RESTORE DATABASE;",
        "RMAN> RECOVER DATABASE;",
        "RMAN> ALTER DATABASE OPEN RESETLOGS;",
        "",
        "Statement processed",
    ],
)

for fname, (title, lines) in SCREENSHOTS.items():
    render(fname, title, lines)

print(f"\nGenerated {len(SCREENSHOTS)} illustrative screenshots in {OUT_DIR}")
