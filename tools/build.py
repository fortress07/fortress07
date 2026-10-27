#!/usr/bin/env python3
"""Generate every SVG under assets/ for the fortress07 profile README.

    uv run --with fonttools --with brotli tools/build.py

Each image is drawn twice, into assets/dark/ and assets/light/, and README.md
picks one with <picture> so it matches the viewer's GitHub theme.

Fonts (JetBrains Mono, OFL-1.1), brand logos (Simple Icons, CC0) and glyphs
(Primer Octicons, MIT) are downloaded once into tools/.cache. Each SVG embeds a
subset of the font it actually uses, so GitHub draws it the same on every OS.

To add a new CVE, append it to DISCLOSURES and rerun. README.md lists the
row images by slug, so add a matching line there too.
"""

import base64
import html
import io
import math
import pathlib
import re
import urllib.request

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"  # set per theme by use_theme()
CACHE = pathlib.Path(__file__).resolve().parent / ".cache"

FONT_URL = "https://cdn.jsdelivr.net/gh/JetBrains/JetBrainsMono@v2.304/fonts/ttf/JetBrainsMono-{}.ttf"
SIMPLE_URL = "https://cdn.jsdelivr.net/npm/simple-icons@13.21.0/icons/{}.svg"
OCTICON_URL = "https://cdn.jsdelivr.net/npm/@primer/octicons@19.8.0/build/svg/{}.svg"
DEVICON_URL = "https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons/{}.svg"
SEMGREP_URL = "https://raw.githubusercontent.com/semgrep/semgrep/develop/semgrep.svg"
WEIGHTS = {400: "Regular", 700: "Bold", 800: "ExtraBold"}

# Dark palette taken from fortress07.github.io/profile; the light one keeps its
# crimson and warm greys but darkens every accent enough to read on white.
THEMES = {
    "dark": dict(BG="#0a0709", PANEL="#120c0f", PANEL2="#1a1116", BORDER="#2b1c23",
                 TEXT="#ece7e9", DIM="#c3bbc0", MUTED="#938a90", FAINT="#5e5459",
                 RED="#ff3b5c", RED_SOFT="#ff8095", ORANGE="#ff7a45", GOLD="#f5b544", GREEN="#4ade80",
                 GRID="#ffffff", GRID_OP=.035, GLOW_OP=.17, SHINE="#ffffff", SHINE_OP=.07,
                 SWEEP_OP=.30, LIFT="#ffffff"),
    "light": dict(BG="#fffdfd", PANEL="#fbf8f9", PANEL2="#f4eef1", BORDER="#e6dce1",
                  TEXT="#1f1519", DIM="#4d4247", MUTED="#75686e", FAINT="#a3969c",
                  RED="#e0234e", RED_SOFT="#c41d44", ORANGE="#d9530f", GOLD="#b7791f", GREEN="#16a34a",
                  GRID="#2b1c23", GRID_OP=.05, GLOW_OP=.08, SHINE="#e0234e", SHINE_OP=.05,
                  SWEEP_OP=.20, LIFT="#000000"),
}
globals().update(THEMES["dark"])


def use_theme(name):
    global OUT
    globals().update(THEMES[name])
    OUT = ROOT / "assets" / name


def sev_color(sev):
    return {"CRITICAL": RED, "HIGH": ORANGE, "MODERATE": GOLD}[sev]


PORTFOLIO = "https://fortress07.github.io/profile/"

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

# Icon keys: a bare name is Simple Icons, "oct:" Octicons, "dev:" Devicon (plain), and
# "semgrep" the three-dot mark cut from Semgrep's own logo.
STACK = [
    ("LANGUAGES", [("python", "Python"), ("javascript", "JavaScript"), ("c", "C"),
                   ("cplusplus", "C++"), ("dev:java/java-plain", "Java"), ("gnubash", "Bash"),
                   ("dev:powershell/powershell-plain", "PowerShell"), ("html5", "HTML5"), ("css3", "CSS3")]),
    ("TOOLING", [("nodedotjs", "Node.js"), ("git", "Git"), ("githubactions", "GitHub Actions"),
                 ("pytest", "pytest"), ("ruff", "Ruff"), ("sonarqube", "SonarQube"), ("linux", "Linux")]),
    ("AI / ML", [("pytorch", "PyTorch"), ("huggingface", "Transformers"), ("huggingface", "PEFT")]),
    ("OFFENSIVE", [("burpsuite", "Burp Suite"), ("oct:eye-24", "Nmap"), ("oct:database-24", "sqlmap"),
                   ("wireshark", "Wireshark"), ("oct:file-binary-24", "IDA Pro")]),
    ("CODE AUDIT", [("semgrep", "Semgrep"), ("oct:codescan-24", "CodeQL"), ("owasp", "OWASP Top 10")]),
    ("FOCUS", [("oct:globe-24", "Web & API pentest"), ("oct:code-review-24", "Source code audit"),
               ("oct:workflow-24", "Taint analysis"), ("oct:package-dependencies-24", "Supply chain"),
               ("oct:hubot-24", "LLM / MCP security")]),
]

CONTACTS = [
    dict(slug="email", icon="gmail", color="#ea4335", label="Email",
         handle="vophuvinh15012007@gmail.com"),
    dict(slug="hackerone", icon="hackerone", color="TEXT", label="HackerOne",
         handle="hackerone.com/fortress07vn"),
    dict(slug="portfolio", icon="oct:globe-24", color="RED", label="Portfolio",
         handle="fortress07.github.io/profile"),
    dict(slug="facebook", icon="facebook", color="#0866ff", label="Facebook",
         handle="facebook.com/f0r7r355"),
    dict(slug="instagram", icon="instagram", color="#ff3d8b", label="Instagram",
         handle="instagram.com/f0r7r355"),
    dict(slug="tiktok", icon="tiktok", color="TEXT", label="TikTok",
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
         # FOCUS is about how I work, not a product, so it takes the accent
         "oct:globe-24": "RED", "oct:code-review-24": "RED", "oct:workflow-24": "RED",
         "oct:package-dependencies-24": "RED", "oct:hubot-24": "RED"}
# Hand-picked lifts for logos that sink into the dark panel; readable() covers the rest.
DARK_ICON = {"python": "#4b8bbe", "cplusplus": "#659ad2", "wireshark": "#3fa3d9", "css3": "#2f8fd8",
             "githubactions": "#3b9bff", "sonarqube": "#5aa9d8", "pytest": "#2bb6f0"}
LIGHT_ICON = {"ruff": "#30173d"}


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
        font = TTFont(font_path(weight))
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
        print(f"  {(OUT / name).relative_to(ROOT).as_posix()}")


def card(x, y, w, h, rx=14, fill=None, stroke=None):
    return (f'<rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" rx="{rx}" '
            f'fill="{fill or PANEL}" stroke="{stroke or BORDER}"/>')


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


# ---------------------------------------------------------------- banner

def build_banner():
    W, H = 1200, 432
    svg = Svg(W, H, "Võ Phú Vinh (Fortress). Information Security student at HCMUTE, "
                    "security researcher and freelance pentester.")
    cx, cy, R = 958, 232, 148
    svg.defs.append(
        f'<clipPath id="win"><rect width="{W}" height="{H}" rx="18"/></clipPath>'
        '<pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">'
        f'<path d="M28 0H0V28" fill="none" stroke="{GRID}" stroke-opacity="{GRID_OP}"/></pattern>'
        f'<radialGradient id="glow" cx="{cx}" cy="{cy}" r="380" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{RED}" stop-opacity="{GLOW_OP}"/>'
        f'<stop offset="1" stop-color="{RED}" stop-opacity="0"/></radialGradient>'
        '<filter id="soft" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="2.4" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')

    svg.add(f'<g clip-path="url(#win)"><rect width="{W}" height="{H}" fill="{BG}"/>'
            f'<rect width="{W}" height="{H}" fill="url(#grid)"/>'
            f'<rect width="{W}" height="{H}" fill="url(#glow)"/>'
            f'<rect width="{W}" height="44" fill="{PANEL}"/>'
            f'<path d="M0 44.5H{W}" stroke="{BORDER}"/></g>')
    svg.add(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="18" fill="none" stroke="{BORDER}"/>')

    # title bar
    for i, c in enumerate((RED, GOLD, GREEN)):
        svg.add(f'<circle cx="{26 + i * 22}" cy="22" r="6" fill="{c}" fill-opacity=".9"/>')
    svg.put_text(W / 2, 27, "root@fortress: ~/profile", size=13, fill=MUTED, anchor="middle")
    svg.add(f'<rect x="1078.5" y="12.5" width="94" height="20" rx="10" fill="{GREEN}" '
            f'fill-opacity=".08" stroke="{GREEN}" stroke-opacity=".35"/>')
    svg.add(f'<circle cx="1093" cy="22.5" r="3.5" fill="{GREEN}"/>'
            f'<circle cx="1093" cy="22.5" r="3.5" fill="none" stroke="{GREEN}">'
            '<animate attributeName="r" values="3.5;9" dur="1.8s" repeatCount="indefinite"/>'
            '<animate attributeName="opacity" values=".8;0" dur="1.8s" repeatCount="indefinite"/></circle>')
    svg.put_text(1104, 27, "ONLINE", size=11, weight=700, fill=GREEN, ls=1.6)

    # identity
    x0 = 56
    svg.put_text(x0, 112, [("// ", RED, 700), ("SECURITY RESEARCHER · FREELANCE PENTESTER", MUTED, 400)],
                 size=13, ls=2.2)
    svg.put_text(x0 - 3, 180, "Võ Phú Vinh", size=62, weight=800, fill=TEXT, ls=-1)
    svg.put_text(x0, 222, [("[ ", FAINT, 400), ("Fortress", RED, 700), (" ]", FAINT, 400)], size=26)

    # terminal session
    fs, cw = 17, 0.6 * 17
    prompt = [("root@fortress", RED, 700), (":", MUTED, 400), ("~", GOLD, 700), ("# ", MUTED, 400)]
    plen = len("root@fortress:~# ") * cw

    def typed(y, cmd, begin, per_char):
        cid = svg.uid("t")
        steps = ";".join(f"{i * cw:.1f}" for i in range(len(cmd) + 1))
        svg.defs.append(
            f'<clipPath id="{cid}"><rect x="{x0 + plen - 1:.1f}" y="{y - fs}" height="{fs * 1.6}" width="0">'
            f'<animate attributeName="width" values="{steps}" begin="{begin}s" '
            f'dur="{per_char * (len(cmd) + 1):.2f}s" calcMode="discrete" fill="freeze"/></rect></clipPath>')
        return svg.text(x0 + plen, y, cmd, size=fs, fill=TEXT, attrs=f'clip-path="url(#{cid})"')

    out1 = [("Information Security student @ ", DIM, 400), ("HCMUTE", TEXT, 700)]

    svg.add(svg.text(x0, 288, prompt, size=fs) + typed(288, "whoami", 0.5, 0.09))
    svg.add(f'<g opacity="0">{appear(1.25)}{svg.text(x0, 318, out1, size=fs)}</g>')
    svg.add(f'<g opacity="0">{appear(1.6, .05)}{svg.text(x0, 358, prompt, size=fs)}'
            f'<rect x="{x0 + plen:.1f}" y="{358 - fs + 3}" width="{cw:.1f}" height="{fs + 2}" fill="{RED}">'
            f'{blink()}</rect></g>')

    # radar: one blip per disclosure, lit when the sweep passes its bearing
    def pt(bearing, r):
        a = math.radians(bearing)
        return cx + r * math.sin(a), cy - r * math.cos(a)

    for i, r in enumerate((R, R * .75, R * .5, R * .25)):
        svg.add(f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="none" stroke="{RED}" '
                f'stroke-opacity="{.38 if i == 0 else .14}"/>')
    svg.add(f'<path d="M{cx - R} {cy}H{cx + R}M{cx} {cy - R}V{cy + R}" stroke="{RED}" '
            'stroke-opacity=".14" stroke-dasharray="2 5"/>')
    ticks = []
    for b in range(0, 360, 5):
        ln = 7 if b % 30 == 0 else 3.5
        (x1, y1), (x2, y2) = pt(b, R), pt(b, R - ln)
        ticks.append(f"M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}")
    svg.add(f'<path d="{"".join(ticks)}" stroke="{RED}" stroke-opacity=".45"/>')
    for b, label in ((0, "000"), (90, "090"), (180, "180"), (270, "270")):
        x, y = pt(b, R + 18)
        svg.put_text(x, y + 4, label, size=11, fill=MUTED, anchor="middle")

    period, trail, slices = 6, 64, 22
    wedges = []
    for i in range(slices):
        a2, a1 = -i * trail / slices, -(i + 1) * trail / slices
        (x1, y1), (x2, y2) = pt(a1, R), pt(a2, R)
        op = SWEEP_OP * (1 - i / slices) ** 1.7
        wedges.append(f'<path d="M{cx} {cy}L{x1:.2f} {y1:.2f}A{R} {R} 0 0 1 {x2:.2f} {y2:.2f}Z" '
                      f'fill="{RED}" fill-opacity="{op:.3f}"/>')
    svg.add(f'<g><animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" '
            f'to="360 {cx} {cy}" dur="{period}s" repeatCount="indefinite"/>{"".join(wedges)}'
            f'<path d="M{cx} {cy}V{cy - R}" stroke="{RED}" stroke-width="2" filter="url(#soft)"/></g>')

    for d in DISCLOSURES:
        bearing, r = d["radar"]
        x, y = pt(bearing, r)
        col = sev_color(d["sev"])
        hit = period * bearing / 360
        svg.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="none" stroke="{col}" opacity="0">'
                f'<animate attributeName="r" values="5.5;21;21" keyTimes="0;.3;1" begin="{hit:.2f}s" '
                f'dur="{period}s" repeatCount="indefinite"/>'
                f'<animate attributeName="opacity" values=".9;0;0" keyTimes="0;.3;1" begin="{hit:.2f}s" '
                f'dur="{period}s" repeatCount="indefinite"/></circle>')
        svg.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{col}" filter="url(#soft)" opacity=".4">'
                f'<animate attributeName="opacity" values="1;.4;.4" keyTimes="0;.55;1" begin="{hit:.2f}s" '
                f'dur="{period}s" repeatCount="indefinite"/></circle>')
        right = x + 13 + tw(f'{d["slug"]} {d["score"]}', 13) < cx + R - 6
        lx = x + 13 if right else x - 13
        svg.put_text(lx, y + 4.5, [(d["slug"], DIM, 400), (" " + d["score"], col, 800)], size=13,
                     anchor="start" if right else "end",
                     attrs=f'stroke="{BG}" stroke-width="4" stroke-linejoin="round" paint-order="stroke"')
    svg.add(f'<circle cx="{cx}" cy="{cy}" r="9" fill="none" stroke="{RED}" stroke-opacity=".5"/>'
            f'<circle cx="{cx}" cy="{cy}" r="3" fill="{RED}"/>')
    # scan log, appended line by line once the sweep has started
    log = [
        [("[*] ", FAINT, 700), ("sweep complete", MUTED, 400)],
        [("[+] ", GREEN, 700), ("found ", DIM, 400), ("4 CVE", RED_SOFT, 700)],
        [("[+] ", GREEN, 700), ("found ", DIM, 400), ("1 bounty", GOLD, 700)],
    ]
    for i, spans in enumerate(log):
        svg.add(f'<g opacity="0">{appear(1.2 + i * .45, .12)}{svg.text(1036, 382 + i * 17, spans, size=11.5)}</g>')
    svg.save("banner.svg")


# ---------------------------------------------------------------- section headers

SECTIONS = [
    ("whoami", "01", "WHOAMI", "cat about.yml"),
    ("hall-of-fame", "02", "HALL OF FAME", "tail -n 5 disclosures.log"),
    ("projects", "03", "PROJECTS", "ls ~/pinned"),
    ("arsenal", "04", "ARSENAL", "cat stack.json | jq"),
    ("links", "05", "LINKS", "cat links.txt"),
]


def build_sections():
    # The transparent strip on top is the gap between sections, so README needs no <br>.
    top, bar = 22, 64
    for slug, num, title, cmd in SECTIONS:
        W, H = 1200, top + bar
        svg = Svg(W, H, f"{num} / {title.lower()}")
        svg.add(f'<g transform="translate(0 {top})">')
        svg.add(card(0, 0, W, bar, rx=12))
        svg.add(f'<rect x="24" y="{bar - 2}" width="96" height="2" fill="{RED}"/>')
        svg.put_text(28, 41, num, size=22, weight=800, fill=RED)
        svg.put_text(66, 41, "/", size=22, fill=FAINT)
        svg.put_text(90, 40, title, size=19, weight=700, fill=TEXT, ls=3)
        svg.put_text(W - 28, 39, [("$ ", RED, 700), (cmd, MUTED, 400)], size=14, anchor="end")
        svg.add("</g>")
        svg.save(f"section-{slug}.svg")


# ---------------------------------------------------------------- about

def build_about():
    W, H = 1200, 312
    svg = Svg(W, H, "about.yml: Võ Phú Vinh, alias Fortress, freelance pentester and vulnerability "
                    "researcher, Information Security student at HCMUTE.")
    svg.add(card(0, 0, W, H, rx=16))
    svg.add(f'<path d="M1 44.5H{W - 1}" stroke="{BORDER}"/>')
    for i, c in enumerate((RED, GOLD, GREEN)):
        svg.add(f'<circle cx="{24 + i * 20}" cy="22" r="5.5" fill="{c}" fill-opacity=".85"/>')
    svg.add(f'<rect x="96" y="10" width="124" height="35" rx="8" fill="{PANEL2}"/>'
            f'<rect x="96" y="43" width="124" height="2" fill="{RED}"/>')
    svg.put_text(158, 32, "about.yml", size=13, fill=TEXT, anchor="middle")

    k, p, v, s, c, b = RED_SOFT, FAINT, TEXT, GOLD, MUTED, GREEN
    lines = [
        [("name", k), (":       ", p), ('"Võ Phú Vinh"', s)],
        [("alias", k), (":      ", p), ("Fortress", v)],
        [("role", k), (":       ", p), ("[", p), ("freelance pentester", v), (", ", p),
         ("vulnerability researcher", v), ("]", p)],
        [("education", k), (":  ", p), ("Information Security @ HCMUTE", v)],
        [("focus", k), (":      ", p), ("[", p), ("web", v), (", ", p), ("api", v), (", ", p),
         ("source-code audit", v), (", ", p), ("supply chain", v), (", ", p), ("llm/mcp", v), ("]", p)],
        [("disclosure", k), (": ", p), ("responsible", v), ("   # maintainer first", c)],
        [("available", k), (":  ", p), ("true", b), ("          # you scope it, I test it", c)],
    ]
    for i, spans in enumerate(lines):
        y = 88 + i * 30
        svg.put_text(46, y, str(i + 1), size=14, fill=FAINT, anchor="end")
        svg.put_text(72, y, [(t, col, 700 if col == k else 400) for t, col in spans], size=16)

    # how I work
    bx, by, bw, bh = 760, 64, 412, 224
    svg.add(card(bx, by, bw, bh, rx=12, fill=PANEL2))
    svg.put_text(bx + 24, by + 34, [("// ", RED, 700), ("HOW I WORK", MUTED, 700)], size=12, ls=2)
    steps = ["read the source, trace the data", "prove it with a minimal PoC",
             "report privately, help ship the fix", "publish once users are safe"]
    for i, st in enumerate(steps):
        y = by + 74 + i * 36
        svg.put_text(bx + 24, y, [(f"0{i + 1}", RED, 700), ("  " + st, DIM, 400)], size=14.5)
    svg.save("about.svg")


# ---------------------------------------------------------------- achievements

def build_achievements():
    W, H = 1200, 216
    svg = Svg(W, H, "Highlights: Finalist with a Consolation Prize at the Cybersecurity Student Contest "
                    "2026, Division A; first place at HCMUTE Capture the Flag 2026; a Mapbox bug bounty on HackerOne "
                    "(CWE-94); 4 CVEs (CWE-306, CWE-78).")
    cards = [
        dict(color=ORANGE, glyph="oct:shield-check-24",
             head=[("FINALIST", ORANGE, 800)], sub="Consolation Prize · CSC 2026",
             det=["Cybersecurity Student Contest", "2026 · Division A"]),
        dict(color=GOLD, glyph="oct:trophy-24",
             head=[("1ST", GOLD, 800), (" PLACE", TEXT, 800)], sub="Champion · UTECTF 2026",
             det=["HCMUTE Capture the Flag 2026"]),
        dict(color=GREEN, glyph="hackerone",
             head=[("1×", GREEN, 800), (" BOUNTY", TEXT, 800)], sub="Mapbox · HackerOne",
             det=["CWE-94 Code Injection"]),
        dict(color=RED, glyph="oct:bug-24",
             head=[("4×", RED, 800), (" CVE", TEXT, 800)], sub="Responsible disclosure",
             det=["CWE-306 Missing Authentication", "CWE-78 OS Command Injection"]),
    ]
    gap = 24
    cw = (W - gap * (len(cards) - 1)) / len(cards)
    clip = "".join(f'<rect x="{i * (cw + gap):.1f}" width="{cw:.1f}" height="{H}" rx="16"/>'
                   for i in range(len(cards)))
    svg.defs.append(f'<clipPath id="cards">{clip}</clipPath>'
                    '<linearGradient id="shine" x1="0" x2="1">'
                    f'<stop offset="0" stop-color="{SHINE}" stop-opacity="0"/>'
                    f'<stop offset=".5" stop-color="{SHINE}" stop-opacity="{SHINE_OP}"/>'
                    f'<stop offset="1" stop-color="{SHINE}" stop-opacity="0"/></linearGradient>')
    for i, c in enumerate(cards):
        x = i * (cw + gap)
        gid = svg.uid("g")
        svg.defs.append(f'<linearGradient id="{gid}" x1="0" x2="1">'
                        f'<stop offset="0" stop-color="{c["color"]}"/>'
                        f'<stop offset="1" stop-color="{c["color"]}" stop-opacity="0"/></linearGradient>')
        svg.add(card(x, 0, cw, H, rx=16))
        svg.add(f'<rect x="{x + 1:.1f}" y="1" width="{cw - 2:.1f}" height="3" fill="url(#{gid})" rx="1.5"/>')
        svg.add(f'<rect x="{x + 26:.1f}" y="26" width="44" height="44" rx="12" fill="{c["color"]}" '
                f'fill-opacity=".12" stroke="{c["color"]}" stroke-opacity=".3"/>')
        svg.add(icon(c["glyph"], x + 37, 37, 22, c["color"]))
        svg.put_text(x + 25, 122, c["head"], size=36, weight=800, ls=-.5)
        svg.put_text(x + 26, 150, c["sub"], size=13, weight=700, fill=TEXT)
        for j, line in enumerate(c["det"]):
            svg.put_text(x + 26, 176 + j * 19, line, size=12, fill=MUTED)
            assert tw(line, 12) < cw - 52, line
        assert tw(c["sub"], 13) < cw - 52 and len(c["det"]) <= 2, c["sub"]
    svg.add(f'<g clip-path="url(#cards)"><rect x="-320" y="0" width="260" height="{H}" fill="url(#shine)" '
            f'transform="skewX(-18)"><animate attributeName="x" from="-320" to="1560" begin=".5s" dur="1.9s" '
            f'fill="freeze"/></rect></g>')
    svg.save("achievements.svg")


# ---------------------------------------------------------------- disclosure rows

def build_disclosures():
    for d in DISCLOSURES:
        W, H = 1200, 72
        col = sev_color(d["sev"])
        svg = Svg(W, H, f'{d["id"]}, {d["pkg"]}, {d["cvss"]} {d["score"]} {d["sev"].title()}. {d["line"]}')
        svg.add(card(0, 0, W, H, rx=12))
        svg.add(f'<rect x="0" y="14" width="3" height="{H - 28}" rx="1.5" fill="{col}"/>')
        svg.add(f'<rect x="24.5" y="14.5" width="92" height="43" rx="10" fill="{col}" fill-opacity=".1" '
                f'stroke="{col}" stroke-opacity=".45"/>')
        svg.put_text(70.5, 37, d["score"], size=19, weight=800, fill=col, anchor="middle")
        svg.put_text(70.5 + .6, 51, d["sev"], size=9, weight=700, fill=col, anchor="middle", ls=1.2)
        svg.put_text(140, 32, d["id"], size=17, weight=700, fill=TEXT)
        svg.put_text(320, 32, d["pkg"], size=15, fill=RED_SOFT)
        svg.put_text(140, 55, d["line"], size=12.5, fill=MUTED)
        svg.put_text(W - 60, 31, d["date"], size=13, fill=DIM, anchor="end")
        svg.put_text(W - 60, 54, d["cvss"], size=11, fill=FAINT, anchor="end", ls=.8)
        svg.add(f'<path d="M{W - 40} 28h10v10M{W - 30} 28l-11 11" stroke="{MUTED}" stroke-width="1.6" '
                'fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
        svg.save(f'cve-{d["slug"]}.svg')


# ---------------------------------------------------------------- projects

def wrap(text, width):
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return lines + [cur] if cur else lines


def build_projects():
    # Three to a row: 392 px wide so they share the 1200 px scale of the full-width images.
    for p in PROJECTS:
        W, H = 392, 262
        svg = Svg(W, H, f'{p["title"]}: {p["desc"]}')
        svg.add(card(0, 0, W, H, rx=16))
        svg.add(f'<rect x="28" y="0" width="72" height="3" rx="1.5" fill="{RED}"/>')
        svg.add(icon("oct:repo-16", 28, 31, 15, MUTED))
        svg.put_text(51, 43, p["repo"], size=12, fill=MUTED)
        svg.add(f'<path d="M{W - 40} 30h10v10M{W - 30} 30l-11 11" stroke="{MUTED}" stroke-width="1.6" '
                'fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
        svg.put_text(28, 90, p["title"], size=26, weight=800, fill=TEXT, ls=-.3)
        lines = wrap(p["desc"], 40)
        assert len(lines) <= 3, p["slug"]
        for i, line in enumerate(lines):
            svg.put_text(28, 126 + i * 22, line, size=14, fill=DIM)

        # language bar, GitHub style
        bx, by, bw = 28, 202, W - 56
        cid = svg.uid("bar")
        svg.defs.append(f'<clipPath id="{cid}"><rect x="{bx}" y="{by}" width="{bw}" height="8" rx="4"/></clipPath>')
        segs, x = [], bx
        for name, color, pct in p["langs"]:
            w = bw * pct / 100
            segs.append(f'<rect x="{x:.1f}" y="{by}" width="{w:.1f}" height="8" fill="{readable(color, 1.8)}"/>')
            x += w
        segs.append(f'<rect x="{x:.1f}" y="{by}" width="{bx + bw - x:.1f}" height="8" fill="{FAINT}"/>')
        seps = "".join(f'<rect x="{bx + bw * sum(l[2] for l in p["langs"][:i + 1]) / 100 - 1:.1f}" y="{by}" '
                       f'width="2" height="8" fill="{PANEL}"/>' for i in range(len(p["langs"])))
        svg.add(f'<g clip-path="url(#{cid})">{"".join(segs)}{seps}</g>')
        lx = bx
        for name, color, pct in p["langs"]:
            svg.add(f'<circle cx="{lx + 4:.1f}" cy="{by + 30}" r="4" fill="{readable(color, 1.8)}"/>')
            svg.put_text(lx + 13, by + 34, name, size=12, weight=700, fill=TEXT)
            lx += 13 + tw(name, 12) + 18
        assert lx - 16 < bx + bw, p["slug"]
        svg.save(f'project-{p["slug"]}.svg')


# ---------------------------------------------------------------- stack

def lift(name):
    picked = (DARK_ICON if LIFT == "#ffffff" else LIGHT_ICON).get(name)
    return token(picked) if picked else readable(BRAND.get(name, "TEXT"))


def build_stack():
    W = 1200
    row_h, top = 58, 26
    H = top * 2 + row_h * len(STACK) - 18
    svg = Svg(W, H, "Stack: " + "; ".join(f'{cat.title()}: {", ".join(l for _, l in items)}'
                                          for cat, items in STACK))
    svg.add(card(0, 0, W, H, rx=16))
    for r, (cat, items) in enumerate(STACK):
        y = top + r * row_h
        if r:
            svg.add(f'<path d="M28 {y - 10.5}H{W - 28}" stroke="{BORDER}" stroke-dasharray="2 4"/>')
        svg.put_text(32, y + 24, cat, size=11.5, weight=700, fill=MUTED, ls=2.2)
        x = 196
        for key, label in items:
            has_icon = key is not None
            w = tw(label, 14) + (52 if has_icon else 28)
            svg.add(f'<rect x="{x + .5:.1f}" y="{y + .5}" width="{w - 1:.1f}" height="37" rx="10" '
                    f'fill="{PANEL2}" stroke="{BORDER}"/>')
            tx = x + 14
            if has_icon:
                svg.add(icon(key, x + 13, y + 9.5, 18, lift(key)))
                tx = x + 40
            svg.put_text(tx, y + 23.5, label, size=14, fill=TEXT)
            x += w + 10
        assert x < W, cat
    svg.save("stack.svg")


# ---------------------------------------------------------------- contact

def build_contacts():
    for c in CONTACTS:
        W, H = 390, 84
        svg = Svg(W, H, f'{c["label"]}: {c["handle"]}')
        col = token(c["color"])
        svg.add(card(0, 0, W, H, rx=14))
        svg.add(f'<rect x="18.5" y="18.5" width="47" height="47" rx="12" fill="{col}" '
                f'fill-opacity=".1" stroke="{col}" stroke-opacity=".28"/>')
        if c["icon"] == "tiktok":
            # the logo's cyan/red offset, drawn under the main mark
            svg.add(icon("tiktok", 30.2, 29.4, 24, "#25f4ee"))
            svg.add(icon("tiktok", 31.8, 30.6, 24, "#fe2c55"))
        svg.add(icon(c["icon"], 31, 30, 24, col))
        svg.put_text(84, 39, c["label"], size=17, weight=700, fill=TEXT)
        svg.put_text(84, 61, c["handle"], size=12.5, fill=MUTED)
        svg.add(f'<path d="M{W - 38} 37h9v9M{W - 29} 37l-10 10" stroke="{MUTED}" stroke-width="1.6" '
                'fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
        svg.save(f'contact-{c["slug"]}.svg')


# ---------------------------------------------------------------- footer

def build_footer():
    W, H = 1200, 96
    svg = Svg(W, H, "exit. Thanks for stopping by. Stay curious, disclose responsibly.")
    svg.add(card(0, 0, W, H, rx=14))
    prompt = [("root@fortress", RED, 700), (":", MUTED, 400), ("~", GOLD, 700), ("# ", MUTED, 400),
              ("exit", TEXT, 400)]
    svg.put_text(28, 40, prompt, size=15)
    msg = "logout · thanks for stopping by. stay curious, disclose responsibly."
    svg.put_text(28, 68, msg, size=15, fill=MUTED)
    svg.add(f'<rect x="{28 + tw(msg, 15) + 6:.1f}" y="55" width="9" height="17" fill="{RED}">{blink()}</rect>')
    svg.put_text(W - 28, 68, "© 2026 Võ Phú Vinh · Fortress", size=12, fill=FAINT, anchor="end")
    svg.save("footer.svg")


if __name__ == "__main__":
    for theme in THEMES:
        use_theme(theme)
        print(f"writing assets/{theme}:")
        build_banner()
        build_sections()
        build_about()
        build_achievements()
        build_disclosures()
        build_projects()
        build_stack()
        build_contacts()
        build_footer()
