#!/usr/bin/env python3
"""
Generates illustrative terminal-style screenshot PNGs for the Oracle DBA
SOP repository. These are SYNTHETIC/ILLUSTRATIVE example outputs (not
captured from any real system) meant to show what a healthy command
result should look like. DBAs should replace these with real screenshots
captured from their own environment during actual SOP execution -- see
README.md in this folder for the naming convention.

Usage: python3 generate_screenshots.py
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

SCREENSHOTS["01-installation-runinstaller-success.png"] = (
    "oracle@dbprod01:~ -- silent install",
    [
        "$ ./runInstaller -silent -responseFile /u01/software/19c/db_install.rsp ...",
        "Launching Oracle Database Setup Wizard...",
        "",
        "[WARNING] [INS-13014] Target environment do not meet some optional requirements.",
        "   ACTION: Identify the list of requirements that have not been met.",
        "",
        "You can find the log of this install session at:",
        " /u01/app/oraInventory/logs/installActions2026-08-16_09-14-02AM.log",
        "",
        "Prepare in progress.",
        "Prepare successful.",
        "Copy files in progress.",
        "Copy files successful.",
        "Link binaries in progress.",
        "Link binaries successful.",
        "Setup files in progress.",
        "Setup files successful.",
        "",
        "As a root user, execute the following script(s):",
        "        1. /u01/app/oraInventory/orainstRoot.sh",
        "        2. /u01/app/oracle/product/19.0.0/dbhome_1/root.sh",
        "",
        "Successfully Setup Software.",
    ],
)

SCREENSHOTS["02-patching-opatch-lsinventory.png"] = (
    "oracle@dbprod01:~ -- opatch lsinventory",
    [
        "$ $ORACLE_HOME/OPatch/opatch lsinventory | tail -20",
        "Oracle Interim Patch Installer version 12.2.0.1.42",
        "Oracle Home       : /u01/app/oracle/product/19.0.0/dbhome_1",
        "",
        "Installed Top-level Products (1):",
        "Oracle Database 19c                                                19.0.0.0.0",
        "",
        "Interim patches (3) :",
        "Patch  36414915     : applied on Wed Jul 16 02:11:44 2026",
        "   Unique Patch ID: 27544122",
        "   Patch description: \"OJVM RELEASE UPDATE 19.24.0.0.0\"",
        "Patch  36414179     : applied on Wed Jul 16 02:04:18 2026",
        "   Unique Patch ID: 27543980",
        "   Patch description: \"Database Release Update : 19.24.0.0.0\"",
        "Patch  29585399     : applied on Mon Jan 12 22:40:05 2026",
        "   Patch description: \"OCW RELEASE UPDATE 19.24.0.0.0\"",
        "",
        "OPatch succeeded.",
    ],
)

SCREENSHOTS["02-patching-datapatch-verbose.png"] = (
    "oracle@dbprod01:~ -- datapatch -verbose",
    [
        "$ $ORACLE_HOME/OPatch/datapatch -verbose",
        "SQL Patching tool version 19.24.0.0.0 Production on Wed Jul 16 02:15:10 2026",
        "Log file for this invocation:",
        "  /u01/app/oracle/cfgtoollogs/sqlpatch/sqlpatch_20418_2026_07_16_02_15_10/sqlpatch.log",
        "",
        "Connecting to database...OK",
        "Bootstrapping registry and package to current versions...done",
        "Determining current state...done",
        "",
        "Adding patches to installation queue and performing prereq checks...done",
        "Installation queue:",
        "  The following patches will be applied:",
        "    36414179 (Database Release Update : 19.24.0.0.0)",
        "    36414915 (OJVM RELEASE UPDATE 19.24.0.0.0)",
        "",
        "Installing patches...",
        "Patch installation complete.  Total patches installed: 2",
        "",
        "Validating logfiles...done",
        "SQL Patching tool complete on Wed Jul 16 02:38:47 2026",
    ],
)

SCREENSHOTS["06-dg-show-configuration.png"] = (
    "DGMGRL> show configuration",
    [
        "DGMGRL> show configuration;",
        "",
        "Configuration - DGCONFIG_PROD",
        "",
        "  Protection Mode: MaxAvailability",
        "  Members:",
        "  PRODDB_A - Primary database",
        "    PRODDB_B - Physical standby database",
        "",
        "Fast-Start Failover: DISABLED",
        "",
        "Configuration Status:",
        "SUCCESS   (status updated 12 seconds ago)",
    ],
)

SCREENSHOTS["06-dg-show-database-verbose.png"] = (
    "DGMGRL> show database verbose PRODDB_B",
    [
        "DGMGRL> show database verbose PRODDB_B;",
        "",
        "Database - PRODDB_B",
        "",
        "  Role:               PHYSICAL STANDBY",
        "  Intended State:     APPLY-ON",
        "  Transport Lag:      0 seconds (computed 1 second ago)",
        "  Apply Lag:          0 seconds (computed 1 second ago)",
        "  Average Apply Rate: 2.86 MByte/s",
        "  Real Time Query:    ON",
        "  Instance(s):",
        "    PRODDB_B",
        "",
        "Database Status:",
        "SUCCESS",
    ],
)

SCREENSHOTS["06-dg-switchover-output.png"] = (
    "DGMGRL> switchover to PRODDB_B",
    [
        "DGMGRL> switchover to PRODDB_B;",
        "Performing switchover NOW, please wait...",
        "New primary database \"PRODDB_B\" is opening...",
        "Oracle Clusterware is restarting database \"PRODDB_A\" ...",
        "Switchover succeeded, new primary is \"PRODDB_B\"",
        "",
        "DGMGRL> show configuration;",
        "  Members:",
        "  PRODDB_B - Primary database",
        "    PRODDB_A - Physical standby database",
        "",
        "Configuration Status:",
        "SUCCESS",
    ],
)

SCREENSHOTS["07-rman-backup-summary.png"] = (
    "RMAN> backup database plus archivelog",
    [
        "RMAN> backup database plus archivelog delete input;",
        "",
        "Starting backup at 16-AUG-2026 01:00:11",
        "channel ORA_DISK_1: starting archived log backup set",
        "channel ORA_DISK_1: finished piece 1 at 16-AUG-2026 01:00:24",
        "Finished backup at 16-AUG-2026 01:00:25",
        "",
        "Starting backup at 16-AUG-2026 01:00:26",
        "channel ORA_DISK_1: starting full datafile backup set",
        "input datafile file number=00001 name=/u02/oradata/PRODDB/system01.dbf",
        "channel ORA_DISK_1: finished piece 1 at 16-AUG-2026 01:14:52",
        "Finished backup at 16-AUG-2026 01:14:53",
        "",
        "Starting Control File and SPFILE Autobackup at 16-AUG-2026 01:14:55",
        "Finished Control File and SPFILE Autobackup at 16-AUG-2026 01:14:58",
    ],
)

SCREENSHOTS["07-rman-restore-validate.png"] = (
    "RMAN> restore database validate",
    [
        "RMAN> restore database validate;",
        "",
        "Starting restore at 16-AUG-2026 03:00:02",
        "channel ORA_DISK_1: starting validation of datafile backup set",
        "channel ORA_DISK_1: restore validate complete, elapsed time: 00:06:41",
        "",
        "List of Datafiles",
        "=================",
        "File #  Status  Marked Corrupt  Empty Blocks",
        "1       OK      0               1245",
        "2       OK      0               890",
        "3       OK      0               102",
        "",
        "Finished restore at 16-AUG-2026 03:07:02",
    ],
)

SCREENSHOTS["08-awr-top-wait-events.png"] = (
    "AWR report -- Top 10 Foreground Events by Total Wait Time",
    [
        "Event                          Waits   Total Wait Time (sec)  Avg Wait  % DB time",
        "-----------------------------  ------  ---------------------  --------  ---------",
        "DB CPU                            -            1,842               -      61.4",
        "db file sequential read      412,908              612            1ms      20.4",
        "log file sync                 88,214              201            2ms       6.7",
        "read by other session          9,442               98           10ms       3.3",
        "gc buffer busy acquire          6,110               71           11ms       2.4",
        "direct path read                4,209               58           14ms       1.9",
    ],
)

SCREENSHOTS["09-audit-privilege-review.png"] = (
    "SQL> DBA_SYS_PRIVS review",
    [
        "SQL> SELECT grantee, privilege FROM dba_sys_privs",
        "  2  WHERE privilege = 'DBA' ORDER BY grantee;",
        "",
        "GRANTEE                       PRIVILEGE",
        "------------------------------ ----------------------------",
        "SYS                            DBA",
        "SYSTEM                         DBA",
        "APP_ADMIN_ROLE                 DBA",
        "",
        "3 rows selected.",
    ],
)

SCREENSHOTS["12-healthcheck-tablespace-usage.png"] = (
    "SQL> Tablespace usage summary",
    [
        "SQL> @tablespace_usage.sql",
        "",
        "TABLESPACE_NAME   SIZE_GB   USED_GB   FREE_GB   PCT_USED",
        "----------------  --------  --------  --------  --------",
        "SYSTEM               2.00      1.21      0.79      60.5",
        "SYSAUX               4.00      2.87      1.13      71.8",
        "USERS               200.00    142.30     57.70      71.2",
        "APP_DATA            500.00    468.90     31.10      93.8   <-- WARN >90%",
        "APP_IDX             150.00     61.44     88.56      41.0",
        "TEMP                 32.00      4.10     27.90      12.8",
    ],
)

SCREENSHOTS["03-autoupgrade-deploy-summary.png"] = (
    "$ java -jar autoupgrade.jar -config upgrade.cfg -mode deploy",
    [
        "Processing config file ...",
        "1 Jobs found",
        "",
        "Type 'help' to list console commands",
        "job 100 completed at 03/12 avg 34 min",
        "",
        "----------------- Summary  -----------------",
        "Number of databases            [ 1 ]",
        "Jobs finished successfully     [1]",
        "Jobs failed                    [0]",
        "----------------------------------------------",
        "Results at /u01/app/oracle/cfgtoollogs/autoupgrade/PRODDB/status.log",
    ],
)

SCREENSHOTS["04-expdp-completion-summary.png"] = (
    "$ expdp system/*** directory=DP_DIR dumpfile=prod_exp_%U.dmp",
    [
        "Export: Release 19.0.0.0.0 - Production on Sun Aug 16 06:20:11 2026",
        "Starting \"SYSTEM\".\"SYS_EXPORT_SCHEMA_01\":",
        "Estimate in progress using BLOCKS method...",
        "Total estimation using BLOCKS method: 48.2 GB",
        "Processing object type SCHEMA_EXPORT/TABLE/TABLE_DATA",
        ". . exported \"APP\".\"ORDERS\"                        14.28 GB 22,104,981 rows",
        ". . exported \"APP\".\"ORDER_ITEMS\"                    9.61 GB 88,442,120 rows",
        "Master table \"SYSTEM\".\"SYS_EXPORT_SCHEMA_01\" successfully loaded/unloaded",
        "Dump file set for SYSTEM.SYS_EXPORT_SCHEMA_01 is:",
        "  /u01/dpdump/prod_exp_01.dmp",
        "Job \"SYSTEM\".\"SYS_EXPORT_SCHEMA_01\" completed with 0 error(s) at 07:48:32",
    ],
)

for fname, (title, lines) in SCREENSHOTS.items():
    render(fname, title, lines)

print(f"\nGenerated {len(SCREENSHOTS)} illustrative screenshots in {OUT_DIR}")
