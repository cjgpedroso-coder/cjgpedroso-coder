#!/usr/bin/env python3
"""
🚀 GitHub Spaceship Contribution Animation Generator
Generates an animated SVG of a spaceship destroying GitHub contribution squares.
"""

import os
import sys
import json
import random
import urllib.request

GITHUB_API = "https://api.github.com/graphql"

# === COLOR SCHEME ===
COLORS = {
    "bg": "#0d1117",
    "empty": "#161b22",
    "level1": "#0e4429",
    "level2": "#006d32",
    "level3": "#26a641",
    "level4": "#39d353",
    "ship": "#00ff88",
    "laser": "#00d4ff",
    "explosion": "#ff6600",
    "explosion_flash": "#ffffff",
    "text": "#8b949e",
    "star": "#ffffff",
    "thrust1": "#ff6600",
    "thrust2": "#ffaa00",
}

# === GRID LAYOUT ===
CELL_SIZE = 10
CELL_GAP = 3
CELL_STEP = CELL_SIZE + CELL_GAP  # 13px

GRID_COLS = 52  # weeks
GRID_ROWS = 7   # days

MARGIN_TOP = 55
MARGIN_LEFT = 35
MARGIN_RIGHT = 35
MARGIN_BOTTOM = 20

GRID_WIDTH = GRID_COLS * CELL_STEP - CELL_GAP
GRID_HEIGHT = GRID_ROWS * CELL_STEP - CELL_GAP

SVG_WIDTH = MARGIN_LEFT + GRID_WIDTH + MARGIN_RIGHT
SVG_HEIGHT = MARGIN_TOP + GRID_HEIGHT + MARGIN_BOTTOM

# === ANIMATION TIMING (seconds) ===
SHIP_CROSS_TIME = 12
TOTAL_CYCLE = 20


def get_level(count):
    if count == 0: return 0
    if count <= 3: return 1
    if count <= 6: return 2
    if count <= 9: return 3
    return 4


def level_color(level):
    return [COLORS["empty"], COLORS["level1"], COLORS["level2"],
            COLORS["level3"], COLORS["level4"]][level]


# ── GitHub API ──────────────────────────────────────────────

def fetch_contributions(username, token):
    """Fetch contribution calendar via GitHub GraphQL API."""
    query = """query($username:String!){
        user(login:$username){
            contributionsCollection{
                contributionCalendar{
                    weeks{
                        contributionDays{
                            contributionCount
                            date
                            weekday
                        }
                    }
                }
            }
        }
    }"""
    payload = json.dumps({"query": query, "variables": {"username": username}}).encode()
    req = urllib.request.Request(GITHUB_API, data=payload, headers={
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())

    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    grid = []
    for week in weeks:
        col = []
        for day in week["contributionDays"]:
            col.append({"count": day["contributionCount"],
                         "level": get_level(day["contributionCount"]),
                         "date": day["date"]})
        grid.append(col)

    # Pad / trim to exactly 52 columns
    while len(grid) < GRID_COLS:
        grid.append([{"count": 0, "level": 0, "date": ""} for _ in range(7)])
    return grid[:GRID_COLS]


def demo_grid():
    """Generate a realistic-looking demo grid (no API needed)."""
    random.seed(2024)
    grid = []
    for w in range(52):
        col = []
        for d in range(7):
            if d >= 5:
                c = random.choices([0,1,2,3], weights=[55,25,12,8])[0]
            else:
                c = random.choices([0,1,2,3,5,8,12], weights=[25,20,18,15,12,7,3])[0]
            col.append({"count": c, "level": get_level(c), "date": ""})
        grid.append(col)
    return grid


# ── SVG Generation ──────────────────────────────────────────

def generate_svg(grid):
    """Build the full animated SVG string."""

    # Identify target squares (level > 0)
    targets_by_col = {}
    for ci, week in enumerate(grid):
        for ri, day in enumerate(week):
            if day["level"] > 0:
                targets_by_col.setdefault(ci, []).append((ri, day["level"]))

    parts = []

    # ── SVG open + defs ──
    parts.append(f'''<svg xmlns="http://www.w3.org/2000/svg"
     width="{SVG_WIDTH}" height="{SVG_HEIGHT}"
     viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}">
<defs>
  <filter id="glow">
    <feGaussianBlur stdDeviation="2" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="laser-glow">
    <feGaussianBlur stdDeviation="1.5" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="boom">
    <feGaussianBlur stdDeviation="3" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>''')

    # ── CSS ──
    ship_start = MARGIN_LEFT - 30
    ship_end = MARGIN_LEFT + GRID_WIDTH + 15
    cross_pct = SHIP_CROSS_TIME / TOTAL_CYCLE * 100
    rebuild_start_pct = 72  # % of cycle where rebuild begins
    rebuild_span_pct = 20   # % of cycle for full rebuild

    css = [f'''
<style>
  .bg {{ fill:{COLORS["bg"]}; }}

  /* ── Ship ── */
  @keyframes ship-fly {{
    0%   {{ transform: translateX({ship_start}px); }}
    {cross_pct:.0f}% {{ transform: translateX({ship_end}px); }}
    100% {{ transform: translateX({ship_end}px); }}
  }}
  .ship {{ animation: ship-fly {TOTAL_CYCLE}s linear infinite; }}

  @keyframes thrust {{
    0%,100% {{ opacity:.9; }}
    50%     {{ opacity:.35; }}
  }}
  .thrust {{ animation: thrust .08s linear infinite; }}

  @keyframes twinkle {{
    0%,100% {{ opacity:.2; }}
    50%     {{ opacity:1; }}
  }}
''']

    # Per-square destroy / rebuild keyframes
    for ci in range(GRID_COLS):
        col_time_s = (ci / GRID_COLS) * SHIP_CROSS_TIME
        hit = col_time_s / TOTAL_CYCLE * 100          # % when laser hits
        flash_end = min(hit + 1.0, 99)
        dead = min(hit + 2.5, 99)
        rb_start = rebuild_start_pct + (ci / GRID_COLS) * rebuild_span_pct
        rb_end = min(rb_start + 3, 99)

        for ri, lv in targets_by_col.get(ci, []):
            sid = f"s{ci}_{ri}"
            clr = level_color(lv)
            css.append(f'''  @keyframes d-{sid} {{
    0%,{hit:.1f}% {{ fill:{clr}; transform:scale(1); }}
    {min(hit+.4,99):.1f}% {{ fill:{COLORS["explosion_flash"]}; transform:scale(1.4); }}
    {flash_end:.1f}% {{ fill:{COLORS["explosion"]}; transform:scale(.6); }}
    {dead:.1f}% {{ fill:{COLORS["empty"]}; transform:scale(1); }}
    {rb_start:.1f}% {{ fill:{COLORS["empty"]}; transform:scale(1); }}
    {rb_end:.1f}% {{ fill:{clr}; transform:scale(1.15); }}
    {min(rb_end+1,99.5):.1f}% {{ fill:{clr}; transform:scale(1); }}
    100% {{ fill:{clr}; transform:scale(1); }}
  }}
  .{sid} {{ animation:d-{sid} {TOTAL_CYCLE}s linear infinite;
            transform-origin:center; transform-box:fill-box; }}
''')

    # Laser keyframes per column (only cols with targets)
    for ci in targets_by_col:
        col_time_s = (ci / GRID_COLS) * SHIP_CROSS_TIME
        hit = col_time_s / TOTAL_CYCLE * 100
        css.append(f'''  @keyframes l-{ci} {{
    0%,{max(hit-.4,0):.1f}% {{ opacity:0; }}
    {hit:.1f}% {{ opacity:1; }}
    {min(hit+1.2,99):.1f}% {{ opacity:0; }}
    100% {{ opacity:0; }}
  }}
  .l-{ci} {{ animation:l-{ci} {TOTAL_CYCLE}s linear infinite; }}
''')

    css.append('</style>')
    parts.append('\n'.join(css))

    # ── Background ──
    parts.append(f'<rect class="bg" width="{SVG_WIDTH}" height="{SVG_HEIGHT}" rx="6"/>')

    # ── Stars ──
    random.seed(42)
    for _ in range(35):
        sx, sy = random.randint(4, SVG_WIDTH-4), random.randint(4, SVG_HEIGHT-4)
        sr = random.uniform(.3, .9)
        dur = random.uniform(1.5, 3.5)
        dl = random.uniform(0, 3)
        parts.append(
            f'<circle cx="{sx}" cy="{sy}" r="{sr}" fill="{COLORS["star"]}" '
            f'opacity=".4" style="animation:twinkle {dur:.1f}s ease-in-out {dl:.1f}s infinite;"/>')

    # ── Contribution Grid ──
    for ci, week in enumerate(grid):
        for ri, day in enumerate(week):
            x = MARGIN_LEFT + ci * CELL_STEP
            y = MARGIN_TOP + ri * CELL_STEP
            clr = level_color(day["level"])
            if day["level"] > 0:
                sid = f"s{ci}_{ri}"
                parts.append(
                    f'<rect class="{sid}" x="{x}" y="{y}" '
                    f'width="{CELL_SIZE}" height="{CELL_SIZE}" rx="2" fill="{clr}"/>')
            else:
                parts.append(
                    f'<rect x="{x}" y="{y}" '
                    f'width="{CELL_SIZE}" height="{CELL_SIZE}" rx="2" fill="{clr}"/>')

    # ── Laser Beams ──
    for ci in targets_by_col:
        lx = MARGIN_LEFT + ci * CELL_STEP + CELL_SIZE // 2
        parts.append(
            f'<line class="l-{ci}" x1="{lx}" y1="{MARGIN_TOP - 12}" '
            f'x2="{lx}" y2="{MARGIN_TOP + GRID_HEIGHT + 2}" '
            f'stroke="{COLORS["laser"]}" stroke-width="2" '
            f'filter="url(#laser-glow)" opacity="0"/>')

    # ── Spaceship ──
    sy = MARGIN_TOP - 28  # ship center Y
    parts.append(f'''
<!-- SPACESHIP -->
<g class="ship" filter="url(#glow)">
  <!-- body -->
  <polygon points="0,{sy+7} 24,{sy} 24,{sy+14}" fill="{COLORS["ship"]}"/>
  <!-- cockpit -->
  <ellipse cx="20" cy="{sy+7}" rx="3" ry="2.5" fill="#fff" opacity=".85"/>
  <!-- wing lines -->
  <line x1="6" y1="{sy+7}" x2="17" y2="{sy+2}" stroke="#00cc66" stroke-width=".8"/>
  <line x1="6" y1="{sy+7}" x2="17" y2="{sy+12}" stroke="#00cc66" stroke-width=".8"/>
  <!-- gun tip -->
  <rect x="24" y="{sy+5}" width="4" height="4" rx="1" fill="#00ffaa" opacity=".7"/>
  <!-- thrust flames -->
  <polygon class="thrust" points="-9,{sy+4} 0,{sy+7} -9,{sy+10}" fill="{COLORS["thrust1"]}" opacity=".85"/>
  <polygon class="thrust" points="-5,{sy+5} 0,{sy+7} -5,{sy+9}" fill="{COLORS["thrust2"]}" opacity=".6"/>
</g>''')

    parts.append('\n</svg>')
    return '\n'.join(parts)


# ── Main ────────────────────────────────────────────────────

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
            print(f"⚠️  API error ({e}). Falling back to demo data.")
            grid = demo_grid()
    else:
        print("⚠️  No GITHUB_TOKEN — using demo data.")
        grid = demo_grid()

    print("🎨 Generating spaceship animation…")
    svg = generate_svg(grid)

    for name in ("github-spaceship-dark.svg", "github-spaceship.svg"):
        path = os.path.join(output_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"✅ {path}")

    print("🚀 Done!")


if __name__ == "__main__":
    main()
