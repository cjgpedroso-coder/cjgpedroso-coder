#!/usr/bin/env python3
"""
🚀 GitHub Spaceship v4 — Grand Finale Edition (No Disappear)
- Ship flies across shooting green squares (always visible)
- Returns to center, fires MEGA RED LASER
- Entire grid explodes in massive shockwave
- Everything rebuilds at end of cycle
- Ship NEVER leaves the screen
"""

import os, json, math, random, urllib.request
from datetime import datetime, timedelta

GITHUB_API = "https://api.github.com/graphql"

BG    = "#0d1117"
EMPTY = "#161b22"
LV    = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

LEVEL_MAP = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

SHIP_C  = "#00ff88"; SHIP_C2 = "#00cc66"
LASER_C = "#00ffcc"; BOLT_C  = "#00d4ff"
FLASH_C = "#ffffff"; BOOM_C  = "#ff6600"; BOOM_C2 = "#ffcc00"
STAR_C  = "#ffffff"; LABEL_C = "#8b949e"
MEGA_C  = "#ff0000"; MEGA_C2 = "#ff3300"; MEGA_C3 = "#ff6600"

CELL = 10; GAP = 3; STEP = 13; ROWS = 7
ML = 55; MT = 80; MR = 35; MB = 25
CYCLE = 28

WEEKDAY_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}
MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]


def get_lv(c):
    if c == 0: return 0
    if c <= 3: return 1
    if c <= 6: return 2
    if c <= 9: return 3
    return 4


def fetch_contributions(username, token):
    q = """query($u:String!){user(login:$u){contributionsCollection{
    contributionCalendar{weeks{contributionDays{
      contributionCount contributionLevel date weekday
    }}}}}}"""
    p = json.dumps({"query": q, "variables": {"u": username}}).encode()
    req = urllib.request.Request(GITHUB_API, data=p, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode())
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    grid, dates = [], []
    for w in weeks:
        days = w["contributionDays"]
        col = []
        for d in days:
            level_str = d.get("contributionLevel", "NONE")
            level = LEVEL_MAP.get(level_str, 0)
            if level == 0 and d["contributionCount"] > 0:
                level = get_lv(d["contributionCount"])
            col.append({"level": level, "count": d["contributionCount"]})
        while len(col) < 7:
            col.append({"level": 0, "count": 0})
        grid.append(col)
        dates.append(days[0]["date"] if days else None)
    total_green = sum(1 for w in grid for d in w if d["level"] > 0)
    by_level = {i: sum(1 for w in grid for d in w if d["level"] == i) for i in range(5)}
    print(f"   API returned {len(grid)} weeks")
    print(f"   Green squares: {total_green} (L1:{by_level[1]} L2:{by_level[2]} L3:{by_level[3]} L4:{by_level[4]})")
    return grid, dates


def demo_grid():
    random.seed(2024)
    n = 53; grid = []
    for _ in range(n):
        col = []
        for d in range(ROWS):
            if d >= 5:
                c = random.choices([0,1,2,3], weights=[55,25,12,8])[0]
            else:
                c = random.choices([0,1,2,3,5,8,12], weights=[25,20,18,15,12,7,3])[0]
            col.append({"level": get_lv(c), "count": c})
        grid.append(col)
    today = datetime.now()
    ds = (today.weekday() + 1) % 7
    ls = today - timedelta(days=ds)
    ss = ls - timedelta(weeks=n - 1)
    dates = [(ss + timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(n)]
    return grid, dates


def get_month_labels(dates):
    labels, lm = [], None
    for ci, ds in enumerate(dates):
        if not ds: continue
        try:
            m = datetime.strptime(ds, "%Y-%m-%d").month
            if m != lm: labels.append({"col": ci, "name": MONTH_NAMES[m-1]}); lm = m
        except: continue
    return labels


def group_targets(grid):
    tc = [ci for ci, w in enumerate(grid) if any(d["level"] > 0 for d in w)]
    groups, i = [], 0
    while i < len(tc):
        g = [tc[i]]
        while len(g) < 3 and i+1 < len(tc) and tc[i+1] - g[-1] <= 2:
            i += 1; g.append(tc[i])
        groups.append(g); i += 1
    return groups


def build_svg(grid, dates):
    COLS = len(grid)
    GW = COLS * STEP - GAP
    GH = ROWS * STEP - GAP
    W = ML + GW + MR
    H = MT + GH + MB
    groups = group_targets(grid)
    print(f"   Grid: {COLS}x{ROWS} = {W}x{H}px, {len(groups)} shot groups")

    fly_end_pct = 43.0
    CENTER_ARRIVE = 49.0
    CENTER_AIM    = 51.5
    MEGA_FIRE     = 52.5
    MEGA_HIT      = 53.0
    MEGA_BOOM     = 54.0
    MEGA_EXPAND   = 58.0
    MEGA_FADE     = 62.0
    REBUILD_START = 70.0
    REBUILD_DUR   = 20.0

    SHIP_Y = MT - 30
    gcx = ML + GW // 2
    gcy = MT + GH // 2

    svg = []
    svg.append(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <filter id="glow"><feGaussianBlur stdDeviation="1.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="boltglow"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="boomglow"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="megaglow"><feGaussianBlur stdDeviation="8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="shockglow"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>''')

    css = ['<style>']
    css.append('@keyframes tw { 0%,100%{opacity:.1} 50%{opacity:.85} }')

    # === SHIP X: always visible, never leaves screen ===
    # Start at left edge of grid, fly right shooting, go to right edge,
    # return to center for mega, then back to start
    xs = ML + 5                    # start: left edge of grid (visible)
    xe = ML + GW - 10             # rightmost: right edge of grid (visible)
    scx = gcx - 16                # center position

    kf = [f"0% {{ transform:translateX({xs}px) }}"]
    for gi, grp in enumerate(groups):
        cc = grp[len(grp)//2]
        tx = ML + cc * STEP + CELL//2 - 16
        ap = (cc / COLS) * fly_end_pct
        pe = min(ap + 1.0, fly_end_pct - 1)
        kf.append(f"{ap:.2f}% {{ transform:translateX({tx}px) }}")
        kf.append(f"{pe:.2f}% {{ transform:translateX({tx}px) }}")
    # Reach right edge (still visible)
    kf.append(f"{fly_end_pct:.1f}% {{ transform:translateX({xe}px) }}")
    # Fly back to center for mega (visible the whole time)
    kf.append(f"{CENTER_ARRIVE:.1f}% {{ transform:translateX({scx}px) }}")
    # Stay at center during mega
    kf.append(f"{MEGA_BOOM:.1f}% {{ transform:translateX({scx}px) }}")
    # Return to start position (visible)
    kf.append(f"{MEGA_FADE:.1f}% {{ transform:translateX({xs}px) }}")
    # Stay at start until loop restarts
    kf.append(f"100% {{ transform:translateX({xs}px) }}")
    css.append(f'@keyframes shipX {{ {" ".join(kf)} }}')
    css.append(f'.shipX {{ animation:shipX {CYCLE}s linear infinite; }}')

    # === SHIP ROTATION ===
    rk = ["0% { transform:rotate(0deg) }"]
    for gi, grp in enumerate(groups):
        cc = grp[len(grp)//2]
        ap = (cc / COLS) * fly_end_pct
        pa = max(ap - 1.2, 0.1); pm = max(ap - 0.2, 0.2)
        pf = ap + 0.2; pr = min(ap + 1.2, fly_end_pct - 0.5)
        rk.append(f"{pa:.2f}% {{ transform:rotate(0deg) }}")
        rk.append(f"{pm:.2f}% {{ transform:rotate(80deg) }}")
        rk.append(f"{pf:.2f}% {{ transform:rotate(80deg) }}")
        rk.append(f"{pr:.2f}% {{ transform:rotate(0deg) }}")
    rk.append(f"{fly_end_pct:.1f}% {{ transform:rotate(0deg) }}")
    rk.append(f"{CENTER_ARRIVE:.1f}% {{ transform:rotate(0deg) }}")
    rk.append(f"{CENTER_AIM:.1f}% {{ transform:rotate(-90deg) }}")
    rk.append(f"{MEGA_BOOM:.1f}% {{ transform:rotate(-90deg) }}")
    rk.append(f"{min(MEGA_BOOM+2,MEGA_FADE-0.5):.1f}% {{ transform:rotate(0deg) }}")
    rk.append(f"100% {{ transform:rotate(0deg) }}")
    css.append(f'@keyframes shipR {{ {" ".join(rk)} }}')
    css.append(f'.shipR {{ animation:shipR {CYCLE}s linear infinite; transform-origin:16px 8px; }}')

    # === SHIP HORIZONTAL FLIP (mirror when returning to center) ===
    fk = [f"0% {{ transform:scaleX(1) }}"]
    fk.append(f"{fly_end_pct:.1f}% {{ transform:scaleX(1) }}")
    fk.append(f"{fly_end_pct+0.3:.1f}% {{ transform:scaleX(-1) }}")
    fk.append(f"{CENTER_ARRIVE:.1f}% {{ transform:scaleX(-1) }}")
    fk.append(f"{CENTER_AIM-0.5:.1f}% {{ transform:scaleX(1) }}")
    fk.append(f"{CENTER_AIM:.1f}% {{ transform:scaleX(1) }}")
    fk.append(f"100% {{ transform:scaleX(1) }}")
    css.append(f'@keyframes shipFlip {{ {" ".join(fk)} }}')
    css.append(f'.shipFlip {{ animation:shipFlip {CYCLE}s linear infinite; transform-origin:16px 8px; }}')

    # === EXHAUST FIRE ===
    ek = ["0% { opacity:1 }"]
    for gi, grp in enumerate(groups):
        cc = grp[len(grp)//2]
        ap = (cc / COLS) * fly_end_pct
        pa = max(ap - 1.2, 0.1); pm = max(ap - 0.2, 0.2)
        pf = ap + 0.2; pr = min(ap + 1.2, fly_end_pct - 0.5)
        ek.append(f"{pa:.2f}% {{ opacity:1 }}")
        ek.append(f"{pm:.2f}% {{ opacity:0 }}")
        ek.append(f"{pf:.2f}% {{ opacity:0 }}")
        ek.append(f"{pr:.2f}% {{ opacity:1 }}")
    ek.append(f"{fly_end_pct:.1f}% {{ opacity:1 }}")
    ek.append(f"{CENTER_ARRIVE:.1f}% {{ opacity:1 }}")
    ek.append(f"{CENTER_AIM:.1f}% {{ opacity:0 }}")
    ek.append(f"{MEGA_BOOM:.1f}% {{ opacity:0 }}")
    ek.append(f"{min(MEGA_BOOM+2,MEGA_FADE-0.5):.1f}% {{ opacity:1 }}")
    ek.append(f"100% {{ opacity:1 }}")
    css.append(f'@keyframes exhaust {{ {" ".join(ek)} }}')
    css.append(f'.exhaust {{ animation:exhaust {CYCLE}s linear infinite; }}')

    # === INDIVIDUAL BOLTS ===
    for gi, grp in enumerate(groups):
        cc = grp[len(grp)//2]
        ap = (cc / COLS) * fly_end_pct
        pf = ap + 0.1; pt = ap + 0.5; ph = ap + 0.8; pg = ap + 1.0
        bys = SHIP_Y + 12; bye = MT + GH//2
        css.append(f'''@keyframes bolt{gi} {{
  0%,{max(pf-0.1,0):.2f}% {{ cy:{bys}; opacity:0; r:0; }}
  {pf:.2f}% {{ cy:{bys}; opacity:1; r:4; }}
  {pt:.2f}% {{ cy:{(bys+bye)//2}; opacity:1; r:3; }}
  {ph:.2f}% {{ cy:{bye}; opacity:1; r:5; }}
  {pg:.2f}% {{ cy:{bye}; opacity:0; r:0; }}
  100% {{ opacity:0; r:0; }}
}}
.bolt{gi} {{ animation:bolt{gi} {CYCLE}s linear infinite; }}''')
        css.append(f'''@keyframes trail{gi} {{
  0%,{max(pf-0.1,0):.2f}% {{ opacity:0; }}
  {pf:.2f}% {{ opacity:.8; }}
  {ph:.2f}% {{ opacity:.5; }}
  {pg:.2f}% {{ opacity:0; }}
  100% {{ opacity:0; }}
}}
.trail{gi} {{ animation:trail{gi} {CYCLE}s linear infinite; }}''')
        css.append(f'''@keyframes xpl{gi} {{
  0%,{max(ph-0.05,0):.2f}% {{ r:0; opacity:0; }}
  {ph:.2f}% {{ r:8; opacity:1; }}
  {min(ph+0.4,99):.2f}% {{ r:18; opacity:.5; }}
  {min(ph+0.8,99):.2f}% {{ r:24; opacity:0; }}
  100% {{ r:0; opacity:0; }}
}}
.xpl{gi} {{ animation:xpl{gi} {CYCLE}s linear infinite; }}''')

    # === INDIVIDUAL GREEN SQUARE DESTROY ===
    shot_set = set()
    for gi, grp in enumerate(groups):
        cc = grp[len(grp)//2]
        ap = (cc / COLS) * fly_end_pct
        ph = ap + 0.8
        for ci in grp:
            for ri, day in enumerate(grid[ci]):
                if day["level"] == 0: continue
                shot_set.add((ci, ri))
                sid = f"c{ci}r{ri}"; clr = LV[day["level"]]
                pfl = min(ph+0.1,99); psh = min(ph+0.3,99); pdd = min(ph+0.6,99)
                rb_s = REBUILD_START + (ci/COLS)*REBUILD_DUR
                rb_e = min(rb_s+2.0,96); rb_set = min(rb_e+1.0,98)
                css.append(f'''@keyframes d{sid} {{
  0%,{max(ph-0.1,0):.2f}% {{ fill:{clr}; transform:scale(1); }}
  {ph:.2f}% {{ fill:{FLASH_C}; transform:scale(1.6); }}
  {pfl:.2f}% {{ fill:{BOOM_C2}; transform:scale(1.3); }}
  {psh:.2f}% {{ fill:{BOOM_C}; transform:scale(.4); }}
  {pdd:.2f}% {{ fill:{EMPTY}; transform:scale(1); }}
  {rb_s:.2f}% {{ fill:{EMPTY}; transform:scale(1); }}
  {rb_e:.2f}% {{ fill:{clr}; transform:scale(1.15); }}
  {rb_set:.2f}% {{ fill:{clr}; transform:scale(1); }}
  100% {{ fill:{clr}; transform:scale(1); }}
}}
.{sid} {{ animation:d{sid} {CYCLE}s linear infinite; transform-origin:center; transform-box:fill-box; }}''')

    # === MEGA LASER BEAM ===
    css.append(f'''@keyframes megaBeam {{
  0%,{MEGA_FIRE-0.5:.1f}% {{ opacity:0; stroke-width:0; }}
  {MEGA_FIRE:.1f}% {{ opacity:1; stroke-width:3; }}
  {MEGA_FIRE+0.3:.1f}% {{ opacity:1; stroke-width:14; }}
  {MEGA_HIT:.1f}% {{ opacity:1; stroke-width:20; }}
  {MEGA_BOOM:.1f}% {{ opacity:.9; stroke-width:28; }}
  {MEGA_EXPAND:.1f}% {{ opacity:.3; stroke-width:6; }}
  {MEGA_FADE:.1f}% {{ opacity:0; stroke-width:0; }}
  100% {{ opacity:0; }}
}}
.megaBeam {{ animation:megaBeam {CYCLE}s linear infinite; }}''')
    css.append(f'''@keyframes megaCore {{
  0%,{MEGA_FIRE-0.5:.1f}% {{ opacity:0; stroke-width:0; }}
  {MEGA_FIRE+0.3:.1f}% {{ opacity:1; stroke-width:5; }}
  {MEGA_HIT:.1f}% {{ opacity:1; stroke-width:9; }}
  {MEGA_BOOM:.1f}% {{ opacity:.8; stroke-width:12; }}
  {MEGA_EXPAND:.1f}% {{ opacity:.2; stroke-width:2; }}
  {MEGA_FADE:.1f}% {{ opacity:0; }}
  100% {{ opacity:0; }}
}}
.megaCore {{ animation:megaCore {CYCLE}s linear infinite; }}''')

    # === MEGA EXPLOSION CIRCLES ===
    for idx, (color, mr, delay) in enumerate([(MEGA_C,60,0),(BOOM_C2,90,0.3),(MEGA_C2,120,0.6)]):
        s = MEGA_HIT + delay; p = s + 0.8; f = p + 2.0
        css.append(f'''@keyframes megaBoom{idx} {{
  0%,{max(s-0.1,0):.2f}% {{ r:0; opacity:0; }}
  {s:.2f}% {{ r:5; opacity:.9; }}
  {p:.2f}% {{ r:{mr}; opacity:.6; }}
  {f:.2f}% {{ r:{mr+30}; opacity:0; }}
  100% {{ r:0; opacity:0; }}
}}
.megaBoom{idx} {{ animation:megaBoom{idx} {CYCLE}s linear infinite; }}''')

    # === SHOCKWAVE ===
    msr = max(GW, GH)//2 + 40
    css.append(f'''@keyframes shockwave {{
  0%,{MEGA_HIT-0.1:.2f}% {{ r:0; stroke-width:0; opacity:0; }}
  {MEGA_HIT:.2f}% {{ r:5; stroke-width:6; opacity:1; }}
  {MEGA_HIT+1.5:.2f}% {{ r:{msr//2}; stroke-width:4; opacity:.7; }}
  {MEGA_HIT+3:.2f}% {{ r:{msr}; stroke-width:1; opacity:0; }}
  100% {{ r:0; opacity:0; }}
}}
.shockwave {{ animation:shockwave {CYCLE}s linear infinite; }}''')

    # === FLASH OVERLAY ===
    css.append(f'''@keyframes megaFlash {{
  0%,{MEGA_HIT-0.1:.2f}% {{ opacity:0; }}
  {MEGA_HIT:.2f}% {{ opacity:.7; }}
  {MEGA_HIT+0.3:.2f}% {{ opacity:.4; }}
  {MEGA_HIT+1.5:.2f}% {{ opacity:0; }}
  100% {{ opacity:0; }}
}}
.megaFlash {{ animation:megaFlash {CYCLE}s linear infinite; }}''')

    # === ALL REMAINING SQUARES: MEGA DESTROY ===
    for ci, week in enumerate(grid):
        for ri, day in enumerate(week):
            if (ci, ri) in shot_set: continue
            sid = f"c{ci}r{ri}"; clr = LV[day["level"]]
            dx = abs(ci - COLS//2); dy = abs(ri - ROWS//2)
            dist = math.sqrt(dx*dx + dy*dy)
            maxd = math.sqrt((COLS//2)**2 + (ROWS//2)**2)
            ripple = (dist / maxd) * 2.0
            ph = MEGA_HIT + ripple
            pfl = min(ph+0.15,99); psh = min(ph+0.4,99); pdd = min(ph+0.8,99)
            rb_s = REBUILD_START + (ci/COLS)*REBUILD_DUR
            rb_e = min(rb_s+2.0,96); rb_set = min(rb_e+1.0,98)
            css.append(f'''@keyframes d{sid} {{
  0%,{max(ph-0.1,0):.2f}% {{ fill:{clr}; transform:scale(1); }}
  {ph:.2f}% {{ fill:{FLASH_C}; transform:scale(1.5); }}
  {pfl:.2f}% {{ fill:{MEGA_C}; transform:scale(1.2); }}
  {psh:.2f}% {{ fill:{BOOM_C}; transform:scale(.3); }}
  {pdd:.2f}% {{ fill:{EMPTY}; transform:scale(0); }}
  {rb_s:.2f}% {{ fill:{EMPTY}; transform:scale(0); }}
  {rb_e:.2f}% {{ fill:{clr}; transform:scale(1.1); }}
  {rb_set:.2f}% {{ fill:{clr}; transform:scale(1); }}
  100% {{ fill:{clr}; transform:scale(1); }}
}}
.{sid} {{ animation:d{sid} {CYCLE}s linear infinite; transform-origin:center; transform-box:fill-box; }}''')

    css.append('</style>')
    svg.append('\n'.join(css))

    # === BACKGROUND ===
    svg.append(f'<rect width="{W}" height="{H}" rx="6" fill="{BG}"/>')

    # === STARS ===
    random.seed(42)
    for _ in range(45):
        sx, sy = random.randint(2,W-2), random.randint(2,H-2)
        sr = random.uniform(.3,1.1); dur = random.uniform(1.5,4); dl = random.uniform(0,5)
        svg.append(f'<circle cx="{sx}" cy="{sy}" r="{sr}" fill="{STAR_C}" opacity=".2" style="animation:tw {dur:.1f}s ease {dl:.1f}s infinite;"/>')

    # === LABELS ===
    for ml_item in get_month_labels(dates):
        lx = ML + ml_item["col"] * STEP
        svg.append(f'<text x="{lx}" y="{MT-8}" fill="{LABEL_C}" font-family="Segoe UI,Helvetica,Arial,sans-serif" font-size="9" opacity=".8">{ml_item["name"]}</text>')
    for row_idx, label in WEEKDAY_LABELS.items():
        ly = MT + row_idx * STEP + CELL * 0.8
        svg.append(f'<text x="{ML-10}" y="{ly}" fill="{LABEL_C}" font-family="Segoe UI,Helvetica,Arial,sans-serif" font-size="9" text-anchor="end" opacity=".8">{label}</text>')

    # === GRID SQUARES ===
    for ci, week in enumerate(grid):
        for ri, day in enumerate(week):
            x = ML + ci * STEP; y = MT + ri * STEP
            sid = f"c{ci}r{ri}"; clr = LV[day["level"]]
            svg.append(f'<rect class="{sid}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{clr}"/>')

    # === INDIVIDUAL SHOTS ===
    for gi, grp in enumerate(groups):
        cc = grp[len(grp)//2]; bx = ML + cc * STEP + CELL//2
        svg.append(f'<line class="trail{gi}" x1="{bx}" y1="{SHIP_Y+14}" x2="{bx}" y2="{MT+GH//2}" stroke="{LASER_C}" stroke-width="2" opacity="0" filter="url(#boltglow)" stroke-linecap="round"/>')
    for gi, grp in enumerate(groups):
        cc = grp[len(grp)//2]; bx = ML + cc * STEP + CELL//2
        svg.append(f'<circle class="bolt{gi}" cx="{bx}" cy="{SHIP_Y+12}" r="0" fill="{BOLT_C}" filter="url(#boltglow)" opacity="0"/>')
    for gi, grp in enumerate(groups):
        cc = grp[len(grp)//2]; ex = ML + cc * STEP + CELL//2
        svg.append(f'<circle class="xpl{gi}" cx="{ex}" cy="{MT+GH//2}" r="0" fill="{BOOM_C2}" opacity="0" filter="url(#boomglow)"/>')

    # === MEGA LASER ===
    svg.append(f'<line class="megaBeam" x1="{gcx}" y1="{SHIP_Y+16}" x2="{gcx}" y2="{gcy}" stroke="{MEGA_C}" stroke-width="0" opacity="0" filter="url(#megaglow)" stroke-linecap="round"/>')
    svg.append(f'<line class="megaCore" x1="{gcx}" y1="{SHIP_Y+16}" x2="{gcx}" y2="{gcy}" stroke="{FLASH_C}" stroke-width="0" opacity="0" stroke-linecap="round"/>')

    # === MEGA EXPLOSIONS ===
    for idx, c in enumerate([MEGA_C, BOOM_C2, MEGA_C2]):
        svg.append(f'<circle class="megaBoom{idx}" cx="{gcx}" cy="{gcy}" r="0" fill="none" stroke="{c}" stroke-width="3" opacity="0" filter="url(#megaglow)"/>')
    svg.append(f'<circle class="shockwave" cx="{gcx}" cy="{gcy}" r="0" fill="none" stroke="{FLASH_C}" stroke-width="0" opacity="0" filter="url(#shockglow)"/>')
    svg.append(f'<rect class="megaFlash" width="{W}" height="{H}" rx="6" fill="{FLASH_C}" opacity="0"/>')

    # === SPACESHIP ===
    svg.append(f'''
<g class="shipX">
  <g style="transform:translateY({SHIP_Y}px)">
    <g class="shipFlip">
    <g class="shipR" filter="url(#glow)">
      <polygon points="0,8 8,3 20,1 28,4 32,8 28,12 20,15 8,13" fill="{SHIP_C}"/>
      <line x1="8" y1="8" x2="22" y2="2" stroke="{SHIP_C2}" stroke-width=".8"/>
      <line x1="8" y1="8" x2="22" y2="14" stroke="{SHIP_C2}" stroke-width=".8"/>
      <polygon class="exhaust" points="28,5 36,8 28,11" fill="{SHIP_C2}"/>
      <polygon class="exhaust" points="32,6 38,8 32,10" fill="#00ffaa" opacity=".85"/>
      <rect class="exhaust" x="36" y="6.5" width="5" height="3" rx="1" fill="{LASER_C}" opacity=".7"/>
      <ellipse cx="20" cy="8" rx="4" ry="3" fill="#ffffff" opacity=".85"/>
      <ellipse cx="20" cy="8" rx="2.5" ry="1.8" fill="{BOLT_C}" opacity=".25"/>
      <polygon points="10,3 16,3 14,0" fill="{SHIP_C2}" opacity=".7"/>
      <polygon points="10,13 16,13 14,16" fill="{SHIP_C2}" opacity=".7"/>
    </g>
    </g>
  </g>
</g>''')

    svg.append('</svg>')
    return '\n'.join(svg)


def main():
    username = os.environ.get("GITHUB_USERNAME", "cjgpedroso-coder")
    token = os.environ.get("GITHUB_TOKEN", "")
    out = os.environ.get("OUTPUT_DIR", "dist")
    os.makedirs(out, exist_ok=True)

    using_real = False
    if token:
        print(f"🚀 Fetching {username}...")
        print(f"   Token: {token[:4]}***{token[-4:]} ({len(token)} chars)")
        try:
            grid, dates = fetch_contributions(username, token)
            using_real = True
            print(f"✅ {len(grid)} weeks (last: {dates[-1]})")
        except Exception as e:
            print(f"❌ API ERROR: {e}")
            grid, dates = demo_grid()
    else:
        print("⚠️ No GITHUB_TOKEN — demo mode")
        grid, dates = demo_grid()

    if not using_real:
        print("⚠️ WARNING: Using DEMO data!")

    print("🎨 Building spaceship v4 (Grand Finale)...")
    s = build_svg(grid, dates)

    for name in ("github-spaceship-dark.svg", "github-spaceship.svg"):
        path = os.path.join(out, name)
        with open(path, "w") as f: f.write(s)
        print(f"✅ {path} ({len(s):,}b)")
    print("🚀 Done!")

if __name__ == "__main__":
    main()

