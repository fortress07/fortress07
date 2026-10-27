#!/usr/bin/env python3
"""Images with transparent backgrounds, readable on both GitHub themes.

Every colour drawn here is clamped to a mid-tone luminance band, so the same
SVG works on GitHub's white and on its #0d1117. Used by build_redteam.py for the
radar, the CVSS pills and the icons; set OUT_DIR, call setup(), then build.
"""

import math
import re

import build as b

OUT_DIR = b.ROOT

# Every colour drawn on a transparent background must stay readable on white
# and on GitHub's #0d1117. Luminance between these bounds keeps roughly 3:1
# contrast against both.
LUM_LO, LUM_HI = .12, .30
GREY = "#8b949e"


def balanced(color):
    color = b.token(color)
    lum = b._luminance(color)
    if LUM_LO <= lum <= LUM_HI:
        return color
    target = "#000000" if lum > LUM_HI else "#ffffff"
    for step in range(1, 41):
        c = b._mix(color, target, step / 40)
        if LUM_LO <= b._luminance(c) <= LUM_HI:
            return c
    return c


def setup():
    b.use_theme("dark")
    b.OUT = OUT_DIR / "assets"
    global RED, SEV, GREEN, GOLD
    RED = balanced(b.RED)
    GREEN = balanced(b.GREEN)
    GOLD = balanced(b.GOLD)
    SEV = {s: balanced(b.sev_color(s)) for s in ("CRITICAL", "HIGH", "MODERATE")}


# ---------------------------------------------------------------- images

def build_radar():
    W, H = 420, 424
    cx, cy, R = 210, 190, 150
    svg = b.Svg(W, H, "Radar sweep: 4 CVEs and 1 bug bounty, plotted by CVSS score.")
    svg.defs.append('<filter id="soft" x="-50%" y="-50%" width="200%" height="200%">'
                    '<feGaussianBlur stdDeviation="2.2" result="b"/>'
                    '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')

    def pt(bearing, r):
        a = math.radians(bearing)
        return cx + r * math.sin(a), cy - r * math.cos(a)

    for i, r in enumerate((R, R * .75, R * .5, R * .25)):
        svg.add(f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="none" stroke="{RED}" '
                f'stroke-opacity="{.55 if i == 0 else .22}"/>')
    svg.add(f'<path d="M{cx - R} {cy}H{cx + R}M{cx} {cy - R}V{cy + R}" stroke="{RED}" '
            'stroke-opacity=".22" stroke-dasharray="2 5"/>')
    ticks = []
    for deg in range(0, 360, 5):
        ln = 7 if deg % 30 == 0 else 3.5
        (x1, y1), (x2, y2) = pt(deg, R), pt(deg, R - ln)
        ticks.append(f"M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}")
    svg.add(f'<path d="{"".join(ticks)}" stroke="{RED}" stroke-opacity=".6"/>')
    for deg, label in ((0, "000"), (90, "090"), (180, "180"), (270, "270")):
        x, y = pt(deg, R + 18)
        svg.put_text(x, y + 4, label, size=11, fill=GREY, anchor="middle")

    period, trail, slices = 6, 64, 22
    wedges = []
    for i in range(slices):
        a2, a1 = -i * trail / slices, -(i + 1) * trail / slices
        (x1, y1), (x2, y2) = pt(a1, R), pt(a2, R)
        wedges.append(f'<path d="M{cx} {cy}L{x1:.2f} {y1:.2f}A{R} {R} 0 0 1 {x2:.2f} {y2:.2f}Z" '
                      f'fill="{RED}" fill-opacity="{.28 * (1 - i / slices) ** 1.7:.3f}"/>')
    svg.add(f'<g><animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" '
            f'to="360 {cx} {cy}" dur="{period}s" repeatCount="indefinite"/>{"".join(wedges)}'
            f'<path d="M{cx} {cy}V{cy - R}" stroke="{RED}" stroke-width="2" filter="url(#soft)"/></g>')

    for d in b.DISCLOSURES:
        bearing, r = d["radar"]
        x, y = pt(bearing, r)
        col, hit = SEV[d["sev"]], period * bearing / 360
        svg.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="none" stroke="{col}" opacity="0">'
                f'<animate attributeName="r" values="5.5;21;21" keyTimes="0;.3;1" begin="{hit:.2f}s" '
                f'dur="{period}s" repeatCount="indefinite"/>'
                f'<animate attributeName="opacity" values=".9;0;0" keyTimes="0;.3;1" begin="{hit:.2f}s" '
                f'dur="{period}s" repeatCount="indefinite"/></circle>')
        svg.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{col}" opacity=".55">'
                f'<animate attributeName="opacity" values="1;.55;.55" keyTimes="0;.55;1" begin="{hit:.2f}s" '
                f'dur="{period}s" repeatCount="indefinite"/></circle>')
        right = x + 13 + b.tw(f'{d["slug"]} {d["score"]}', 13) < cx + R - 6
        svg.put_text(x + 13 if right else x - 13, y + 4.5,
                     [(d["slug"], GREY, 400), (" " + d["score"], col, 800)], size=13,
                     anchor="start" if right else "end")
    svg.add(f'<circle cx="{cx}" cy="{cy}" r="9" fill="none" stroke="{RED}" stroke-opacity=".6"/>'
            f'<circle cx="{cx}" cy="{cy}" r="3" fill="{RED}"/>')

    log = [[("[*] ", GREY, 700), ("sweep complete", GREY, 400)],
           [("[+] ", GREEN, 700), ("found ", GREY, 400), ("4 CVE", RED, 700)],
           [("[+] ", GREEN, 700), ("found ", GREY, 400), ("1 bounty", GOLD, 700)]]
    lx = cx - b.tw("[+] found 1 bounty", 12) / 2
    for i, spans in enumerate(log):
        svg.add(f'<g opacity="0">{b.appear(1.2 + i * .45, .12)}{svg.text(lx, 376 + i * 18, spans, size=12)}</g>')
    svg.save("radar.svg")


def build_pills():
    for d in b.DISCLOSURES:
        col = SEV[d["sev"]]
        W, H = 108, 26
        svg = b.Svg(W, H, f'CVSS {d["score"]} {d["sev"].title()}')
        svg.add(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="13" fill="{col}" '
                f'fill-opacity=".12" stroke="{col}" stroke-opacity=".7"/>')
        svg.put_text(W / 2, 17.5, [(d["score"], col, 800), ("  " + d["sev"], col, 700)], size=11.5,
                     anchor="middle")
        svg.save(f'cvss-{d["slug"]}.svg')


def glyph(key, color, size, name):
    (b.OUT / "icons").mkdir(parents=True, exist_ok=True)
    svg = b.Svg(size, size, name)
    if key.startswith("mark:"):
        b.letter_mark(svg, key[5:], 0, 0, size, color)
    else:
        svg.add(b.icon(key, 0, 0, size, color))
    svg.save(f"icons/{name}.svg")


def slug(label):
    return re.sub(r"[^a-z0-9]+", "-", label.lower().replace("+", "p")).strip("-")


# ---------------------------------------------------------------- readme helpers

def icon(name, size, alt=""):
    return f'<img src="assets/icons/{name}.svg" width="{size}" height="{size}" alt="{b.esc(alt)}">'


CWE_SHORT = {"CWE-306": "Missing Authentication", "CWE-78": "OS Command Injection",
             "CWE-94": "Code Injection", "CWE-1059": "Insufficient Documentation"}


def weakness(line):
    """One short-named CWE per line, so the table stays narrow enough not to wrap IDs."""
    cwes = [part for part in line.split(" · ") if part.startswith("CWE-")]
    return "<br>".join(f"{cwe} {CWE_SHORT[cwe]}" for cwe in cwes)
