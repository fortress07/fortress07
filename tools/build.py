#!/usr/bin/env python3
"""Shared data and SVG helpers for the fortress07 profile.

Run tools/build_redteam.py to build README.md and assets/. This module holds what
every image needs: the facts (CVEs, projects, stack, links), the palette, font
subsetting and icon loading.

Fonts (JetBrains Mono, OFL-1.1), brand logos (Simple Icons, CC0), glyphs (Primer
Octicons, MIT; Devicon, MIT) are downloaded once into tools/.cache. Each SVG
embeds a subset of the font it actually uses, so GitHub draws it the same on
every OS.
"""

import base64
import html
import io
import pathlib
import re
import urllib.request

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
CACHE = pathlib.Path(__file__).resolve().parent / ".cache"

FONT_URL = "https://cdn.jsdelivr.net/gh/JetBrains/JetBrainsMono@v2.304/fonts/ttf/JetBrainsMono-{}.ttf"
SIMPLE_URL = "https://cdn.jsdelivr.net/npm/simple-icons@13.21.0/icons/{}.svg"
OCTICON_URL = "https://cdn.jsdelivr.net/npm/@primer/octicons@19.8.0/build/svg/{}.svg"
DEVICON_URL = "https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons/{}.svg"
SEMGREP_URL = "https://raw.githubusercontent.com/semgrep/semgrep/develop/semgrep.svg"
WEIGHTS = {400: "Regular", 700: "Bold", 800: "ExtraBold"}

# Palette taken from fortress07.github.io/profile. Images on the profile sit on a
# transparent background, so transparent.py shifts these to mid-tones before use.
THEMES = {
    "dark": dict(BG="#0a0709", PANEL="#120c0f", PANEL2="#1a1116", BORDER="#2b1c23",
                 TEXT="#ece7e9", DIM="#c3bbc0", MUTED="#938a90", FAINT="#5e5459",
                 RED="#ff3b5c", RED_SOFT="#ff8095", ORANGE="#ff7a45", GOLD="#f5b544", GREEN="#4ade80",
                 LIFT="#ffffff"),
}
globals().update(THEMES["dark"])


def use_theme(name):
    globals().update(THEMES[name])


def sev_color(sev):
    return {"CRITICAL": RED, "HIGH": ORANGE, "MODERATE": GOLD}[sev]


PORTFOLIO = "https://fortress07.github.io/profile/"
PROJECT_URL = "https://github.com/fortress07/{}"

DISCLOSURES = [
    # line is the CWE class shown under each row; radar is the blip's bearing and radius
    dict(slug="55640", id="CVE-2026-55640", pkg="nextcloud-mcp-server", score="9.1",
         sev="CRITICAL", cvss="CVSS 3.1", date="2026-06-14", wu="wu-55640",
         line="CWE-306 · Missing Authentication for Critical Function",
         radar=(40, 100)),
    dict(slug="55849", id="CVE-2026-55849", pkg="@cyclonedx/cyclonedx-npm", score="8.5",
         sev="HIGH", cvss="CVSS 4.0", date="2026-06-16", wu="wu-55849",
         line="CWE-78 · OS Command Injection",
         radar=(110, 120)),
    dict(slug="71538", id="CVE-2026-71538", pkg="@cyclonedx/cyclonedx-npm", score="8.5",
         sev="HIGH", cvss="CVSS 4.0", date="2026-07-07", wu="wu-71538",
         line="CWE-78 · OS Command Injection",
         radar=(165, 70)),
    dict(slug="pbf", id="Mapbox bounty", pkg="mapbox/pbf", score="8.1",
         sev="HIGH", cvss="CVSS 3.1", date="2026-07-09", wu="wu-h1-pbf",
         line="CWE-94 · Code Injection",
         radar=(232, 105)),
    dict(slug="57207", id="CVE-2026-57207", pkg="netbox-mcp-server", score="5.9",
         sev="MODERATE", cvss="CVSS 3.1", date="2026-06-18", wu="wu-57207",
         line="CWE-306 · Missing Authentication for Critical Function · CWE-1059 · Insufficient Technical Documentation",
         radar=(300, 128)),
]

PROJECTS = [
    # langs: GitHub's language split on 2026-10-27, used only for the bar widths.
    # Languages under 1% (fortress-scan's test samples, Makefiles) are the grey tail.
    dict(slug="fortress-scan", title="Fortress Scan", repo="fortress-scan",
         desc="Traces untrusted data through code in 22 languages to find vulnerabilities. "
              "Reports in Vietnamese.",
         langs=[("Python", "#3572a5", 98.0)]),
    dict(slug="poisonlab", title="PoisonLab", repo="LLM-Data-Poisoning-Simulation-Sandbox",
         desc="Poison your own fine-tuning data, measure what the attack achieves, and test "
              "whether your review would catch it.",
         langs=[("Python", "#3572a5", 91.7), ("JavaScript", "#f1e05a", 5.7), ("C", "#555555", 2.1)]),
    dict(slug="s-graph", title="S-Graph", repo="project_S-Graph",
         desc="Plot functions and get the area of a plane region by clicking its vertices on "
              "the graph.",
         langs=[("JavaScript", "#f1e05a", 84.0), ("CSS", "#663399", 9.2), ("HTML", "#e34c26", 6.8)]),
]

# Icon keys: a bare name is Simple Icons, "oct:" Octicons, "dev:" Devicon (plain),
# "semgrep" the three-dot mark cut from Semgrep's own logo, and "mark:Xyz" a letter
# tile for a language no icon set covers (Pascal).
STACK = [
    ("LANGUAGES", [("python", "Python"), ("javascript", "JavaScript"), ("c", "C"),
                   ("cplusplus", "C++"), ("dev:java/java-plain", "Java"), ("mark:Pas", "Pascal"), ("gnubash", "Bash"),
                   ("dev:powershell/powershell-plain", "PowerShell"), ("html5", "HTML5"), ("css3", "CSS3")]),
    ("TOOLING", [("nodedotjs", "Node.js"), ("git", "Git"), ("githubactions", "GitHub Actions"),
                 ("pytest", "pytest"), ("ruff", "Ruff"), ("sonarqube", "SonarQube"), ("linux", "Linux")]),
    ("AI / ML", [("pytorch", "PyTorch"), ("huggingface", "Transformers"), ("huggingface", "PEFT")]),
    ("OFFENSIVE", [("burpsuite", "Burp Suite"), ("oct:eye-24", "Nmap"), ("oct:database-24", "sqlmap"),
                   ("wireshark", "Wireshark"), ("oct:file-binary-24", "IDA Pro")]),
    ("INFRA & DEFENSE", [("docker", "Docker"), ("pfsense", "pfSense"), ("oct:shield-24", "Suricata")]),
    ("CODE AUDIT", [("semgrep", "Semgrep"), ("oct:codescan-24", "CodeQL"), ("owasp", "OWASP Top 10")]),
    ("FOCUS", [("oct:globe-24", "Web & API pentest"), ("oct:code-review-24", "Source code audit"),
               ("oct:workflow-24", "Taint analysis"), ("oct:package-dependencies-24", "Supply chain"),
               ("oct:hubot-24", "LLM / MCP security")]),
]

CONTACTS = [
    dict(slug="email", href="mailto:vophuvinh15012007@gmail.com", icon="gmail", color="#ea4335", label="Email",
         handle="vophuvinh15012007@gmail.com"),
    dict(slug="hackerone", href="https://hackerone.com/fortress07vn", icon="hackerone", color="TEXT", label="HackerOne",
         handle="hackerone.com/fortress07vn"),
    dict(slug="portfolio", href=PORTFOLIO, icon="oct:globe-24", color="RED", label="Portfolio",
         handle="fortress07.github.io/profile"),
    dict(slug="facebook", href="https://www.facebook.com/f0r7r355", icon="facebook", color="#0866ff", label="Facebook",
         handle="facebook.com/f0r7r355"),
    dict(slug="instagram", href="https://www.instagram.com/f0r7r355", icon="instagram", color="#ff3d8b", label="Instagram",
         handle="instagram.com/f0r7r355"),
    dict(slug="tiktok", href="https://www.tiktok.com/@fortress.vn", icon="tiktok", color="TEXT", label="TikTok",
         handle="tiktok.com/@fortress.vn"),
]

BRAND = {"python": "#3776ab", "javascript": "#f7df1e", "c": "#a8b9cc", "gnubash": "#4eaa25",
         "html5": "#e34f26", "css3": "#1572b6", "nodedotjs": "#5fa04e", "git": "#f05032",
         "githubactions": "#2088ff", "pytest": "#0a9edc", "ruff": "#d7ff64",
         "sonarqube": "#4e9bcd", "linux": "#fcc624", "pytorch": "#ee4c2c",
         "huggingface": "#ffd21e", "burpsuite": "#ff6633", "owasp": "TEXT",
         "cplusplus": "#00599c", "wireshark": "#1679a7",
         "dev:java/java-plain": "#f89820", "dev:powershell/powershell-plain": "#5391fe",
         "oct:eye-24": "#4f9fd8", "oct:database-24": "#9bcf53", "oct:file-binary-24": "#c792ea",
         "semgrep": "#13bf95", "oct:codescan-24": "#58a6ff",
         "mark:Pas": "#e3f171",  # GitHub's colour for Pascal
         "docker": "#2496ed", "pfsense": "#212121", "oct:shield-24": "#f08a24",  # Suricata has no logo set
         # FOCUS is about how I work, not a product, so it takes the accent
         "oct:globe-24": "RED", "oct:code-review-24": "RED", "oct:workflow-24": "RED",
         "oct:package-dependencies-24": "RED", "oct:hubot-24": "RED"}
# Hand-picked lifts for logos that sink into the dark panel; readable() covers the rest.
DARK_ICON = {"python": "#4b8bbe", "cplusplus": "#659ad2", "wireshark": "#3fa3d9", "css3": "#2f8fd8",
             "githubactions": "#3b9bff", "sonarqube": "#5aa9d8", "pytest": "#2bb6f0"}


# ---------------------------------------------------------------- resources

def fetch(url, dest):
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url) as resp:
            dest.write_bytes(resp.read())
    return dest


def font_path(weight):
    name = WEIGHTS[weight]
    return fetch(FONT_URL.format(name), CACHE / f"JetBrainsMono-{name}.ttf")


_face_cache = {}


def font_face(weight, chars):
    """Return a base64 woff2 subset of JetBrains Mono holding only `chars`."""
    key = (weight, chars)
    if key not in _face_cache:
        font = TTFont(font_path(weight), recalcTimestamp=False)  # same bytes every build
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = []  # no ligatures: "--" and "->" must stay literal
        opts.hinting = False
        opts.name_IDs = [1, 2]
        sub = subset.Subsetter(opts)
        sub.populate(text=chars)
        sub.subset(font)
        buf = io.BytesIO()
        font.flavor = "woff2"
        font.save(buf)
        _face_cache[key] = base64.b64encode(buf.getvalue()).decode()
    return _face_cache[key]


def icon_paths(name):
    """Fill-less path markup for an icon, plus its viewBox width and height."""
    if name == "semgrep":
        svg = fetch(SEMGREP_URL, CACHE / "semgrep-logo.svg").read_text(encoding="utf-8")
        svg = re.search(r'<g id="semgrep-ellipsis".*?</g>', svg, re.S).group(0)
        vb = (0, 0, 512, 200)
    else:
        if name.startswith("oct:"):
            src = fetch(OCTICON_URL.format(name[4:]), CACHE / f"oct-{name[4:]}.svg")
        elif name.startswith("dev:"):
            src = fetch(DEVICON_URL.format(name[4:]), CACHE / f"dev-{name[4:].replace('/', '-')}.svg")
        else:
            src = fetch(SIMPLE_URL.format(name), CACHE / f"si-{name}.svg")
        svg = src.read_text(encoding="utf-8")
        vb = tuple(float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split())
    paths = []
    for tag in re.findall(r"<path\b[^>]*>", svg):
        d = re.search(r'\sd="([^"]+)"', tag).group(1)
        rule = re.search(r'fill-rule="(\w+)"', tag)
        paths.append(f'<path d="{d}"' + (f' fill-rule="{rule.group(1)}"' if rule else "") + "/>")
    return "".join(paths), vb


def letter_mark(svg, text, x, y, size, color):
    """A rounded tile with white letters, for languages that have no logo."""
    pad = size * .08
    side = size - 2 * pad
    svg.add(f'<rect x="{x + pad:.1f}" y="{y + pad:.1f}" width="{side:.1f}" height="{side:.1f}" '
            f'rx="{size * .14:.1f}" fill="{color}"/>')
    svg.put_text(x + size / 2, y + pad + side * .7, text, size=side * .46, weight=800, fill="#ffffff",
                 anchor="middle")


def icon(name, x, y, size, color):
    """Draw an icon centred in a size x size box at (x, y), keeping its aspect ratio."""
    paths, (vx, vy, vw, vh) = icon_paths(name)
    s = size / max(vw, vh)
    ox, oy = x + (size - vw * s) / 2 - vx * s, y + (size - vh * s) / 2 - vy * s
    return f'<g transform="translate({ox:.2f} {oy:.2f}) scale({s:.4f})" fill="{color}">{paths}</g>'


# ---------------------------------------------------------------- svg builder

def esc(s):
    return html.escape(s, quote=True)


def tw(s, size, ls=0.0):
    """Width of a JetBrains Mono string (every glyph advances 0.6 em)."""
    return len(s) * (0.6 * size + ls)


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h, self.title = w, h, title
        self.defs, self.body, self.css = [], [], []
        self.chars = {}
        self._ids = 0

    def uid(self, prefix):
        self._ids += 1
        return f"{prefix}{self._ids}"

    def add(self, markup):
        self.body.append(markup)

    def text(self, x, y, spans, size=16, weight=400, fill=None, anchor="start", ls=0, attrs=""):
        """spans: a string, or a list of (text, fill, weight) tuples."""
        fill = fill or TEXT
        if isinstance(spans, str):
            spans = [(spans, fill, weight)]
        parts = []
        for span in spans:
            if isinstance(span, str):
                s, f, wt = span, fill, weight
            elif len(span) == 2:
                (s, f), wt = span, weight
            else:
                s, f, wt = span
            self.chars.setdefault(wt, set()).update(s)
            parts.append(f'<tspan fill="{f}" font-weight="{wt}">{esc(s)}</tspan>')
        ls_attr = f' letter-spacing="{ls}"' if ls else ""
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}"'
                f'{ls_attr} {attrs}>{"".join(parts)}</text>')

    def put_text(self, *a, **k):
        self.add(self.text(*a, **k))

    def render(self):
        faces = "".join(
            f"@font-face{{font-family:'JBM';font-weight:{wt};"
            f"src:url(data:font/woff2;base64,{font_face(wt, ''.join(sorted(chars)))}) format('woff2')}}"
            for wt, chars in sorted(self.chars.items()))
        style = (faces + "text{font-family:'JBM','JetBrains Mono',ui-monospace,SFMono-Regular,"
                 "Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre}" + "".join(self.css))
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" xml:space="preserve" role="img" aria-label="{esc(self.title)}">'
                f'<title>{esc(self.title)}</title><style>{style}</style>'
                f'<defs>{"".join(self.defs)}</defs>{"".join(self.body)}</svg>')

    def save(self, name):
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / name).write_text(self.render(), encoding="utf-8")
        print(f"  assets/{name}")


# ---------------------------------------------------------------- colour helpers

def token(color):
    """'TEXT' or 'RED' mean the current theme's colour; anything else is literal."""
    return globals()[color] if color in THEMES["dark"] else color


def _luminance(color):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return .2126 * ch(r) + .7152 * ch(g) + .0722 * ch(b)


def _mix(a, b, t):
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


def readable(color, ratio=2.6):
    """Push a brand colour toward LIFT until it stands out from the chip fill."""
    color = token(color)
    bg = _luminance(PANEL2)
    for step in range(0, 21):
        c = _mix(color, LIFT, step / 20)
        hi, lo = sorted((_luminance(c), bg), reverse=True)
        if (hi + .05) / (lo + .05) >= ratio:
            return c
    return c


def appear(begin, dur=0.18):
    return f'<animate attributeName="opacity" from="0" to="1" begin="{begin}s" dur="{dur}s" fill="freeze"/>'


def blink(period=1.05):
    return f'<animate attributeName="opacity" values="1;0" dur="{period}s" calcMode="discrete" repeatCount="indefinite"/>'


def lift(name):
    """Brand colour for an icon, lifted where it would sink into a dark surface."""
    picked = DARK_ICON.get(name)
    return token(picked) if picked else readable(BRAND.get(name, "TEXT"))
