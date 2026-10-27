#!/usr/bin/env python3
"""Red-team draft of the profile README.

    uv run --with fonttools --with brotli tools/build_redteam.py [OUT_DIR]

A glitching FORTRESS header, then plain numbered sections in Markdown text.
The images (header, radar, CVSS pills, icons) have transparent backgrounds and
mid-tone colours, so one set reads on both GitHub themes.

Data comes from build.py; transparent.py draws the radar, pills and icons.
"""

import pathlib
import sys

import build as b
import transparent as bt

OUT_DIR = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else b.ROOT
bt.OUT_DIR = OUT_DIR

# ---------------------------------------------------------------- images

def build_hero():
    W, H = 1000, 300
    x0, y0, x1, y1 = 110, 30, 890, 266
    red, teal, grey = bt.RED, bt.balanced("#22d3ee"), bt.GREY
    svg = b.Svg(W, H, "FORTRESS. Operator Võ Phú Vinh: vulnerability research, freelance pentest.")
    svg.css.append(
        ".ga{animation:ga 4.2s steps(1) infinite}.gb{animation:gb 4.2s steps(1) infinite}"
        "@keyframes ga{0%,84%{opacity:0;transform:none}85%{opacity:.85;transform:translate(-6px,0)}"
        "88%{transform:translate(4px,0)}91%{transform:translate(-3px,0)}94%,100%{opacity:0;transform:none}}"
        "@keyframes gb{0%,85%{opacity:0;transform:none}86%{opacity:.85;transform:translate(5px,0)}"
        "89%{transform:translate(-4px,0)}92%{transform:translate(2px,0)}95%,100%{opacity:0;transform:none}}"
        ".base{animation:base 4.2s steps(1) infinite}"
        "@keyframes base{0%,85%{transform:none}86%{transform:translate(2px,0)}90%{transform:translate(-1px,0)}93%,100%{transform:none}}"
        "@media (prefers-reduced-motion:reduce){.ga,.gb,.base,.scan{animation:none;display:none}.base{display:inline}}")
    svg.defs.append('<clipPath id="bandA"><rect x="0" y="118" width="1000" height="18"/>'
                    '<rect x="0" y="158" width="1000" height="9"/></clipPath>'
                    '<clipPath id="bandB"><rect x="0" y="138" width="1000" height="14"/>'
                    '<rect x="0" y="171" width="1000" height="6"/></clipPath>'
                    f'<linearGradient id="scan" x1="0" x2="1"><stop offset="0" stop-color="{red}" stop-opacity="0"/>'
                    f'<stop offset=".5" stop-color="{red}" stop-opacity=".5"/>'
                    f'<stop offset="1" stop-color="{red}" stop-opacity="0"/></linearGradient>')

    # targeting brackets
    ln = 28
    corners = [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]
    svg.add("".join(f'<path d="M{x + dx * ln} {y}H{x}V{y + dy * ln}" fill="none" stroke="{red}" '
                    f'stroke-width="2.5"/>' for x, y, dx, dy in corners))
    mid = (x0 + x1) / 2
    svg.add(f'<path d="M{mid} {y0 - 7}v14M{mid} {y1 - 7}v14M{x0 - 7} {(y0 + y1) / 2}h14M{x1 - 7} {(y0 + y1) / 2}h14" '
            f'stroke="{red}" stroke-opacity=".55"/>')
    svg.add(f'<rect x="{x0 + 6}" y="{y0}" width="{x1 - x0 - 12}" height="2" fill="url(#scan)" class="scan">'
            f'<animate attributeName="y" values="{y0 + 4};{y1 - 4};{y0 + 4}" dur="6s" repeatCount="indefinite"/></rect>')

    # HUD readouts
    hud = 12
    svg.put_text(x0 + 18, y0 + 30, [("OPERATOR ", grey, 700), ("// Võ Phú Vinh", grey, 400)], size=hud, ls=1.2)
    svg.add(f'<circle cx="{x1 - 104}" cy="{y0 + 26}" r="4" fill="{red}">{b.blink(1.1)}</circle>')
    svg.put_text(x1 - 18, y0 + 30, "ENGAGED", size=hud, weight=700, fill=grey, anchor="end", ls=2)
    svg.put_text(x1 - 18, y1 - 18, [("CVE ", grey, 400), ("x4", red, 700), ("  BOUNTY ", grey, 400),
                                    ("x1", red, 700)], size=hud, anchor="end", ls=1.2)

    # glitching callsign
    word, fs, ls = "FORTRESS", 92, 10
    cx = W / 2 + ls / 2
    for cls, color, clip in (("gb", teal, "bandB"), ("ga", red, "bandA")):
        svg.add(f'<g class="{cls}" clip-path="url(#{clip})">'
                + svg.text(cx, 172, word, size=fs, weight=800, fill=color, anchor="middle", ls=ls) + "</g>")
    svg.add('<g class="base">' + svg.text(cx, 172, word, size=fs, weight=800, fill=red, anchor="middle", ls=ls) + "</g>")
    svg.put_text(W / 2 + 1.5, 214, "VULNERABILITY RESEARCH · FREELANCE PENTEST", size=13.5, fill=grey,
                 anchor="middle", ls=3)
    svg.save("hero.svg")


def build_icons():
    """Only the icons this README shows: the stack tables, the achievements and the links."""
    for cat, items in b.STACK:
        for key, label in items:
            bt.glyph(key, bt.balanced(b.lift(key)), 48, bt.slug(label))
    for key, color, name in [("oct:shield-check-24", b.ORANGE, "finalist"), ("oct:trophy-24", b.GOLD, "first"),
                             ("hackerone", b.GREEN, "bounty"), ("oct:bug-24", b.RED, "cve")]:
        bt.glyph(key, bt.balanced(color), 24, name)
    for c in b.CONTACTS:
        bt.glyph(c["icon"], bt.balanced(c["color"]), 24, f'link-{c["slug"]}')


# ---------------------------------------------------------------- readme

PER_ROW = 5  # stack tables wrap after this many columns, so they never scroll sideways
STACK_TITLES = {"LANGUAGES": "Languages", "TOOLING": "Tooling", "AI / ML": "AI / ML",
                "OFFENSIVE": "Offensive", "INFRA & DEFENSE": "Infra & defense", "CODE AUDIT": "Code audit",
                "FOCUS": "Focus areas"}


def stack_table(items):
    """Names over icons, wrapped into balanced rows of at most PER_ROW."""
    rows = -(-len(items) // PER_ROW)
    per = -(-len(items) // rows)
    chunks = [items[k:k + per] for k in range(0, len(items), per)]
    pad = lambda cells: cells + [""] * (per - len(cells))
    lines = []
    for n, chunk in enumerate(chunks):
        names = [label if n == 0 else f"**{label}**" for _, label in chunk]
        icons = [bt.icon(bt.slug(label), 48, label) for _, label in chunk]
        lines.append("| " + " | ".join(pad(names)) + " |")
        if n == 0:
            lines.append("|" + ":-:|" * per)
        lines.append("| " + " | ".join(pad(icons)) + " |")
    return "\n".join(lines)


def build_readme():
    awards = [
        ("finalist", "Finalist", "Consolation Prize", "Cybersecurity Student Contest (CSC) 2026 · Group A"),
        ("first", "1st Place", "Champion", "HCMUTE Capture the Flag (UTECTF) 2026"),
        ("bounty", "1x Bounty", "Mapbox · HackerOne", ""),
        ("cve", "4x CVE", "Responsible disclosure", ""),
    ]
    out = [
        '<p align="center"><img src="assets/hero.svg" width="100%" alt="FORTRESS. Operator Võ Phú Vinh: '
        'vulnerability research, freelance pentest."></p>',

        "## 01. About me",
        "- Information Security student at **HCMUTE**, Ho Chi Minh City.\n"
        "- **Finalist** (Consolation Prize) at the Cybersecurity Student Contest (CSC) 2026, Group A.\n"
        "- **1st place** at HCMUTE Capture the Flag (UTECTF) 2026.\n"
        "- Freelance pentester: web and API testing, source code audit, LLM and MCP security.\n"
        "- Vulnerability researcher with **4 CVEs** and **1 bug bounty** on HackerOne.\n"
        "- Responsible disclosure: report privately, help ship the fix, publish once users are safe.",

        "## 02. Achievements",
        "| | Result | Event |\n|:-:|---|---|\n" + "\n".join(
            f"| {bt.icon(n, 22)} | **{title}** · {sub} | {event} |" for n, title, sub, event in awards),

        "## 03. Vulnerability disclosures",
        '<p align="center"><img src="assets/radar.svg" width="340" alt="Radar sweep: 4 CVEs and 1 bug '
        'bounty, plotted by CVSS score."></p>',
        "| CVSS | Finding | Weakness | Date |\n|:-:|---|---|:-:|\n" + "\n".join(
            f'| <img src="assets/cvss-{d["slug"]}.svg" alt="{d["score"]} {d["sev"].title()}"> '
            f'| [**{d["id"]}**]({b.PORTFOLIO}#/{d["wu"]})<br><sub><code>{d["pkg"]}</code></sub> '
            f'| {bt.weakness(d["line"])} | {d["date"]} |' for d in b.DISCLOSURES),

        "## 04. Projects",
        "| Project | What it does | Language |\n|---|---|---|\n" + "\n".join(
            f'| [**{p["title"].replace(" ", "&nbsp;")}**]({b.PROJECT_URL.format(p["repo"])}) | {p["desc"]} | '
            + "<br>".join(l[0] for l in p["langs"]) + " |"
            for p in b.PROJECTS),

        "## 05. Languages & tools",
    ]
    for cat, items in b.STACK:
        out += [f"### {STACK_TITLES[cat]}", stack_table(items)]
    out += [
        "## 06. Links",
        "| | Channel | Address |\n|:-:|---|---|\n" + "\n".join(
            f'| {bt.icon("link-" + c["slug"], 20)} | **{c["label"]}** | [{c["handle"]}]({c["href"]}) |'
            for c in b.CONTACTS),
        '<p align="center"><samp>[*] session closed · stay curious, disclose responsibly</samp></p>',
    ]
    (OUT_DIR / "README.md").write_text("\n\n".join(out) + "\n", encoding="utf-8")
    print("  README.md")


def main():
    bt.setup()
    print(f"writing to {OUT_DIR}:")
    build_hero()
    bt.build_radar()
    bt.build_pills()
    build_icons()
    build_readme()


if __name__ == "__main__":
    main()
