#!/usr/bin/env python3
"""
Builds the black futuristic profile dashboard for github.com/aslamrekik.

Outputs (in ./profile):
  dashboard.svg      the whole profile as one animated SVG
  btn-*.svg          clickable buttons shown under it in README.md

Live data comes from the GitHub GraphQL API (env GH_TOKEN, needs read:user).
If the token is missing or a call fails, fallback values are used so the
build never breaks. Standard library only: no pip install needed.
"""
import base64, datetime as dt, json, math, os, textwrap, urllib.request
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "profile")
USER = os.environ.get("GH_USER", "aslamrekik")
TOKEN = os.environ.get("GH_TOKEN", "")

# ── palette ──────────────────────────────────────────────────────────────
BG, SURF, SURF2 = "#000000", "#0B0507", "#140709"
LINE, OXB, BURG = "#3A0C18", "#4A0E1F", "#800020"
WINE, CRIM, BLUSH = "#B3304C", "#E63E62", "#F2B8C6"
MUTED, DIM = "#C9A3AD", "#7A5560"
MONO = "'JetBrains Mono','Fira Code','Cascadia Code',Consolas,'DejaVu Sans Mono','Courier New',monospace"
W, PAD = 1000, 40
CW = W - 2 * PAD  # content width

# ── content ──────────────────────────────────────────────────────────────
PROFILE = [
    ("user", "Aslam Rekik"),
    ("role", "Software Engineer"),
    ("", "Software Architect"),
    ("", "Project Manager"),
    ("education", "Software Engineering @ Universidade Positivo → 2027"),
    ("base", "Curitiba, Brazil"),
    ("languages", "[ Portuguese, English, French ]  # all fluent"),
    ("work_mode", "backlog → user stories → 2-week sprints → MVP"),
    ("looking_for", "estágio / junior"),
    ("focus", "software dev · AI & automation · project management"),
]
PROJECTS = [
    dict(title="ONE LOVE RECORDS", tag="FREELANCE · LAUNCH NOV 2026", wide=True,
         desc="Website for a Dutch music label: events & tickets, DJ booking, artist roster, "
              "demo submissions and merch. Solo project run in Scrum: scope document, architecture "
              "document (DAS), 5 sprints with a client MVP review after each. English + Dutch.",
         stack="Next.js · React Three Fiber · GSAP · Tailwind · Sanity · Supabase · Vercel"),
    dict(title="LIGA APP", tag="TEAM LEAD · MVP OCT 2026",
         desc="MVP for Formigueiro Metais, a metals company: calculates and corrects the chemical composition of "
              "secondary aluminium alloys. In a 9-person team, I co-lead management, architecture, "
              "PR review, QA and deploy.",
         stack="React · TypeScript · FastAPI · PostgreSQL · Docker · Gemini"),
    dict(title="BARI · AI & DATA LAB", tag="CHALLENGE",
         desc="Credit-funnel diagnosis, an automated weekly report and structured AI extraction "
              "from property appraisal reports, with a log of how AI was used and where it failed.",
         stack="Python · pandas · Jupyter · Claude API · pytest"),
    dict(title="EVENT ANALYTICS", tag="DATA",
         desc="Event management with revenue tracking, performance metrics and visual reports.",
         stack="Python · pandas"),
    dict(title="TAREFAS API", tag="BACKEND",
         desc="Task management REST API with a Kanban web interface, filters and Swagger docs.",
         stack="ASP.NET Core · EF Core · SQLite · JavaScript"),
]
PRINCIPLES = [
    ("SCRUM IN PRACTICE", "backlog → user stories → 2-week sprints → a client MVP every sprint"),
    ("SELF-DEFENDING ARCHITECTURE", "layered APIs with tests that fail when a layer rule breaks"),
    ("AI WITH GUARDRAILS", "AI explains results but never calculates them; every number is validated"),
    ("CLEAN WORKFLOW", "feature branches, PR templates, conventional commits, CI on real cases"),
]
BUTTONS = [  # (file, label) — links live in README.md
    ("btn-linkedin", "LINKEDIN ↗"), ("btn-email", "EMAIL ↗"), ("btn-cv", "CV ↓"),
    ("btn-liga", "LIGA APP ↗"), ("btn-bari", "BARI ↗"), ("btn-events", "EVENTS ↗"), ("btn-tarefas", "TAREFAS API ↗"),
]
LANG_HIDE = {"HTML", "CSS", "Jupyter Notebook", "Dockerfile", "Batchfile", "Shell", "PowerShell"}

FALLBACK = dict(total=90, cur=4, longest=4, commits=90, prs=2, repos=7, stars=0,
                langs=[("Python", 47.5), ("JavaScript", 32.2), ("Java", 16.0), ("C#", 3.8), ("TypeScript", 0.3)],
                days=[])


# ── data ─────────────────────────────────────────────────────────────────
def gql(query, variables=None):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "profile-builder"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if body.get("errors"):
        raise RuntimeError(body["errors"])
    return body["data"]


def fetch():
    d = dict(FALLBACK)
    if not TOKEN:
        print("no token: using fallback data")
        return d
    try:
        u = gql("""query($l:String!){user(login:$l){createdAt
          pullRequests{totalCount}
          repositories(ownerAffiliations:OWNER,isFork:false,first:100,privacy:PUBLIC){totalCount
            nodes{stargazerCount languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}}}""",
                {"l": USER})["user"]
        d["prs"] = u["pullRequests"]["totalCount"]
        d["repos"] = u["repositories"]["totalCount"]
        d["stars"] = sum(n["stargazerCount"] for n in u["repositories"]["nodes"])
        sizes = {}
        for n in u["repositories"]["nodes"]:
            for e in n["languages"]["edges"]:
                if e["node"]["name"] not in LANG_HIDE:
                    sizes[e["node"]["name"]] = sizes.get(e["node"]["name"], 0) + e["size"]
        tot = sum(sizes.values()) or 1
        d["langs"] = [(k, 100 * v / tot) for k, v in sorted(sizes.items(), key=lambda x: -x[1])][:5]

        # contributions, year by year since account creation
        start = int(u["createdAt"][:4])
        now = dt.datetime.utcnow()
        days, commits_year = {}, 0
        for y in range(start, now.year + 1):
            c = gql("""query($l:String!,$f:DateTime!,$t:DateTime!){user(login:$l){
              contributionsCollection(from:$f,to:$t){totalCommitContributions restrictedContributionsCount
                contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}""",
                    {"l": USER, "f": f"{y}-01-01T00:00:00Z",
                     "t": (now if y == now.year else dt.datetime(y, 12, 31, 23, 59, 59)).strftime("%Y-%m-%dT%H:%M:%SZ")}
                    )["user"]["contributionsCollection"]
            if y == now.year:
                commits_year = c["totalCommitContributions"] + c["restrictedContributionsCount"]
            for w in c["contributionCalendar"]["weeks"]:
                for day in w["contributionDays"]:
                    days[day["date"]] = day["contributionCount"]
        seq = sorted(days.items())
        d["days"] = seq
        d["total"] = sum(v for _, v in seq)
        d["commits"] = commits_year
        # streaks
        longest = run = 0
        for _, v in seq:
            run = run + 1 if v > 0 else 0
            longest = max(longest, run)
        cur, i = 0, len(seq) - 1
        if i >= 0 and seq[i][1] == 0:
            i -= 1  # today not counted yet
        while i >= 0 and seq[i][1] > 0:
            cur += 1
            i -= 1
        d["cur"], d["longest"] = cur, longest
        print("live data ok:", {k: d[k] for k in ("total", "cur", "longest", "commits", "prs", "repos")})
    except Exception as e:  # never break the build
        print("API error, using fallback where needed:", e)
    return d


# ── svg helpers ──────────────────────────────────────────────────────────
def t(x, y, s, size=12, fill=BLUSH, weight=400, anchor="start", ls=0, extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{MONO}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" text-anchor="{anchor}" letter-spacing="{ls}" {extra}>{escape(s)}</text>')


def chamfer(x, y, w, h, c=12, fill=SURF, stroke=LINE, sw=1, extra=""):
    p = f"M{x+c},{y} H{x+w} V{y+h-c} L{x+w-c},{y+h} H{x} V{y+c} Z"
    return f'<path d="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'


def section(y, num, name):
    label = f"◢ {num} // {name}"
    lw = len(label) * 10.2 + 18
    return (t(PAD, y, label, 14, CRIM, 700, ls=1.5) +
            f'<rect x="{PAD+lw:.0f}" y="{y-5}" width="{CW-lw:.0f}" height="1" fill="url(#fadeLine)"/>')


def wrap(s, chars):
    return textwrap.wrap(s, chars)


# ── 3D wireframe (pre-rendered as animated vector paths) ────────────────
def icosa():
    p = (1 + 5 ** 0.5) / 2
    v = [(-1, p, 0), (1, p, 0), (-1, -p, 0), (1, -p, 0), (0, -1, p), (0, 1, p),
         (0, -1, -p), (0, 1, -p), (p, 0, -1), (p, 0, 1), (-p, 0, -1), (-p, 0, 1)]
    e = [(i, j) for i in range(12) for j in range(i + 1, 12)
         if abs(math.dist(v[i], v[j]) - 2) < 1e-6]
    return v, e


def wire_frames(cx, cy, r, frames, spin=1, tilt=0.45, phase=0.0):
    v, e = icosa()
    n = math.sqrt(1 + ((1 + 5 ** 0.5) / 2) ** 2)
    paths, pts = [], []
    for f in range(frames):
        a = spin * 2 * math.pi * f / frames + phase
        b = tilt + 0.18 * math.sin(2 * math.pi * f / frames)
        proj = []
        for x, y, z in v:
            x, y, z = x / n, y / n, z / n
            x, z = x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
            y, z = y * math.cos(b) - z * math.sin(b), y * math.sin(b) + z * math.cos(b)
            k = 3.2 / (3.2 + z)
            proj.append((cx + x * r * k, cy + y * r * k))
        paths.append(" ".join(f"M{proj[i][0]:.1f} {proj[i][1]:.1f}L{proj[j][0]:.1f} {proj[j][1]:.1f}" for i, j in e))
        pts.append(proj)
    return paths, pts


def wireframe(cx, cy, r, dur=16):
    out = []
    for rr, spin, col, op, sw in ((r, 1, CRIM, 0.95, 1.4), (r * 0.46, -1, WINE, 0.8, 1)):
        paths, pts = wire_frames(cx, cy, rr, 60, spin)
        vals = ";".join(paths + [paths[0]])
        out.append(f'<path fill="none" stroke="{col}" stroke-width="{sw}" opacity="{op}" filter="url(#glow)">'
                   f'<animate attributeName="d" dur="{dur}s" repeatCount="indefinite" values="{vals}"/></path>')
        if rr == r:
            for k in range(12):
                xs = ";".join(f"{p[k][0]:.1f}" for p in pts + [pts[0]])
                ys = ";".join(f"{p[k][1]:.1f}" for p in pts + [pts[0]])
                out.append(f'<circle r="2.6" fill="{BLUSH}"><animate attributeName="cx" dur="{dur}s" repeatCount="indefinite" values="{xs}"/>'
                           f'<animate attributeName="cy" dur="{dur}s" repeatCount="indefinite" values="{ys}"/></circle>')
    # orbit rings
    out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{r*1.35:.0f}" ry="{r*0.32:.0f}" fill="none" stroke="{OXB}" stroke-width="1" stroke-dasharray="3 7">'
               f'<animateTransform attributeName="transform" type="rotate" from="-12 {cx} {cy}" to="348 {cx} {cy}" dur="40s" repeatCount="indefinite"/></ellipse>')
    return "".join(out)


# ── sections ─────────────────────────────────────────────────────────────
def header():
    H, hz = 330, 238
    o = [f'<rect width="{W}" height="{H}" fill="url(#hdrGlow)"/>']
    # grid floor: vanishing lines + moving horizontal lines
    o.append(f'<g stroke="{OXB}" stroke-width="1" opacity="0.8">')
    for x in range(-1400, 2500, 120):
        o.append(f'<line x1="{W/2}" y1="{hz}" x2="{x}" y2="{H}"/>')
    for k in range(7):
        ys = ";".join(f"{hz + (H - hz) * (s / 11) ** 2:.1f}" for s in range(12))
        o.append(f'<line x1="0" x2="{W}" y1="{hz}" y2="{hz}"><animate attributeName="y1" values="{ys}" dur="3.5s" begin="{-k*0.5:.1f}s" repeatCount="indefinite"/>'
                 f'<animate attributeName="y2" values="{ys}" dur="3.5s" begin="{-k*0.5:.1f}s" repeatCount="indefinite"/></line>')
    o.append('</g>')
    o.append(f'<rect y="{hz-2}" width="{W}" height="{H-hz+2}" fill="url(#floorFade)"/>')
    o.append(f'<rect y="{hz}" width="{W}" height="1.2" fill="url(#fadeLineC)"/>')
    # HUD corners + tags
    o.append(f'<path d="M20 40 V20 H40 M{W-40} 20 H{W-20} V40" stroke="{WINE}" stroke-width="1.5" fill="none"/>')
    o.append(t(52, 34, "[ SYS://ASLAM.DEV ]  BUILD 2026", 11, DIM, ls=1))
    o.append(f'<circle cx="{W-118}" cy="30" r="4" fill="{CRIM}"><animate attributeName="opacity" values="1;.2;1" dur="1.6s" repeatCount="indefinite"/></circle>')
    o.append(t(W - 108, 34, "ONLINE", 11, CRIM, 700, ls=2))
    # name with glow
    o.append(t(PAD + 8, 122, "ASLAM REKIK", 58, CRIM, 800, ls=9, extra='filter="url(#glowBig)" opacity=".75"'))
    o.append(t(PAD + 8, 122, "ASLAM REKIK", 58, BLUSH, 800, ls=9))
    o.append(t(PAD + 10, 158, "SOFTWARE ENGINEER // SOFTWARE ARCHITECT // PROJECT MANAGER", 14, CRIM, 600, ls=2.2))
    # typing line
    line = "> status: open to estágio / junior roles in Curitiba"
    tw = len(line) * 9.05
    o.append(f'<clipPath id="typeClip"><rect x="{PAD+8}" y="178" height="30" width="0">'
             f'<animate attributeName="width" values="0;{tw:.0f};{tw:.0f};0" keyTimes="0;.45;.9;1" dur="7s" repeatCount="indefinite"/></rect></clipPath>')
    o.append(f'<g clip-path="url(#typeClip)">{t(PAD + 10, 198, line, 15, MUTED)}</g>')
    o.append(f'<rect y="185" width="9" height="17" fill="{CRIM}"><animate attributeName="x" values="{PAD+10};{PAD+12+tw:.0f};{PAD+12+tw:.0f};{PAD+10}" keyTimes="0;.45;.9;1" dur="7s" repeatCount="indefinite"/>'
             f'<animate attributeName="opacity" values="1;0;1" dur=".9s" repeatCount="indefinite"/></rect>')
    o.append(wireframe(850, 132, 96))
    return "".join(o), H


def profile(y0, avatar_b64):
    o = [section(y0 + 20, "01", "SYSTEM.PROFILE")]
    cx, cy, r = PAD + 130, y0 + 170, 104
    o.append(f'<clipPath id="avClip"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>')
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{r+22}" fill="url(#avGlow)"/>')
    o.append(f'<image href="data:image/jpeg;base64,{avatar_b64}" x="{cx-r}" y="{cy-r}" width="{2*r}" height="{2*r}" clip-path="url(#avClip)"/>')
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{r+3}" fill="none" stroke="url(#ringGrad)" stroke-width="5"/>')
    for rr, dash, dur, rev, col in ((r + 16, "18 10", 24, False, CRIM), (r + 27, "4 14", 36, True, WINE), (r + 36, "60 200", 12, False, BLUSH)):
        a, b = (360, 0) if rev else (0, 360)
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="none" stroke="{col}" stroke-width="1.6" stroke-dasharray="{dash}" opacity=".85">'
                 f'<animateTransform attributeName="transform" type="rotate" from="{a} {cx} {cy}" to="{b} {cx} {cy}" dur="{dur}s" repeatCount="indefinite"/></circle>')
    # terminal window
    x, y, w, h = 330, y0 + 48, W - PAD - 330, 262
    o.append(chamfer(x, y, w, h, 14, SURF, LINE))
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="30" fill="{SURF2}"/>')
    for i, c in enumerate((CRIM, WINE, BURG)):
        o.append(f'<circle cx="{x+20+i*16}" cy="{y+15}" r="4.5" fill="{c}"/>')
    o.append(t(x + w / 2, y + 19, "~/aslam/profile.yaml", 11, DIM, anchor="middle"))
    for i, (k, v) in enumerate(PROFILE):
        yy = y + 58 + i * 20.5
        if k:
            o.append(t(x + 22, yy, f"{k}", 13, CRIM, 600))
            o.append(t(x + 150, yy, ":", 13, DIM))
        o.append(t(x + 166, yy, v, 13, BLUSH))
    return "".join(o), 330


def projects(y0):
    o = [section(y0 + 20, "02", "FEATURED.BUILDS")]
    y, gap, h = y0 + 44, 16, 150
    cells, col = [], 0
    for p in PROJECTS:
        if p.get("wide"):
            cells.append((PAD, y, CW, p)); y += h + gap; col = 0
        else:
            cw = (CW - gap) / 2
            cells.append((PAD + col * (cw + gap), y, cw, p))
            col += 1
            if col == 2:
                col, y = 0, y + h + gap
    if col:
        y += h + gap
    for i, (x, yy, w, p) in enumerate(cells):
        o.append(f'<g class="fade" style="animation-delay:{0.15*i:.2f}s">')
        o.append(chamfer(x, yy, w, h, 16, SURF, LINE))
        o.append(f'<rect x="{x}" y="{yy+16}" width="3" height="{h-32}" fill="url(#vGrad)"/>')
        o.append(t(x + 22, yy + 32, p["title"], 15, BLUSH, 700, ls=1))
        tag = p["tag"]; tw = len(tag) * 6.6 + 18
        o.append(f'<rect x="{x+w-tw-16:.1f}" y="{yy+17}" width="{tw:.1f}" height="21" rx="3" fill="none" stroke="{WINE}"/>')
        o.append(t(x + w - tw / 2 - 16, yy + 31.5, tag, 10, CRIM, 700, "middle", 0.6))
        chars = int((w - 44) / 7.25)
        for j, ln in enumerate(wrap(p["desc"], chars)[:4]):
            o.append(t(x + 22, yy + 58 + j * 17, ln, 12, MUTED))
        o.append(t(x + 22, yy + h - 16, "▸ " + p["stack"], 11, WINE, 600))
        o.append('</g>')
    return "".join(o), y - y0 + 6


def principles(y0):
    o = [section(y0 + 20, "03", "OPERATING.PRINCIPLES")]
    gap, h = 14, 150
    w = (CW - 3 * gap) / 4
    for i, (title, desc) in enumerate(PRINCIPLES):
        x, y = PAD + i * (w + gap), y0 + 44
        o.append(chamfer(x, y, w, h, 14, SURF, LINE))
        o.append(t(x + 18, y + 38, f"[0{i+1}]", 22, CRIM, 800, extra='filter="url(#glow)"'))
        for j, ln in enumerate(wrap(title, 22)):
            o.append(t(x + 18, y + 64 + j * 16, ln, 12, BLUSH, 700, ls=0.5))
        ty = y + 64 + len(wrap(title, 22)) * 16 + 6
        for j, ln in enumerate(wrap(desc, 30)[:4]):
            o.append(t(x + 18, ty + j * 15, ln, 11, MUTED))
    return "".join(o), h + 64


def stack(y0, icons):
    o = [section(y0 + 20, "04", "TECH.STACK")]
    per, gap = 11, 10
    s = (CW - (per - 1) * gap) / per
    for i, ic in enumerate(icons):
        r, c = divmod(i, per)
        x, y = PAD + c * (s + gap), y0 + 44 + r * (s + gap)
        o.append(f'<g class="fade" style="animation-delay:{0.05*i:.2f}s">')
        o.append(chamfer(x, y, s, s, 9, SURF, LINE))
        sc = 26 / 24
        o.append(f'<path d="{ic["path"]}" fill="{BLUSH}" transform="translate({x+s/2-13:.1f},{y+14:.1f}) scale({sc:.3f})"/>')
        o.append(t(x + s / 2, y + s - 12, ic["label"], 9, MUTED, anchor="middle"))
        o.append('</g>')
    rows = math.ceil(len(icons) / per)
    return "".join(o), 44 + rows * (s + gap) + 16


def telemetry(y0, d):
    o = [section(y0 + 20, "05", "TELEMETRY")]
    y = y0 + 44
    # stat tiles 3x2
    tiles = [("TOTAL CONTRIBUTIONS", d["total"]), ("CURRENT STREAK", f'{d["cur"]} d'), ("LONGEST STREAK", f'{d["longest"]} d'),
             ("COMMITS THIS YEAR", d["commits"]), ("PULL REQUESTS", d["prs"]), ("PUBLIC REPOS", d["repos"])]
    lw, gap, th = 568, 12, 80
    tw = (lw - 2 * gap) / 3
    for i, (lab, val) in enumerate(tiles):
        r, c = divmod(i, 3)
        x, yy = PAD + c * (tw + gap), y + r * (th + gap)
        o.append(chamfer(x, yy, tw, th, 12, SURF, LINE))
        o.append(t(x + 18, yy + 42, str(val), 28, CRIM if i in (1, 2) else BLUSH, 800,
                   extra='filter="url(#glow)"' if i == 1 else ""))
        o.append(t(x + 18, yy + 64, lab, 10, DIM, 600, ls=1))
    # languages
    lx, lwid, lh = PAD + lw + 16, CW - lw - 16, 2 * th + gap
    o.append(chamfer(lx, y, lwid, lh, 12, SURF, LINE))
    o.append(t(lx + 18, y + 26, "// LANGUAGES", 11, CRIM, 700, ls=1))
    shades = [CRIM, WINE, BURG, "#5E1026", OXB]
    langs = d["langs"][:5]
    tot = sum(p for _, p in langs) or 1
    bx, bw = lx + 18, lwid - 36
    o.append(f'<rect x="{bx}" y="{y+38}" width="{bw}" height="8" rx="4" fill="{SURF2}"/>')
    cx = bx
    for i, (name, pct) in enumerate(langs):
        sw = bw * pct / tot
        o.append(f'<rect x="{cx:.1f}" y="{y+38}" width="{max(sw,1.5):.1f}" height="8" fill="{shades[i]}">'
                 f'<animate attributeName="width" from="0" to="{max(sw,1.5):.1f}" dur="1.4s" fill="freeze"/></rect>')
        cx += sw
        ly = y + 72 + i * 20
        o.append(f'<rect x="{bx}" y="{ly-9}" width="10" height="10" fill="{shades[i]}"/>')
        o.append(t(bx + 18, ly, name, 12, BLUSH))
        o.append(t(bx + bw, ly, f"{pct:.1f}%", 12, MUTED, anchor="end"))
    y += lh + 20
    # heatmap (last 52 weeks)
    o.append(chamfer(PAD, y, CW, 200, 14, SURF, LINE))
    o.append(t(PAD + 18, y + 26, "// CONTRIBUTIONS · LAST 12 MONTHS", 11, CRIM, 700, ls=1))
    today = dt.date.today()
    days = dict(d["days"])
    start = today - dt.timedelta(days=7 * 51 + (today.weekday() + 1) % 7)
    vals = [days.get((start + dt.timedelta(i)).isoformat(), 0) for i in range((today - start).days + 1)]
    mx = max(vals) if vals and max(vals) else 1
    lv = [SURF2, OXB, BURG, WINE, CRIM]
    cs, cg = 13, 3.6
    gx0 = PAD + (CW - 52 * (cs + cg)) / 2
    for i, v in enumerate(vals):
        wk, wd = divmod(i, 7)
        lvl = 0 if v == 0 else min(4, 1 + int(3 * v / mx))
        o.append(f'<rect x="{gx0 + wk*(cs+cg):.1f}" y="{y+42+wd*(cs+cg):.1f}" width="{cs}" height="{cs}" rx="2.5" fill="{lv[lvl]}"/>')
    # scanning beam
    o.append(f'<rect y="{y+38}" width="46" height="{7*(cs+cg)+4:.0f}" fill="url(#beam)"><animate attributeName="x" values="{gx0-60:.0f};{gx0+52*(cs+cg)+10:.0f}" dur="5s" repeatCount="indefinite"/></rect>')
    o.append(t(PAD + CW - 150, y + 186, "less", 10, DIM, anchor="end"))
    for i, c in enumerate(lv):
        o.append(f'<rect x="{PAD + CW - 142 + i*16}" y="{y+176}" width="11" height="11" rx="2" fill="{c}"/>')
    o.append(t(PAD + CW - 18, y + 186, "more", 10, DIM, anchor="end"))
    y += 200
    return "".join(o), y - y0 + 10


def footer(y0):
    o = [f'<rect x="{PAD}" y="{y0+10}" width="{CW}" height="1" fill="url(#fadeLineC)"/>',
         t(W / 2, y0 + 42, "> END_OF_TRANSMISSION", 13, CRIM, 700, "middle", 3),
         t(W / 2, y0 + 62, f"last sync {dt.date.today().isoformat()} · auto-generated by GitHub Actions", 10, DIM, anchor="middle")]
    return "".join(o), 84


DEFS = f"""
<defs>
  <filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="glowBig" x="-10%" y="-60%" width="120%" height="220%"><feGaussianBlur stdDeviation="9"/></filter>
  <radialGradient id="hdrGlow" cx="72%" cy="38%" r="70%"><stop offset="0" stop-color="#2A0A12"/><stop offset=".55" stop-color="#0B0507"/><stop offset="1" stop-color="{BG}"/></radialGradient>
  <radialGradient id="avGlow"><stop offset=".78" stop-color="{CRIM}" stop-opacity=".45"/><stop offset="1" stop-color="{CRIM}" stop-opacity="0"/></radialGradient>
  <linearGradient id="floorFade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG}" stop-opacity=".95"/><stop offset=".6" stop-color="{BG}" stop-opacity=".2"/><stop offset="1" stop-color="{BG}" stop-opacity="0"/></linearGradient>
  <linearGradient id="fadeLine"><stop offset="0" stop-color="{CRIM}"/><stop offset="1" stop-color="{CRIM}" stop-opacity="0"/></linearGradient>
  <linearGradient id="fadeLineC"><stop offset="0" stop-color="{CRIM}" stop-opacity="0"/><stop offset=".5" stop-color="{CRIM}"/><stop offset="1" stop-color="{CRIM}" stop-opacity="0"/></linearGradient>
  <linearGradient id="vGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CRIM}"/><stop offset="1" stop-color="{BURG}"/></linearGradient>
  <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{CRIM}"/><stop offset=".5" stop-color="{BURG}"/><stop offset="1" stop-color="{WINE}"/></linearGradient>
  <linearGradient id="beam"><stop offset="0" stop-color="{CRIM}" stop-opacity="0"/><stop offset=".8" stop-color="{CRIM}" stop-opacity=".35"/><stop offset="1" stop-color="{BLUSH}" stop-opacity=".7"/></linearGradient>
  <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#fff" opacity=".025"/></pattern>
  <linearGradient id="sweep" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CRIM}" stop-opacity="0"/><stop offset="1" stop-color="{CRIM}" stop-opacity=".06"/></linearGradient>
</defs>
<style>
  .fade {{ opacity:0; animation: fadeIn .8s ease-out forwards; }}
  @keyframes fadeIn {{ from {{ opacity:0; transform: translateY(6px); }} to {{ opacity:1; transform: none; }} }}
</style>"""


def dashboard(d):
    with open(os.path.join(OUT, "avatar-src.jpg"), "rb") as f:
        av = base64.b64encode(f.read()).decode()
    with open(os.path.join(ROOT, "scripts", "icons.json")) as f:
        icons = json.load(f)
    parts, y = [], 0
    s, h = header(); parts.append(s); y += h
    for fn in (lambda y: profile(y, av), projects, principles, lambda y: stack(y, icons), lambda y: telemetry(y, d), footer):
        s, h = fn(y); parts.append(s); y += h
    H = int(y)
    frame = (f'<rect x="8" y="8" width="{W-16}" height="{H-16}" fill="none" stroke="{OXB}" stroke-width="1"/>'
             f'<path d="M8 60 V8 H60 M{W-60} 8 H{W-8} V60 M{W-8} {H-60} V{H-8} H{W-60} M60 {H-8} H8 V{H-60}" stroke="{CRIM}" stroke-width="2" fill="none"/>')
    overlay = (f'<rect width="{W}" height="{H}" fill="url(#scan)" pointer-events="none"/>'
               f'<rect width="{W}" height="140" fill="url(#sweep)"><animate attributeName="y" values="-140;{H}" dur="9s" repeatCount="indefinite"/></rect>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<title>Aslam Rekik · Software Engineer · Software Architect · Project Manager</title>'
            f'{DEFS}<rect width="{W}" height="{H}" fill="{BG}"/>{"".join(parts)}{frame}{overlay}</svg>')


def button(label):
    w, h = int(len(label) * 9.2 + 44), 44
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{CRIM}"/><stop offset="1" stop-color="{BURG}"/></linearGradient></defs>'
            f'<path d="M10 1 H{w-1} V{h-11} L{w-11} {h-1} H1 V11 Z" fill="{BG}" stroke="url(#g)" stroke-width="1.6"/>'
            f'<rect x="1" y="14" width="3" height="{h-28}" fill="{CRIM}"/>'
            f'{t(w/2, h/2 + 5, label, 13, BLUSH, 700, "middle", 1.5)}</svg>')


def main():
    os.makedirs(OUT, exist_ok=True)
    d = fetch()
    with open(os.path.join(OUT, "dashboard.svg"), "w", encoding="utf-8") as f:
        f.write(dashboard(d))
    for name, label in BUTTONS:
        with open(os.path.join(OUT, f"{name}.svg"), "w", encoding="utf-8") as f:
            f.write(button(label))
    print("built", os.path.getsize(os.path.join(OUT, "dashboard.svg")) // 1024, "KB")


if __name__ == "__main__":
    main()
