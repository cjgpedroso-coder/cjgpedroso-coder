#!/usr/bin/env python3
"""
🚀 GitHub Spaceship v3 — Clean rewrite
- Ship flies across the top
- Rotates nose downward before each shot group
- Fires visible projectile bolts that travel to targets
- Targets flash and disintegrate on hit
- Everything rebuilds at end of cycle
"""

import os, json, math, random, urllib.request

GITHUB_API = "https://api.github.com/graphql"

# ── Colors ──
BG       = "#0d1117"
EMPTY    = "#161b22"
LV       = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
SHIP_C   = "#00ff88"
SHIP_C2  = "#00cc66"
LASER_C  = "#00ffcc"
BOLT_C   = "#00d4ff"
FLASH_C  = "#ffffff"
BOOM_C   = "#ff6600"
BOOM_C2  = "#ffcc00"
THRUST_C = "#ff6600"
THRUST_C2= "#ffcc00"
STAR_C   = "#ffffff"

# ── Grid layout ──
CELL = 10; GAP = 3; STEP = 13
COLS = 52; ROWS = 7
ML = 35; MT = 65; MR = 35; MB = 25  # bigger top margin for ship
GW = COLS * STEP - GAP
GH = ROWS * STEP - GAP
W = ML + GW + MR
H = MT + GH + MB

# ── Timing ──
CYCLE = 24  # seconds total loop


def get_lv(c):
    if c == 0: return 0
    if c <= 3: return 1
    if c <= 6: return 2
    if c <= 9: return 3
    return 4


# ── Data fetch ──

def fetch_contributions(username, token):
    q = """query($u:String!){user(login:$u){contributionsCollection{
    contributionCalendar{weeks{contributionDays{contributionCount date weekday}}}}}}"""
    p = json.dumps({"query": q, "variables": {"u": username}}).encode()
    req = urllib.request.Request(GITHUB_API, data=p, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode())
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    grid = []
    for w in weeks:
        col = [{"level": get_lv(d["contributionCount"])} for d in w["contributionDays"]]
        grid.append(col)
    while len(grid) < COLS:
        grid.append([{"level": 0} for _ in range(7)])
    return grid[:COLS]


def demo_grid():
    random.seed(2024)
    grid = []
    for _ in range(COLS):
        col = []
        for d in range(ROWS):
            if d >= 5:
                c = random.choices([0,1,2,3], weights=[55,25,12,8])[0]
            else:
                c = random.choices([0,1,2,3,5,8,12], weights=[25,20,18,15,12,7,3])[0]
            col.append({"level": get_lv(c)})
        grid.append(col)
    return grid


# ── Group adjacent target columns for cleaner animation ──

def group_targets(grid):
    """Group target columns into shot groups (max 3 cols per group)."""
    target_cols = []
    for ci, week in enumerate(grid):
        has_target = any(d["level"] > 0 for d in week)
        if has_target:
            target_cols.append(ci)

    groups = []
    i = 0
    while i < len(target_cols):
        grp = [target_cols[i]]
        while len(grp) < 3 and i + 1 < len(target_cols) and target_cols[i + 1] - grp[-1] <= 2:
            i += 1
            grp.append(target_cols[i])
        groups.append(grp)
        i += 1
    return groups


# ── SVG ──

def build_svg(grid):
    groups = group_targets(grid)
    n_groups = len(groups)

    # Timing: ship flies during first 60% of cycle
    fly_dur = CYCLE * 0.60  # seconds of flight
    rebuild_start_pct = 75
    rebuild_dur_pct = 18

    def t2p(sec):
        """Seconds -> percentage of cycle"""
        return (sec / CYCLE) * 100

    # Ship Y: flies at fixed altitude
    SHIP_Y = MT - 30  # ship center Y, well above grid

    svg = []
    svg.append(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <filter id="glow"><feGaussianBlur stdDeviation="1.5" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="boltglow"><feGaussianBlur stdDeviation="3" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="boomglow"><feGaussianBlur stdDeviation="5" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>''')

    # ── CSS ──
    css = ['<style>']

    # Twinkle stars
    css.append('@keyframes tw { 0%,100%{opacity:.1} 50%{opacity:.85} }')

    # Thrust flicker

    # ── Ship X movement ──
    x_start = ML - 50
    x_end = ML + GW + 40
    fly_end_pct = t2p(fly_dur)

    # Build ship X keyframes with pauses at each group
    ship_x_kf = []
    ship_x_kf.append(f"0% {{ transform:translateX({x_start}px) }}")

    for gi, grp in enumerate(groups):
        center_col = grp[len(grp)//2]
        target_x = ML + center_col * STEP + CELL // 2 - 16  # offset for ship width
        # Time when ship arrives at this group
        arrive_pct = t2p((center_col / COLS) * fly_dur)
        # Brief pause (ship hovers to aim and shoot)
        pause_end = min(arrive_pct + 1.2, fly_end_pct - 1)

        ship_x_kf.append(f"{arrive_pct:.2f}% {{ transform:translateX({target_x}px) }}")
        ship_x_kf.append(f"{pause_end:.2f}% {{ transform:translateX({target_x}px) }}")

    ship_x_kf.append(f"{fly_end_pct:.1f}% {{ transform:translateX({x_end}px) }}")
    ship_x_kf.append(f"100% {{ transform:translateX({x_end}px) }}")

    css.append(f'@keyframes shipX {{ {" ".join(ship_x_kf)} }}')
    css.append(f'.shipX {{ animation:shipX {CYCLE}s linear infinite; }}')

    # ── Ship rotation (aim down at target groups) ──
    rot_kf = []
    rot_kf.append("0% { transform:rotate(0deg) }")

    for gi, grp in enumerate(groups):
        center_col = grp[len(grp)//2]
        arrive_pct = t2p((center_col / COLS) * fly_dur)

        # Timeline: approach → aim down → hold → fire → recover
        p_approach  = max(arrive_pct - 1.5, 0.1)
        p_aimed     = max(arrive_pct - 0.3, 0.2)
        p_fire      = arrive_pct + 0.3
        p_recover   = min(arrive_pct + 1.5, fly_end_pct - 0.5)

        rot_kf.append(f"{p_approach:.2f}% {{ transform:rotate(0deg) }}")
        rot_kf.append(f"{p_aimed:.2f}% {{ transform:rotate(80deg) }}")
        rot_kf.append(f"{p_fire:.2f}% {{ transform:rotate(80deg) }}")
        rot_kf.append(f"{p_recover:.2f}% {{ transform:rotate(0deg) }}")

    rot_kf.append(f"{fly_end_pct:.1f}% {{ transform:rotate(0deg) }}")
    rot_kf.append("100% { transform:rotate(0deg) }")

    css.append(f'@keyframes shipR {{ {" ".join(rot_kf)} }}')
    css.append(f'.shipR {{ animation:shipR {CYCLE}s linear infinite; transform-origin:16px 8px; }}')

    # ── Projectile bolts (one per group) ──
    for gi, grp in enumerate(groups):
        center_col = grp[len(grp)//2]
        bolt_x = ML + center_col * STEP + CELL // 2

        arrive_pct = t2p((center_col / COLS) * fly_dur)
        p_fire   = arrive_pct + 0.1
        p_travel = arrive_pct + 0.6
        p_hit    = arrive_pct + 0.9
        p_gone   = arrive_pct + 1.1

        # Bolt travels from ship Y down to mid-grid
        bolt_y_start = SHIP_Y + 12
        bolt_y_end = MT + GH // 2

        css.append(f'''@keyframes bolt{gi} {{
  0%,{max(p_fire-0.1,0):.2f}% {{ cy:{bolt_y_start}; opacity:0; r:0; }}
  {p_fire:.2f}% {{ cy:{bolt_y_start}; opacity:1; r:4; }}
  {p_travel:.2f}% {{ cy:{(bolt_y_start+bolt_y_end)//2}; opacity:1; r:3; }}
  {p_hit:.2f}% {{ cy:{bolt_y_end}; opacity:1; r:5; }}
  {p_gone:.2f}% {{ cy:{bolt_y_end}; opacity:0; r:0; }}
  100% {{ opacity:0; r:0; }}
}}
.bolt{gi} {{ animation:bolt{gi} {CYCLE}s linear infinite; }}''')

        # Bolt trail (line from ship to impact)
        css.append(f'''@keyframes trail{gi} {{
  0%,{max(p_fire-0.1,0):.2f}% {{ opacity:0; }}
  {p_fire:.2f}% {{ opacity:.8; }}
  {p_hit:.2f}% {{ opacity:.5; }}
  {p_gone:.2f}% {{ opacity:0; }}
  100% {{ opacity:0; }}
}}
.trail{gi} {{ animation:trail{gi} {CYCLE}s linear infinite; }}''')

        # Explosion at impact
        css.append(f'''@keyframes xpl{gi} {{
  0%,{max(p_hit-0.05,0):.2f}% {{ r:0; opacity:0; }}
  {p_hit:.2f}% {{ r:8; opacity:1; }}
  {min(p_hit+0.5,99):.2f}% {{ r:20; opacity:.6; }}
  {min(p_hit+1.0,99):.2f}% {{ r:28; opacity:0; }}
  100% {{ r:0; opacity:0; }}
}}
.xpl{gi} {{ animation:xpl{gi} {CYCLE}s linear infinite; }}''')

    # ── Square destroy & rebuild ──
    for gi, grp in enumerate(groups):
        center_col = grp[len(grp)//2]
        arrive_pct = t2p((center_col / COLS) * fly_dur)
        p_hit = arrive_pct + 0.9

        for ci in grp:
            for ri, day in enumerate(grid[ci]):
                if day["level"] == 0:
                    continue
                sid = f"c{ci}r{ri}"
                clr = LV[day["level"]]

                p_flash   = min(p_hit + 0.1, 99)
                p_shrink  = min(p_hit + 0.4, 99)
                p_dead    = min(p_hit + 0.8, 99)

                # Rebuild timing spread across columns
                rb_s = rebuild_start_pct + (ci / COLS) * rebuild_dur_pct
                rb_e = min(rb_s + 2.5, 98)
                rb_settle = min(rb_e + 1.0, 99)

                css.append(f'''@keyframes d{sid} {{
  0%,{max(p_hit-0.1,0):.2f}% {{ fill:{clr}; transform:scale(1); }}
  {p_hit:.2f}% {{ fill:{FLASH_C}; transform:scale(1.6); }}
  {p_flash:.2f}% {{ fill:{BOOM_C2}; transform:scale(1.3); }}
  {p_shrink:.2f}% {{ fill:{BOOM_C}; transform:scale(.4); }}
  {p_dead:.2f}% {{ fill:{EMPTY}; transform:scale(1); }}
  {rb_s:.2f}% {{ fill:{EMPTY}; transform:scale(1); }}
  {rb_e:.2f}% {{ fill:{clr}; transform:scale(1.15); }}
  {rb_settle:.2f}% {{ fill:{clr}; transform:scale(1); }}
  100% {{ fill:{clr}; transform:scale(1); }}
}}
.{sid} {{ animation:d{sid} {CYCLE}s linear infinite; transform-origin:center; transform-box:fill-box; }}''')

    css.append('</style>')
    svg.append('\n'.join(css))

    # ── Background ──
    svg.append(f'<rect width="{W}" height="{H}" rx="6" fill="{BG}"/>')

    # ── Stars ──
    random.seed(42)
    for _ in range(45):
        sx, sy = random.randint(2, W-2), random.randint(2, H-2)
        sr = random.uniform(.3, 1.1)
        dur = random.uniform(1.5, 4)
        dl = random.uniform(0, 5)
        svg.append(f'<circle cx="{sx}" cy="{sy}" r="{sr}" fill="{STAR_C}" opacity=".2" '
                   f'style="animation:tw {dur:.1f}s ease {dl:.1f}s infinite;"/>')

    # ── Grid squares ──
    for ci, week in enumerate(grid):
        for ri, day in enumerate(week):
            x = ML + ci * STEP
            y = MT + ri * STEP
            clr = LV[day["level"]]
            if day["level"] > 0:
                sid = f"c{ci}r{ri}"
                svg.append(f'<rect class="{sid}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{clr}"/>')
            else:
                svg.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{clr}"/>')

    # ── Projectile trails (laser lines) ──
    for gi, grp in enumerate(groups):
        center_col = grp[len(grp)//2]
        bx = ML + center_col * STEP + CELL // 2
        svg.append(f'<line class="trail{gi}" x1="{bx}" y1="{SHIP_Y+14}" x2="{bx}" y2="{MT+GH//2}" '
                   f'stroke="{LASER_C}" stroke-width="2" opacity="0" filter="url(#boltglow)" stroke-linecap="round"/>')

    # ── Projectile bolts (circles) ──
    for gi, grp in enumerate(groups):
        center_col = grp[len(grp)//2]
        bx = ML + center_col * STEP + CELL // 2
        svg.append(f'<circle class="bolt{gi}" cx="{bx}" cy="{SHIP_Y+12}" r="0" fill="{BOLT_C}" filter="url(#boltglow)" opacity="0"/>')

    # ── Explosions ──
    for gi, grp in enumerate(groups):
        center_col = grp[len(grp)//2]
        ex = ML + center_col * STEP + CELL // 2
        ey = MT + GH // 2
        svg.append(f'<circle class="xpl{gi}" cx="{ex}" cy="{ey}" r="0" fill="{BOOM_C2}" opacity="0" filter="url(#boomglow)"/>')

    # ── SPACESHIP ──
    svg.append(f'''
<g class="shipX">
  <g style="transform:translateY({SHIP_Y}px)">
    <g class="shipR" filter="url(#glow)">

      <!-- Thrust flames -->

      <!-- Main hull -->
      <polygon points="0,8 8,3 20,1 28,4 32,8 28,12 20,15 8,13" fill="{SHIP_C}"/>

      <!-- Hull detail lines -->
      <line x1="8" y1="8" x2="22" y2="2" stroke="{SHIP_C2}" stroke-width=".8"/>
      <line x1="8" y1="8" x2="22" y2="14" stroke="{SHIP_C2}" stroke-width=".8"/>

      <!-- Nose / gun -->
      <polygon points="28,5 36,8 28,11" fill="{SHIP_C2}"/>
      <polygon points="32,6 38,8 32,10" fill="#00ffaa" opacity=".85"/>
      <rect x="36" y="6.5" width="5" height="3" rx="1" fill="{LASER_C}" opacity=".7"/>

      <!-- Cockpit -->
      <ellipse cx="20" cy="8" rx="4" ry="3" fill="#ffffff" opacity=".85"/>
      <ellipse cx="20" cy="8" rx="2.5" ry="1.8" fill="{BOLT_C}" opacity=".25"/>

      <!-- Top fin -->
      <polygon points="10,3 16,3 14,0" fill="{SHIP_C2}" opacity=".7"/>
      <!-- Bottom fin -->
      <polygon points="10,13 16,13 14,16" fill="{SHIP_C2}" opacity=".7"/>

    </g>
  </g>
</g>''')

    svg.append('</svg>')
    return '\n'.join(svg)


# ── Main ──

def main():
    username = os.environ.get("GITHUB_USERNAME", "cjgpedroso-coder")
    token = os.environ.get("GITHUB_TOKEN", "")
    out = os.environ.get("OUTPUT_DIR", "dist")
    os.makedirs(out, exist_ok=True)

    if token:
        print(f"🚀 Fetching {username}…")
        try:
            grid = fetch_contributions(username, token)
            print(f"✅ {len(grid)} weeks loaded")
        except Exception as e:
            print(f"⚠️ {e} — demo mode")
            grid = demo_grid()
    else:
        print("⚠️ No token — demo mode")
        grid = demo_grid()

    print("🎨 Building spaceship v3…")
    s = build_svg(grid)

    for name in ("github-spaceship-dark.svg", "github-spaceship.svg"):
        path = os.path.join(out, name)
        with open(path, "w") as f:
            f.write(s)
        print(f"✅ {path} ({len(s):,}b)")

    print("🚀 Done!")

if __name__ == "__main__":
    main()

