#!/usr/bin/env python3
"""
Batch E: illustrative terminal-style screenshot PNGs for the Exadata/OCI
IORM, cross-region Data Guard, and OCI Object Storage RMAN backup SOPs in
13-cloud-exadata-oci/. Same SYNTHETIC/ILLUSTRATIVE convention as
generate_screenshots.py (and batches A-D) -- not captured from any real
system. See README.md in this folder for the naming convention.

Usage: python3 generate_batch_e.py
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

SCREENSHOTS["13-exadata-iorm-plan-detail.png"] = (
    "CellCLI> list iormplan detail (fanned out via dcli to all cells)",
    [
        "$ dcli -g ~/cell_group -l root \"cellcli -e list iormplan detail\"",
        "",
        "cel01: name:              iormplan1",
        "cel01: catPlan:",
        "cel01: dbPlan:            name=PRODDB,share=8;",
        "cel01:                    name=REPORTDB,share=3,limit=60;",
        "cel01:                    name=DEVDB,share=1,limit=25,flashCache=off;",
        "cel01:                    name=DEFAULT,share=2",
        "cel01: objective:         auto",
        "cel01: status:            active",
        "",
        "cel02: name:              iormplan1",
        "cel02: dbPlan:            name=PRODDB,share=8;",
        "cel02:                    name=REPORTDB,share=3,limit=60;",
        "cel02:                    name=DEVDB,share=1,limit=25,flashCache=off;",
        "cel02:                    name=DEFAULT,share=2",
        "cel02: objective:         auto",
        "cel02: status:            active",
        "",
        "cel03: -- output identical to cel01/cel02 (verified via diff)",
    ],
)

SCREENSHOTS["13-oci-dg-association-status.png"] = (
    "oci db data-guard-association get -- role, transport, apply lag",
    [
        "$ oci db data-guard-association get \\",
        "    --database-id $database_id \\",
        "    --data-guard-association-id <dg-association-ocid> \\",
        "    --query 'data.{state:\"lifecycle-state\",role:role,transport:\"transport-type\",apply:\"apply-lag\"}'",
        "",
        "{",
        "  \"apply\": \"00:00:12\",",
        "  \"role\": \"STANDBY\",",
        "  \"state\": \"AVAILABLE\",",
        "  \"transport\": \"ASYNC\"",
        "}",
        "",
        "-- apply lag 12s, well within target RPO band for a",
        "-- MAXIMUM_PERFORMANCE/ASYNC cross-region association",
    ],
)

SCREENSHOTS["13-oci-object-storage-backup-complete.png"] = (
    "oci os object list -- rman backup pieces landed in bucket",
    [
        "$ oci os object list --bucket-name appdb1-rman-backups \\",
        "    --query 'data[].{name:name,size:size,timeCreated:\"time-created\"}' \\",
        "    --sort-by timeCreated",
        "",
        "[",
        "  {",
        "    \"name\": \"appdb1/backupset/2026_08_17/o1_mf_nnnd0_CLOUD_L0_....bkp\",",
        "    \"size\": 52887654400,",
        "    \"timeCreated\": \"2026-08-17T01:14:52.221Z\"",
        "  },",
        "  {",
        "    \"name\": \"appdb1/backupset/2026_08_17/o1_mf_annnn_CLOUD_L0_ARCH_..bkp\",",
        "    \"size\": 1884392,",
        "    \"timeCreated\": \"2026-08-17T01:15:08.004Z\"",
        "  },",
        "  {",
        "    \"name\": \"appdb1/autobackup/2026_08_17/o1_mf_s_..........ctl\",",
        "    \"size\": 41943040,",
        "    \"timeCreated\": \"2026-08-17T01:15:22.777Z\"",
        "  }",
        "]",
        "",
        "RMAN> LIST BACKUP OF DATABASE COMPLETED AFTER 'SYSDATE-1';",
        "Piece Name: sbt_tape ...  Status: AVAILABLE   Tag: CLOUD_L0",
        "Backup validation SUCCESSFUL -- 0 corrupt blocks found",
    ],
)

for fname, (title, lines) in SCREENSHOTS.items():
    render(fname, title, lines)

print(f"\nGenerated {len(SCREENSHOTS)} illustrative screenshots in {OUT_DIR}")
