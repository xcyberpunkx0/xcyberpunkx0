"""Builds the README's SVG panels in the portfolio's theme (dark + light variants)."""
import base64, io, math, os, re
from fontTools.ttLib import TTFont
from fontTools import subset
from PIL import Image

# Inputs: ASSET_CACHE holds fonts/ (Geist, Geist Mono, Caveat TTFs) and pk/ (unpacked simple-icons + feather-icons npm tarballs).
S = os.environ.get("ASSET_CACHE", ".cache")
P = os.environ.get("PORTFOLIO", "../Portfolio_v6")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
SI = [f"{S}/pk/si13/package/icons", f"{S}/pk/simple-icons-11.15.0/package/icons"]
FI = f"{S}/pk/feather-icons-4.29.2/package/dist/icons"
W = 1000

THEMES = {
    "dark": dict(heading="#fafafa", ink="#eeeeee", secondary="#c4c4c4", muted="#a0a0a0", dim="#7b7b7b",
                 faint="#5a5a5a", rule="#262626", strong="#363636", accent="#f26a50", card="#161616", bg="#0d1117"),
    "light": dict(heading="#171717", ink="#202020", secondary="#4f4f4f", muted="#6f6f6f", dim="#8d8d8d",
                  faint="#bbbbbb", rule="#e8e8e8", strong="#d4d4d4", accent="#b93a27", card="#f9f9f9", bg="#ffffff"),
}


def mix(a, b, t):
    a = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x * t + y * (1 - t)):02x}" for x, y in zip(a, b))


class Font:
    def __init__(self, file, family, weight):
        self.file, self.family, self.weight = f"{S}/fonts/{file}", family, weight
        tt = TTFont(self.file)
        self.cmap, self.hmtx, self.upm = tt.getBestCmap(), tt["hmtx"], tt["head"].unitsPerEm

    def width(self, s, size, ls=0):
        return sum(self.hmtx[self.cmap.get(ord(c), ".notdef")][0] for c in s) * size / self.upm + ls * size * len(s)


SANS = Font("Geist-400.ttf", "G4", 400)
MED = Font("Geist-500.ttf", "G5", 500)
SEMI = Font("Geist-600.ttf", "G6", 600)
MONO = Font("GeistMono-400.ttf", "M4", 400)
MONO5 = Font("GeistMono-500.ttf", "M5", 500)
SCRIPT = Font("Caveat-500.ttf", "C5", 500)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Doc:
    def __init__(self, h, t, label):
        self.h, self.t, self.label, self.els, self.defs, self.used = h, t, label, [], [], {}

    def add(self, s):
        self.els.append(s)

    def text(self, x, y, s, font, size, fill, anchor="start", ls=0, extra="", inner=""):
        self.used.setdefault(font, set()).update(s)
        lsa = f' letter-spacing="{ls * size:.2f}"' if ls else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font.family}" font-size="{size}" fill="{fill}" '
                 f'text-anchor="{anchor}"{lsa}{extra}>{inner}{esc(s)}</text>')

    def hline(self, y, x1=0, x2=W, color=None):
        self.add(f'<path d="M{x1} {y + .5}H{x2}" stroke="{color or self.t["rule"]}"/>')

    def vline(self, x, y1, y2, color=None, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<path d="M{x + .5} {y1}V{y2}" stroke="{color or self.t["rule"]}"{d}/>')

    def hatch(self, y, h):
        if '<pattern id="hatch"' not in "".join(self.defs):
            self.defs.append(f'<pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" '
                             f'patternTransform="rotate(45)"><rect width="1" height="7" fill="{self.t["rule"]}"/></pattern>')
        self.add(f'<rect x="0" y="{y}" width="{W}" height="{h}" fill="url(#hatch)"/>')
        self.hline(y)
        self.hline(y + h)

    def frame(self):
        self.vline(0, 0, self.h)
        self.vline(W - 1, 0, self.h)

    def save(self, name):
        faces = []
        for font, chars in self.used.items():
            opts = subset.Options()
            opts.flavor, opts.layout_features, opts.name_IDs, opts.notdef_outline = "woff2", ["kern"], [], True
            tt = TTFont(font.file)
            sub = subset.Subsetter(opts)
            sub.populate(text="".join(chars))
            sub.subset(tt)
            buf = io.BytesIO()
            tt.flavor = "woff2"
            tt.save(buf)
            b64 = base64.b64encode(buf.getvalue()).decode()
            faces.append(f"@font-face{{font-family:{font.family};src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
        style = "<style>" + "".join(faces) + "text{font-kerning:none;white-space:pre}</style>"
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
               f'viewBox="0 0 {W} {self.h}" width="{W}" height="{self.h}" role="img" aria-label="{esc(self.label)}" fill="none">'
               f'<title>{esc(self.label)}</title>{style}<defs>{"".join(self.defs)}</defs>{"".join(self.els)}</svg>')
        with open(f"{OUT}/{name}.svg", "w") as f:
            f.write(svg)


def feather(name, x, y, size, color):
    body = re.search(r"<svg[^>]*>(.*)</svg>", open(f"{FI}/{name}.svg").read(), re.S).group(1)
    s = size / 24
    return (f'<g transform="translate({x} {y}) scale({s})" stroke="{color}" stroke-width="{2}" '
            f'stroke-linecap="round" stroke-linejoin="round" fill="none">{body}</g>')


def simple_icon(name):
    for d in SI:
        p = f"{d}/{name}.svg"
        if os.path.exists(p):
            return re.search(r'<path d="([^"]+)"', open(p).read()).group(1)
    raise FileNotFoundError(name)


# ---------------------------------------------------------------- avatar
def avatar_b64():
    im = Image.open(f"{P}/public/images/profile_pic.jpg").convert("RGB")
    side = min(im.size)
    # object-[40%_42%] from the site
    x = round((im.width - side) * 0.40)
    y = round((im.height - side) * 0.42)
    im = im.crop((x, y, x + side, y + side)).resize((320, 320), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=84, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


AVATAR = avatar_b64()

# ---------------------------------------------------------------- iso AG blocks (port of IsoBlocks.tsx)
A = [".##.", "#..#", "####", "#..#"]
G = [".###", "#...", "#.##", ".###"]
ROWS = [A[i] + "." + G[i] for i in range(4)]
COLS = len(ROWS[0])
U, HB = 40, 20
C30 = math.cos(math.pi / 6)


def Pt(x, y, z=0):
    return f"{(x + y) * C30 * U:.2f},{(y - x) * .5 * U - z:.2f}"


def has(x, y):
    return 0 <= y < len(ROWS) and 0 <= x < COLS and ROWS[y][x] == "#"


BLOCKS = sorted([(x, y) for y, r in enumerate(ROWS) for x, c in enumerate(r) if c == "#"], key=lambda b: (b[1] - b[0], b[0]))
SHAPES = []


def add(kind, *pts):
    SHAPES.append((kind, " ".join(Pt(x, y, up * HB) for x, y, up in pts)))


for x, y in BLOCKS:
    front, left = not has(x, y + 1), not has(x - 1, y)
    if left: add("wall", (x, y, 0), (x, y + 1, 0), (x, y + 1, 1), (x, y, 1))
    if front: add("wall", (x, y + 1, 0), (x + 1, y + 1, 0), (x + 1, y + 1, 1), (x, y + 1, 1))
    add("top", (x, y, 1), (x + 1, y, 1), (x + 1, y + 1, 1), (x, y + 1, 1))
    if not has(x, y - 1): add("edge", (x, y, 1), (x + 1, y, 1))
    if not has(x + 1, y): add("edge", (x + 1, y, 1), (x + 1, y + 1, 1))
    if front:
        add("edge", (x, y + 1, 1), (x + 1, y + 1, 1))
        add("edge", (x, y + 1, 0), (x + 1, y + 1, 0))
        if not (has(x - 1, y) and not has(x - 1, y + 1)): add("edge", (x, y + 1, 0), (x, y + 1, 1))
        if not (has(x + 1, y) and not has(x + 1, y + 1)): add("edge", (x + 1, y + 1, 0), (x + 1, y + 1, 1))
    if left:
        add("edge", (x, y, 1), (x, y + 1, 1))
        add("edge", (x, y, 0), (x, y + 1, 0))
        if not (has(x, y - 1) and not has(x - 1, y - 1)): add("edge", (x, y, 0), (x, y, 1))
        if not front and not (has(x, y + 1) and not has(x - 1, y + 1)): add("edge", (x, y + 1, 0), (x, y + 1, 1))

GUIDES = [(Pt(-60, len(ROWS)), Pt(60, len(ROWS))), (Pt(0, -60), Pt(0, 60)), (Pt(COLS, -60), Pt(COLS, 60))]
IW = (COLS + len(ROWS)) * C30 * U
ITOP = -COLS * .5 * U - HB
IHT = len(ROWS) * .5 * U - ITOP


def iso(t, x, y, w, h):
    top = mix(t["ink"], t["bg"], .06)
    cx, cy = IW / 2, ITOP + IHT / 2
    out = [f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="-2 {ITOP - 2:.2f} {IW + 4:.2f} {IHT + 4:.2f}" overflow="visible">',
           f'<defs><radialGradient id="iso" gradientUnits="userSpaceOnUse" cx="{cx:.1f}" cy="{cy:.1f}" r="{IW * .4:.1f}">'
           f'<stop offset="0" stop-color="{t["ink"]}" stop-opacity=".9"/><stop offset=".5" stop-color="{t["ink"]}" stop-opacity=".4"/>'
           f'<stop offset="1" stop-color="{t["ink"]}" stop-opacity=".12"/></radialGradient></defs>']
    for a, b in GUIDES:
        out.append(f'<polyline points="{a} {b}" stroke="{t["strong"]}" stroke-dasharray="4 2" vector-effect="non-scaling-stroke"/>')
    for kind, pts in SHAPES:
        if kind == "edge":
            out.append(f'<polyline points="{pts}" stroke="url(#iso)" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>')
        else:
            out.append(f'<polygon points="{pts}" fill="{top if kind == "top" else t["bg"]}"/>')
    out.append("</svg>")
    return "".join(out)


VERIFIED = ("M24 12a4.454 4.454 0 0 0-2.564-3.91 4.437 4.437 0 0 0-.948-4.578 4.436 4.436 0 0 0-4.577-.948A4.44 4.44 0 0 0 12 0"
            "a4.423 4.423 0 0 0-3.9 2.564 4.434 4.434 0 0 0-2.43-.178 4.425 4.425 0 0 0-2.158 1.126 4.42 4.42 0 0 0-1.12 2.156 "
            "4.42 4.42 0 0 0 .183 2.421A4.456 4.456 0 0 0 0 12a4.465 4.465 0 0 0 2.576 3.91 4.433 4.433 0 0 0 .936 4.577 4.459 "
            "4.459 0 0 0 4.577.95A4.454 4.454 0 0 0 12 24a4.439 4.439 0 0 0 3.91-2.563 4.26 4.26 0 0 0 5.526-5.526A4.453 4.453 0 0 0 "
            "24 12Zm-13.709 4.917-4.38-4.378 1.652-1.663 2.646 2.646L15.83 7.4l1.72 1.591-7.258 7.926Z")

FLIP = ["Software Engineer · GenAI", "From the schema to the last hover state.",
        "Open to work. I can start right away.", "Based in Bangalore, India."]

INFO = [("code", "Software engineer, open to work"), ("briefcase", "Previously @TrueKhoj, Sep 2026"),
        ("map-pin", "Bangalore, India"), ("clock", "IST, UTC+05:30"),
        ("mail", "adityagup1a@gmail.com"), ("file-text", "Résumé (PDF)")]


def banner(name, t):
    d = Doc(369, t, "Aditya Gupta. Software Engineer, GenAI. Bangalore, India. Open to work.")
    d.hatch(0, 28)
    # profile band 28..248
    top, bot = 28, 248
    d.defs.append('<clipPath id="av"><circle cx="96" cy="152" r="80"/></clipPath>')
    d.add(f'<image x="16" y="72" width="160" height="160" clip-path="url(#av)" preserveAspectRatio="xMidYMid slice" '
          f'href="data:image/jpeg;base64,{AVATAR}" xlink:href="data:image/jpeg;base64,{AVATAR}"/>')
    d.add(f'<circle cx="96" cy="152" r="80" stroke="{t["rule"]}"/>')
    d.vline(192, top, bot)
    d.vline(550, top, bot)
    d.hline(204, 192, 550)
    nm = "Aditya Gupta"
    d.text(208, 188, nm, SEMI, 40, t["heading"], ls=-.03)
    bx = 208 + SEMI.width(nm, 40, -.03) + 8
    d.add(f'<g transform="translate({bx:.1f} 165) scale({22 / 24})"><path fill="{t["ink"]}" d="{VERIFIED}"/></g>')
    # flip sentences, cycled with SMIL
    n, step = len(FLIP), 3.2
    for i, s in enumerate(FLIP):
        k0, k1 = i / n, (i + 1) / n
        vals, keys = ("1;0", f"0;{k1:.4f}") if i == 0 else ("0;1;0", f"0;{k0:.4f};{k1:.4f}")
        d.text(208, 231, s, MONO, 14, t["secondary"], extra=f' opacity="{1 if i == 0 else 0}"',
               inner=f'<animate attributeName="opacity" values="{vals}" keyTimes="{keys}" dur="{n * step}s" '
                     f'repeatCount="indefinite" calcMode="discrete"/>')
    d.defs.append(f'<clipPath id="cell"><rect x="551" y="{top + 1}" width="448" height="{bot - top - 1}"/></clipPath>')
    d.add(f'<g clip-path="url(#cell)">{iso(t, 566, top + 14, 450 - 32, 220 - 36)}</g>')
    d.text(988, 242, "Fig. 1", SANS, 12, t["dim"], anchor="end")
    d.hatch(bot, 32)
    # info grid 280..368
    y0, rh, cw = 280, 44, W / 3
    for i, (icon, label) in enumerate(INFO):
        cx, cy = (i % 3) * cw, y0 + (i // 3) * rh
        d.add(f'<rect x="{cx + 20.5:.1f}" y="{cy + 8.5}" width="27" height="27" rx="6" fill="{t["card"]}" stroke="{t["rule"]}"/>')
        d.add(feather(icon, cx + 27.5, cy + 15.5, 13, t["muted"]))
        d.text(cx + 60, cy + 26.5, label, MONO, 13, t["ink"])
    d.hline(y0 + rh)
    d.vline(round(cw), y0, y0 + 2 * rh)
    d.vline(round(2 * cw), y0, y0 + 2 * rh)
    d.hline(y0 + 2 * rh)
    d.frame()
    d.save(name)


# ---------------------------------------------------------------- section titles
def title(name, t, text, count=None, note=None, script=False):
    d = Doc(93, t, text)
    d.hatch(0, 32)
    if script:
        d.text(24, 75, text, SCRIPT, 36, t["heading"])
    else:
        d.text(24, 73, text, SEMI, 30, t["heading"], ls=-.03)
        if count:
            d.text(24 + SEMI.width(text, 30, -.03) + 5, 58, f"({count})", SANS, 13, t["muted"])
    if note:
        nw = SCRIPT.width(note, 22)
        d.add(f'<g transform="rotate(-4 {976 - nw / 2:.0f} 66)">')
        d.text(976, 70, note, SCRIPT, 22, t["muted"], anchor="end")
        ax = 976 - nw - 46
        d.add(f'<path d="M{ax + 38:.0f} 62c-10 -6 -22 -6 -34 2" stroke="{t["dim"]}" stroke-width="1.3" stroke-linecap="round"/>'
              f'<path d="M{ax + 11:.0f} 59l-7 5 8 2" stroke="{t["dim"]}" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></g>')
    d.hline(92)
    d.frame()
    d.save(name)


# ---------------------------------------------------------------- stack rows (port of StackRows)
SKILLS = {
    "Languages": ["JavaScript (ES6+)", "TypeScript", "Python", "Dart", "Java", "C/C++", "SQL", "Bash", "HTML/CSS"],
    "Frontend": ["React", "Next.js (App Router)", "Tailwind CSS", "shadcn/ui", "Zustand", "Framer Motion", "Electron", "SSR/ISR"],
    "Mobile": ["Flutter/Dart", "React Native (familiar)", "Clean Architecture"],
    "Backend": ["Node.js", "Express.js", "FastAPI", "RESTful APIs", "GraphQL", "WebSockets", "Microservices"],
    "Databases": ["PostgreSQL", "Supabase", "pgvector", "MongoDB", "MySQL", "Redis", "Firebase"],
    "AI / LLM": ["LLM API Integration", "RAG Pipelines", "Vector Embeddings", "Prompt Engineering", "LangChain"],
    "Testing & DevOps": ["Playwright", "Vitest", "fast-check", "Lighthouse CI", "Docker", "GitHub Actions", "GCP", "AWS", "Vercel"],
    "Tools": ["Claude Code", "Codex", "Gemini", "Figma"],
}
ICONS = {"Next.js (App Router)": "nextdotjs", "shadcn/ui": "shadcnui", "Framer Motion": "framer", "Express.js": "express",
         "WebSockets": "socketdotio", "LLM API Integration": "openai", "LangChain": "langchain", "Lighthouse CI": "lighthouse",
         "Vercel": "vercel", "Codex": "openai"}
LOGOS = {"JavaScript (ES6+)": "javascript", "TypeScript": "typescript", "Python": "python", "Dart": "dart", "Java": "java",
         "C/C++": "cplusplus", "Bash": "bash", "HTML/CSS": "html5", "React": "react", "Tailwind CSS": "tailwindcss",
         "Electron": "electron", "Flutter/Dart": "flutter", "React Native (familiar)": "react", "Node.js": "nodejs",
         "FastAPI": "fastapi", "GraphQL": "graphql", "PostgreSQL": "postgresql", "Supabase": "supabase", "pgvector": "postgresql",
         "MongoDB": "mongodb", "MySQL": "mysql", "Redis": "redis", "Firebase": "firebase", "Playwright": "playwright",
         "Vitest": "vitest", "Docker": "docker", "GitHub Actions": "githubactions", "GCP": "googlecloud",
         "AWS": "amazonwebservices", "Claude Code": "claude", "Gemini": "gemini", "Figma": "figma"}


def logo_uri(key):
    raw = open(f"{P}/public/icons/stack/{key}.svg", "rb").read()
    return "data:image/svg+xml;base64," + base64.b64encode(raw).decode()


def stack(name, t):
    LEFT, X0, X1, CH, GAP = 192, 208, 984, 36, 6
    rows, y = [], 0
    for i, (group, items) in enumerate(SKILLS.items()):
        items = sorted(items, key=lambda it: -(it in LOGOS or it in ICONS))
        chips, x, line = [], X0, 0
        for it in items:
            logo = it in LOGOS or it in ICONS
            w = (7 + 20 + 8 + MED.width(it, 14) + 11) if logo else (10 + SANS.width(it, 14) + 10)
            if x + w > X1:
                x, line = X0, line + 1
            chips.append((it, logo, x, line, w))
            x += w + GAP
        h = 16 + (line + 1) * CH + line * GAP + 16
        rows.append((i, group, chips, y, h))
        y += h
    d = Doc(y + 1, t, "Stack: " + "; ".join(f"{g}: {', '.join(v)}" for g, v in SKILLS.items()))
    d.hline(0)
    seen = set()
    for i, group, chips, y0, h in rows:
        d.text(16, y0 + 16 + 18 + 5, f"{i + 1:02d}", MONO, 14, t["muted"], extra=' opacity=".8"')
        d.text(16 + MONO.width("00", 14) + 6, y0 + 16 + 18 + 5, group, SANS, 14, t["ink"])
        for it, logo, x, line, w in chips:
            cy = y0 + 16 + line * (CH + GAP)
            d.add(f'<rect x="{x + .5:.1f}" y="{cy + .5}" width="{w - 1:.1f}" height="{CH - 1}" rx="8" fill="{t["card"]}" stroke="{t["rule"]}"/>')
            if logo:
                if it in LOGOS:
                    key = LOGOS[it]
                    if key not in seen:
                        seen.add(key)
                        uri = logo_uri(key)
                        d.defs.append(f'<image id="l-{key}" width="20" height="20" href="{uri}" xlink:href="{uri}"/>')
                    d.add(f'<use href="#l-{key}" xlink:href="#l-{key}" x="{x + 7:.1f}" y="{cy + 8}"/>')
                else:
                    d.add(f'<g transform="translate({x + 9:.1f} {cy + 10}) scale({16 / 24})"><path fill="{t["ink"]}" d="{simple_icon(ICONS[it])}"/></g>')
                d.text(x + 35, cy + 23, it, MED, 14, t["ink"])
            else:
                d.text(x + 10, cy + 23, it, SANS, 14, t["muted"])
        d.hline(y0 + h)
    d.vline(LEFT, 0, d.h, color=t["rule"], dash="4 3")
    d.frame()
    d.save(name)


# ---------------------------------------------------------------- footer title block (port of Footer.tsx)
WG = {
    "a": [".....", ".....", ".####", "#...#", "#...#", "#...#", "#..##", ".##.#"],
    "d": ["....#", "....#", ".####", "#...#", "#...#", "#...#", "#...#", ".####"],
    "g": [".....", ".....", ".####", "#...#", "#...#", ".####", "....#", "####."],
    "i": [".#", "..", "##", ".#", ".#", ".#", ".#", ".#"],
    "p": [".....", ".....", "####.", "#...#", "#...#", "####.", "#....", "#...."],
    "t": [".#.", ".#.", "###", ".#.", ".#.", ".#.", ".#.", "..#"],
    "u": [".....", ".....", "#...#", "#...#", "#...#", "#...#", "#..##", ".##.#"],
    "y": [".....", ".....", "#...#", "#...#", "#...#", ".####", "....#", "####."],
}


def wordmark_paths(u):
    paths, col = [], 0
    for ch in "adityagupta":
        g = WG[ch]
        bars, open_ = [], []
        for y in range(9):
            row = g[y] if y < 8 else ""
            runs = [(m.start(), len(m.group())) for m in re.finditer("#+", row)]
            nxt = []
            for rx, rw in runs:
                bar = next((b for b in open_ if b[0] == rx and b[2] == rw), None)
                if bar:
                    bar[3] += 1
                else:
                    bar = [rx, y, rw, 1]
                    bars.append(bar)
                nxt.append(bar)
            open_ = nxt
        paths.append("".join(f"M{(col + x) * u + 1:.2f} {y * u + 1:.2f}h{w * u:.2f}v{h * u:.2f}h{-w * u:.2f}Z" for x, y, w, h in bars))
        col += len(g[0]) + 1
    return paths, col - 1


def footer(name, t):
    _, cols = wordmark_paths(1)
    u = (W - 32) / cols
    paths, _ = wordmark_paths(u)
    shown = 5 * u  # top five of eight rows sit above the cut, like the site
    y = 0
    d = Doc(0, t, "adityagupta.space. Crafted by Aditya Gupta in Bangalore, India. Open to work.")
    d.hatch(0, 48)
    y = 48
    d.text(16, y + 27, "adityagupta.space", MONO5, 14, t["heading"])
    d.text(984, y + 27, "A software engineer's profile, set in Geist.", SANS, 14, t["muted"], anchor="end")
    y += 44
    d.hline(y)
    cw = W / 4

    def field(col, row_y, label, value, span=1):
        x = col * cw
        d.text(x + 16, row_y + 24, label.upper(), MED, 10, t["muted"], ls=.05)
        if isinstance(value, str):
            d.text(x + 16, row_y + 46, value, MONO, 14, t["ink"])
        else:
            value(x, row_y)

    rh = 64
    for i, (l, v) in enumerate([("Crafted by", "Aditya Gupta"), ("Based in", "Bangalore, India"),
                                ("Status", "Open to work"), ("Typeface", "Geist")]):
        field(i, y, l, v)
    for i in (1, 2, 3):
        d.vline(round(cw * i), y, y + rh)
    y += rh
    d.hline(y)
    field(0, y, "Portfolio", "adityagupta.space")
    field(2, y, "Résumé", "AdityaGupta.pdf")
    d.vline(round(cw * 2), y, y + rh)
    y += rh
    d.hline(y)
    inspired = ["Vercel", "shadcn/ui", "Tailwind CSS", "GSAP", "Geist", "Linear"]
    d.text(16, y + 24, "INSPIRED BY", MED, 10, t["muted"], ls=.05)
    for i, s in enumerate(inspired):
        cx, cy = (i % 4) * cw + 16, y + 46 + (i // 4) * 20
        d.text(cx, cy, f"{i + 1:02d}", MONO, 14, t["muted"], extra=' opacity=".8"')
        d.text(cx + MONO.width("00", 14) + 8, cy, s, SANS, 14, t["ink"])
    y += 84
    d.hline(y)
    y += 16
    d.hline(y)
    # pixel AG mark
    for ry, row in enumerate(ROWS):
        for rx, c in enumerate(row):
            if c == "#":
                d.add(f'<rect x="{16 + rx * 4}" y="{y + 14 + ry * 4}" width="4" height="4" fill="{t["muted"]}"/>')
    y += 44
    d.hline(y)
    # wordmark sunk into the bottom edge
    wy = y + 20
    d.defs.append(f'<clipPath id="cut"><rect x="0" y="{y + 1}" width="{W}" height="{20 + shown:.1f}"/></clipPath>')
    d.add(f'<g clip-path="url(#cut)"><g transform="translate(16 {wy})">' +
          "".join(f'<path d="{p}" fill="{t["ink"]}" fill-opacity=".035" stroke="{t["ink"]}" stroke-opacity=".16" stroke-width="1.5"/>' for p in paths) +
          "</g></g>")
    y = wy + shown
    d.defs.append(f'<linearGradient id="glint" x1="0" x2="1"><stop offset="0" stop-color="{t["ink"]}" stop-opacity="0"/>'
                  f'<stop offset=".5" stop-color="{t["ink"]}" stop-opacity=".3"/><stop offset="1" stop-color="{t["ink"]}" stop-opacity="0"/></linearGradient>')
    d.add(f'<path d="M0 {y + .5}H{W}" stroke="{t["strong"]}"/><rect x="{W / 4}" y="{y}" width="{W / 2}" height="1" fill="url(#glint)"/>')
    d.h = y + 1
    d.frame()
    d.save(name)


# ---------------------------------------------------------------- project screenshots
SHOTS = {"stockvault": "stockvault/1.png", "instastash": "instastash/home.jpg",
         "aurastream": "aurastream/main.jpg", "clearfeed": "clearfeed/main.png"}


def shots():
    os.makedirs(f"{OUT}/projects", exist_ok=True)
    for slug, src in SHOTS.items():
        im = Image.open(f"{P}/public/images/{src}").convert("RGB")
        im = im.resize((1200, round(im.height * 1200 / im.width)), Image.LANCZOS)
        im.save(f"{OUT}/projects/{slug}.jpg", "JPEG", quality=80, optimize=True, progressive=True)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for mode, t in THEMES.items():
        banner(f"banner-{mode}", t)
        title(f"title-hello-{mode}", t, "Hi there", script=True)
        title(f"title-stack-{mode}", t, "Stack")
        title(f"title-experience-{mode}", t, "Experience")
        title(f"title-projects-{mode}", t, "Projects", count=5, note="all shipped")
        title(f"title-recognition-{mode}", t, "Recognition")
        title(f"title-education-{mode}", t, "Education")
        stack(f"stack-{mode}", t)
        footer(f"footer-{mode}", t)
    shots()
    print("done")
