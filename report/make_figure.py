#!/usr/bin/env python3
"""Render the architecture diagram used in the report as a PNG."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FIG_DIR = Path(__file__).resolve().parent / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)
OUT = FIG_DIR / "architecture.png"

W, H = 1800, 820
img = Image.new("RGB", (W, H), "#ffffff")
d = ImageDraw.Draw(img)

BLUE = "#243b55"
LIGHT = "#eef3f9"
GREEN = "#35b57f"
GREEN_BG = "#e8f5ee"
ORANGE = "#d98c2b"
ORANGE_BG = "#fff7ec"
GREY = "#6b7785"

try:
    font_bold = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
    font_small = ImageFont.truetype("DejaVuSans.ttf", 28)
    font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
except OSError:
    font_bold = font_small = font_title = ImageFont.load_default()


def box(x, y, w, h, title, lines, fill=LIGHT, stroke=BLUE, text_color=BLUE):
    d.rounded_rectangle([x, y, x + w, y + h], radius=20, fill=fill, outline=stroke, width=4)
    bbox = d.textbbox((0, 0), title, font=font_bold)
    d.text((x + w / 2 - (bbox[2] - bbox[0]) / 2, y + 26), title, fill=text_color, font=font_bold)
    for i, line in enumerate(lines):
        bbox = d.textbbox((0, 0), line, font=font_small)
        d.text((x + w / 2 - (bbox[2] - bbox[0]) / 2, y + 82 + i * 40), line, fill=text_color, font=font_small)


def arrow_right(x1, y1, x2, y2, label=None):
    d.line([x1, y1, x2, y2], fill=GREY, width=4)
    d.polygon([(x2, y2), (x2 - 16, y2 - 10), (x2 - 16, y2 + 10)], fill=GREY)
    if label:
        bbox = d.textbbox((0, 0), label, font=font_small)
        tw = bbox[2] - bbox[0]
        d.text(((x1 + x2) / 2 - tw / 2, (y1 + y2) / 2 - 34), label, fill=GREY, font=font_small)


def arrow_up(x, y1, y2, label=None):
    d.line([x, y1, x, y2], fill=GREY, width=4)
    d.polygon([(x, y2), (x - 10, y2 + 16), (x + 10, y2 + 16)], fill=GREY)
    if label:
        bbox = d.textbbox((0, 0), label, font=font_small)
        d.text((x + 18, (y1 + y2) / 2 - 14), label, fill=GREY, font=font_small)


d.text((70, 36), "Committee-Verifiable Indexer workflow", fill=BLUE, font=font_title)

# Processing row (lower band).
box(70, 380, 360, 220, "Instance state", ["seed batch", "history cache"], fill="#f7f9fc")
box(540, 380, 360, 220, "propose()", ["local", "deterministic replay"])
box(1010, 380, 360, 220, "aggregate()", ["head-block grouping", "majority tally"])
# Reads card, lower band far right; the read-back arrow enters its top edge.
box(1480, 380, 270, 220, "HTTP / ABI reads", ["SPA, records", "committee"], fill=ORANGE_BG, stroke=ORANGE)

# Consensus row (upper band).
box(1010, 70, 360, 220, "Certified call", ["committee", "certificate verified"], fill=GREEN_BG, stroke=GREEN)
box(1480, 70, 270, 220, "network state", ["records", "signers, history"], fill=GREEN_BG, stroke=GREEN)

arrow_right(430, 490, 540, 490, "observation")
arrow_right(900, 490, 1010, 490, "signed inputs")
arrow_up(1190, 380, 290, "threshold agrees")
arrow_right(1370, 180, 1480, 180, "store record")
# Read-back: network state down to the reads card in the lower band.
d.line([1615, 290, 1615, 380], fill=GREY, width=4)
d.polygon([(1615, 380), (1605, 364), (1625, 364)], fill=GREY)
d.text((1640, 318), "read verified record", fill=GREY, font=font_small)

img.save(OUT)
print(f"Wrote {OUT}")
