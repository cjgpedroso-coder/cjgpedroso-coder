#!/usr/bin/env python3
"""
🚀 GitHub Spaceship Contribution Animation Generator v2
Ship rotates to aim at targets, fires visible projectiles, targets explode.
"""

import os
import json
import math
import random
import urllib.request

GITHUB_API = "https://api.github.com/graphql"

# === COLORS ===
C = {
    "bg":       "#0d1117",
    "empty":    "#161b22",
    "lv1":      "#0e4429",
    "lv2":      "#006d32",
    "lv3":      "#26a641",
    "lv4":      "#39d353",
    "ship":     "#00ff88",
    "ship2":    "#00cc66",
    "cockpit":  "#ffffff",
    "laser":    "#00ffcc",
    "laser2":   "#00d4ff",
    "boom1":    "#ffffff",
    "boom2":    "#ffcc00",
    "boom3":    "#ff6600",
    "thrust1":  "#ff6600",
    "thrust2":  "#ffcc00",
    "star":     "#ffffff",
    "text":     "#8b949e",
}

# === GRID ===
CELL = 10
GAP = 3
STEP = CELL + GAP  # 13
COLS = 52
ROWS = 7

ML = 35   # margin left
MT = 60   # margin top (extra space for ship movement)
MR = 35
MB = 20

GW = COLS * STEP - GAP
GH = ROWS * STEP - GAP

W = ML + GW + MR
H = MT + GH + MB

# === TIMING ===
FLY_TIME = 14        # seconds for ship to cross
REBUILD_START = 0.72  # 72% of cycle — rebuild begins
REBUILD_SPAN = 0.20   # 20% of cycle for full rebuild
CYCLE = 22            # total loop duration


def lvl(count):
    if count == 0: return 0
    if count <= 3: return 1
    if count <= 6: return 2
    if count <= 9: return 3
    return 4


def lvl_color(l):
    return [C["empty"], C["lv1"], C["lv2"], C["lv3"], C["lv4"]][l]


def pct(seconds):
    """Convert seconds to % of cycle."""
    return (seconds / CYCLE) * 100


def clamp(v, lo=0.0, hi=99.9):
    return max(lo, min(v, hi))


# ── GitHub API ──────────────────────────────────────────

def fetch_contributions(username, token):
    query = """query($u:String!){user(login:$u){contributionsCollection{
        contributionCalendar{weeks{contributionDays{contributionCount date weekday}}}}}}"""
    payload = json.dumps({"query": query, "variables": {"u": username}}).encode()
    req = urllib.request.Request(GITHUB_API, data=payload, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode())
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    grid = []
    for w in weeks:
        col = []
        for d in w["contributionDays"]:
            col.append({"count": d["contributionCount"], "level": lvl(d["contributionCount"])})
        grid.append(col)
    while len(grid) < COLS:
        grid.append([{"count": 0, "level": 0} for _ in range(7)])
    return grid[:COLS]


def demo_grid():
    random.seed(2024)
    grid = []
    for w in range(COLS):
        col = []
        for d in range(ROWS):
            if d >= 5:
                c = random.choices([0,1,2,3], weights=[55,25,12,8])[0]
            else:
                c = random.choices([0,1,2,3,5,8,12], weights=[25,20,18,15,12,7,3])[0]
            col.append({"count": c, "level": lvl(c)})
        grid.append(col)
    return grid


# ── SVG Builder ─────────────────────────────────────────

def build_svg(grid):
    # Collect targets: {col_index: [(row, level), ...]}
    targets = {}
    for ci, week in enumerate(grid):
        for ri, day in enumerate(week):
            if day["level"] > 0:
                targets.setdefault(ci, []).append((ri, day["level"]))

    # Sort target columns
    target_cols = sorted(targets.keys())

    # Ship Y positions
    ship_cruise_y = MT - 25          # cruising altitude
    ship_grid_top_y = MT - 8         # dive position (just above grid)

    # For each target column, compute timing
    # ship_time = when ship center is over column
    shots = []
    for ci in target_cols:
        col_center_x = ML + ci * STEP + CELL // 2
        ship_time_s = (ci / COLS) * FLY_TIME + 0.3  # seconds into cycle

        # Find lowest target in this column for aim direction
        rows_in_col = targets[ci]
        lowest_row = max(r for r, _ in rows_in_col)
        target_y = MT + lowest_row * STEP + CELL // 2

        shots.append({
            "ci": ci,
            "col_x": col_center_x,
            "time_s": ship_time_s,
            "target_y": target_y,
            "rows": rows_in_col,
        })

    # ── Start SVG ──
    svg = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <filter id="glow"><feGaussianBlur stdDeviation="2" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="lglow"><feGaussianBlur stdDeviation="2.5" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="bglow"><feGaussianBlur stdDeviation="4" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <radialGradient id="boomG">
    <stop offset="0%" stop-color="{C['boom1']}" stop-opacity="1"/>
    <stop offset="40%" stop-color="{C['boom2']}" stop-opacity=".8"/>
    <stop offset="100%" stop-color="{C['boom3']}" stop-opacity="0"/>
  </radialGradient>
</defs>''']

    # ── CSS ──
    css = ['<style>']

    # Stars twinkle
    css.append('''  @keyframes twinkle {
    0%,100% { opacity:.15; } 50% { opacity:.9; }
  }''')

    # Thrust flicker
    css.append('''  @keyframes thrust {
    0%,100% { opacity:.85; transform:scaleX(1); }
    50% { opacity:.4; transform:scaleX(.6); }
  }
  .thrust { animation: thrust .1s linear infinite; transform-origin: right center; }''')

    # ── Ship horizontal movement ──
    ship_x_start = ML - 40
    ship_x_end = ML + GW + 30
    fly_pct = clamp(pct(FLY_TIME))

    css.append(f'''  @keyframes shipX {{
    0%   {{ transform: translateX({ship_x_start}px); }}
    {fly_pct:.1f}% {{ transform: translateX({ship_x_end}px); }}
    100% {{ transform: translateX({ship_x_end}px); }}
  }}
  .shipX {{ animation: shipX {CYCLE}s linear infinite; }}''')

    # ── Ship vertical movement (dive toward targets) ──
    # Build Y keyframes: cruise by default, dip down near target columns
    y_kf = []
    y_kf.append(f"    0% {{ transform: translateY({ship_cruise_y}px); }}")

    for shot in shots:
        t = shot["time_s"]
        p_before = clamp(pct(t - 0.45))
        p_at     = clamp(pct(t))
        p_after  = clamp(pct(t + 0.45))

        y_kf.append(f"    {p_before:.2f}% {{ transform: translateY({ship_cruise_y}px); }}")
        y_kf.append(f"    {p_at:.2f}% {{ transform: translateY({ship_grid_top_y}px); }}")
        y_kf.append(f"    {p_after:.2f}% {{ transform: translateY({ship_cruise_y}px); }}")

    y_kf.append(f"    {fly_pct:.1f}% {{ transform: translateY({ship_cruise_y}px); }}")
    y_kf.append(f"    100% {{ transform: translateY({ship_cruise_y}px); }}")

    # Deduplicate and sort keyframes
    y_kf_clean = list(dict.fromkeys(y_kf))
    css.append(f'  @keyframes shipY {{\n' + '\n'.join(y_kf_clean) + '\n  }')
    css.append(f'  .shipY {{ animation: shipY {CYCLE}s linear infinite; }}')

    # ── Ship rotation (aim at targets) ──
    rot_kf = []
    rot_kf.append(f"    0% {{ transform: rotate(0deg); }}")

    for shot in shots:
        t = shot["time_s"]
        p_aim_start = clamp(pct(t - 0.35))
        p_aimed     = clamp(pct(t - 0.1))
        p_fire      = clamp(pct(t + 0.05))
        p_recover   = clamp(pct(t + 0.35))

        # Calculate aim angle: ship is above, target is below-right
        # Rotate clockwise (positive) to point nose downward
        aim_angle = 35  # degrees, nose dips down

        rot_kf.append(f"    {p_aim_start:.2f}% {{ transform: rotate(0deg); }}")
        rot_kf.append(f"    {p_aimed:.2f}% {{ transform: rotate({aim_angle}deg); }}")
        rot_kf.append(f"    {p_fire:.2f}% {{ transform: rotate({aim_angle}deg); }}")
        rot_kf.append(f"    {p_recover:.2f}% {{ transform: rotate(0deg); }}")

    rot_kf.append(f"    {fly_pct:.1f}% {{ transform: rotate(0deg); }}")
    rot_kf.append(f"    100% {{ transform: rotate(0deg); }}")

    rot_kf_clean = list(dict.fromkeys(rot_kf))
    css.append(f'  @keyframes shipRot {{\n' + '\n'.join(rot_kf_clean) + '\n  }')
    css.append(f'  .shipRot {{ animation: shipRot {CYCLE}s linear infinite; transform-origin: 12px 7px; }}')

    # ── Laser beams per target column ──
    for shot in shots:
        ci = shot["ci"]
        t = shot["time_s"]
        p_start = clamp(pct(t - 0.05))
        p_on    = clamp(pct(t))
        p_peak  = clamp(pct(t + 0.08))
        p_off   = clamp(pct(t + 0.3))

        css.append(f'''  @keyframes laser-{ci} {{
    0%, {p_start:.2f}% {{ opacity:0; stroke-width:0; }}
    {p_on:.2f}% {{ opacity:1; stroke-width:4; }}
    {p_peak:.2f}% {{ opacity:1; stroke-width:2.5; }}
    {p_off:.2f}% {{ opacity:0; stroke-width:0; }}
    100% {{ opacity:0; stroke-width:0; }}
  }}
  .laser-{ci} {{ animation: laser-{ci} {CYCLE}s linear infinite; }}''')

    # ── Explosion flash per target column ──
    for shot in shots:
        ci = shot["ci"]
        t = shot["time_s"]
        p_pre   = clamp(pct(t - 0.02))
        p_flash = clamp(pct(t + 0.05))
        p_grow  = clamp(pct(t + 0.2))
        p_fade  = clamp(pct(t + 0.5))

        # Center of targets in this column
        mid_row = sum(r for r, _ in shot["rows"]) / len(shot["rows"])
        ey = MT + mid_row * STEP + CELL // 2

        css.append(f'''  @keyframes boom-{ci} {{
    0%, {p_pre:.2f}% {{ opacity:0; r:0; }}
    {p_flash:.2f}% {{ opacity:.9; r:12; }}
    {p_grow:.2f}% {{ opacity:.5; r:18; }}
    {p_fade:.2f}% {{ opacity:0; r:22; }}
    100% {{ opacity:0; r:0; }}
  }}
  .boom-{ci} {{ animation: boom-{ci} {CYCLE}s linear infinite; }}''')

    # ── Square destroy & rebuild per target ──
    for ci in target_cols:
        col_t = shots[[s["ci"] for s in shots].index(ci)]["time_s"]
        p_hit = clamp(pct(col_t))
        p_flash_end = clamp(pct(col_t + 0.1))
        p_shrink = clamp(pct(col_t + 0.25))
        p_dead = clamp(pct(col_t + 0.5))

        rb_start = (REBUILD_START + (ci / COLS) * REBUILD_SPAN) * 100
        rb_end = clamp(rb_start + 3)
        rb_settle = clamp(rb_end + 1.5)

        for ri, lv in targets[ci]:
            sid = f"c{ci}r{ri}"
            clr = lvl_color(lv)

            css.append(f'''  @keyframes d-{sid} {{
    0%, {clamp(p_hit - 0.1):.2f}% {{ fill:{clr}; transform:scale(1); }}
    {p_hit:.2f}% {{ fill:{C["boom1"]}; transform:scale(1.5); }}
    {p_flash_end:.2f}% {{ fill:{C["boom2"]}; transform:scale(1.2); }}
    {p_shrink:.2f}% {{ fill:{C["boom3"]}; transform:scale(.3); }}
    {p_dead:.2f}% {{ fill:{C["empty"]}; transform:scale(1); }}
    {rb_start:.2f}% {{ fill:{C["empty"]}; transform:scale(1); }}
    {rb_end:.2f}% {{ fill:{clr}; transform:scale(1.2); }}
    {rb_settle:.2f}% {{ fill:{clr}; transform:scale(1); }}
    100% {{ fill:{clr}; transform:scale(1); }}
  }}
  .{sid} {{ animation: d-{sid} {CYCLE}s linear infinite;
            transform-origin:center; transform-box:fill-box; }}''')

    css.append('</style>')
    svg.append('\n'.join(css))

    # ── Background ──
    svg.append(f'<rect width="{W}" height="{H}" rx="6" fill="{C["bg"]}"/>')

    # ── Stars ──
    random.seed(42)
    for _ in range(40):
        sx = random.randint(4, W - 4)
        sy = random.randint(4, H - 4)
        sr = random.uniform(.3, 1.0)
        dur = random.uniform(1.5, 4.0)
        dl = random.uniform(0, 4)
        svg.append(
            f'<circle cx="{sx}" cy="{sy}" r="{sr}" fill="{C["star"]}" '
            f'opacity=".3" style="animation:twinkle {dur:.1f}s ease-in-out {dl:.1f}s infinite;"/>')

    # ── Contribution Grid ──
    for ci, week in enumerate(grid):
        for ri, day in enumerate(week):
            x = ML + ci * STEP
            y = MT + ri * STEP
            clr = lvl_color(day["level"])
            if day["level"] > 0:
                sid = f"c{ci}r{ri}"
                svg.append(f'<rect class="{sid}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{clr}"/>')
            else:
                svg.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{clr}"/>')

    # ── Laser Beams (vertical, at each target column) ──
    for shot in shots:
        ci = shot["ci"]
        lx = shot["col_x"]
        svg.append(
            f'<line class="laser-{ci}" x1="{lx}" y1="{MT - 15}" '
            f'x2="{lx}" y2="{MT + GH + 3}" '
            f'stroke="{C["laser"]}" stroke-width="3" '
            f'filter="url(#lglow)" opacity="0" stroke-linecap="round"/>')

    # ── Explosion Flashes ──
    for shot in shots:
        ci = shot["ci"]
        ex = shot["col_x"]
        mid_row = sum(r for r, _ in shot["rows"]) / len(shot["rows"])
        ey = MT + mid_row * STEP + CELL // 2
        svg.append(
            f'<circle class="boom-{ci}" cx="{ex}" cy="{ey}" r="0" '
            f'fill="url(#boomG)" filter="url(#bglow)" opacity="0"/>')

    # ── Spaceship ──
    # Structure: .shipX (horizontal) > .shipY (vertical) > .shipRot (rotation) > graphics
    svg.append(f'''
<!-- ═══ SPACESHIP ═══ -->
<g class="shipX">
  <g class="shipY">
    <g class="shipRot" filter="url(#glow)">

      <!-- Main body -->
      <polygon points="0,7 10,2 22,0 26,7 22,14 10,12" fill="{C['ship']}"/>

      <!-- Nose cone -->
      <polygon points="26,4 32,7 26,10" fill="{C['ship2']}"/>
      <polygon points="30,5.5 34,7 30,8.5" fill="#00ffaa" opacity=".8"/>

      <!-- Cockpit window -->
      <ellipse cx="19" cy="7" rx="3.5" ry="2.5" fill="{C['cockpit']}" opacity=".85"/>
      <ellipse cx="19" cy="7" rx="2" ry="1.5" fill="{C['laser']}" opacity=".3"/>

      <!-- Wing details -->
      <line x1="8" y1="7" x2="20" y2="1" stroke="{C['ship2']}" stroke-width="1"/>
      <line x1="8" y1="7" x2="20" y2="13" stroke="{C['ship2']}" stroke-width="1"/>

      <!-- Top/bottom fins -->
      <polygon points="6,2 12,2 10,0" fill="{C['ship2']}" opacity=".7"/>
      <polygon points="6,12 12,12 10,14" fill="{C['ship2']}" opacity=".7"/>

      <!-- Gun barrel (front) -->
      <rect x="32" y="5.5" width="5" height="3" rx="1" fill="#00ffcc" opacity=".75"/>

      <!-- Engine thrust -->
      <g class="thrust">
        <polygon points="-10,3 0,5.5 0,8.5 -10,11" fill="{C['thrust1']}" opacity=".8"/>
        <polygon points="-6,4 0,6 0,8 -6,10" fill="{C['thrust2']}" opacity=".6"/>
        <polygon points="-3,5 0,6.5 0,7.5 -3,9" fill="{C['boom1']}" opacity=".3"/>
      </g>

    </g>
  </g>
</g>''')

    svg.append('\n</svg>')
    return '\n'.join(svg)


# ── Main ────────────────────────────────────────────────

def main():
    username = os.environ.get("GITHUB_USERNAME", "cjgpedroso-coder")
    token = os.environ.get("GITHUB_TOKEN", "")
    output_dir = os.environ.get("OUTPUT_DIR", "dist")
    os.makedirs(output_dir, exist_ok=True)

    if token:
        print(f"🚀 Fetching contributions for {username}…")
        try:
            grid = fetch_contributions(username, token)
            print(f"✅ Loaded {len(grid)} weeks")
        except Exception as e:
            print(f"⚠️  API error ({e}). Using demo data.")
            grid = demo_grid()
    else:
        print("⚠️  No GITHUB_TOKEN — using demo data.")
        grid = demo_grid()

    print("🎨 Generating spaceship animation v2…")
    svg_str = build_svg(grid)

    for name in ("github-spaceship-dark.svg", "github-spaceship.svg"):
        path = os.path.join(output_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg_str)
        print(f"✅ {path} ({len(svg_str):,} bytes)")

    print("🚀 Done!")


if __name__ == "__main__":
    main()

