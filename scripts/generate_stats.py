#!/usr/bin/env python3
"""
📊 GitHub Stats Generator — Streak Stats + Activity Graph
Uses PAT to include private contributions.
Outputs SVGs matching the original visual style.
"""

import os, json, urllib.request
from datetime import datetime, timedelta

GITHUB_API = "https://api.github.com/graphql"

# Colors matching the README theme
BG = "#0D1117"
GREEN = "#00ff88"
GREEN_DIM = "#00cc66"
WHITE = "#ffffff"
GRAY = "#8b949e"
GRAY_LIGHT = "#9F9F9F"
FIRE_COLOR = "#00E7FF"


def fetch_contributions(username, token):
    """Fetch contribution data from GitHub GraphQL API."""
    q = """query($u:String!){user(login:$u){
        contributionsCollection{
            contributionCalendar{
                totalContributions
                weeks{contributionDays{
                    contributionCount date weekday
                }}
            }
        }
    }}"""
    p = json.dumps({"query": q, "variables": {"u": username}}).encode()
    req = urllib.request.Request(GITHUB_API, data=p, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode())
    
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    total = cal["totalContributions"]
    
    # Flatten all days
    days = []
    for w in cal["weeks"]:
        for d in w["contributionDays"]:
            days.append({
                "date": d["date"],
                "count": d["contributionCount"]
            })
    
    return total, days


def calc_streaks(days):
    """Calculate current and longest streaks."""
    current_streak = 0
    current_start = None
    current_end = None
    longest_streak = 0
    longest_start = None
    longest_end = None
    
    # Sort days by date
    sorted_days = sorted(days, key=lambda d: d["date"])
    
    streak = 0
    streak_start = None
    
    for day in sorted_days:
        if day["count"] > 0:
            if streak == 0:
                streak_start = day["date"]
            streak += 1
        else:
            if streak > longest_streak:
                longest_streak = streak
                longest_start = streak_start
                longest_end = sorted_days[sorted_days.index(day) - 1]["date"] if sorted_days.index(day) > 0 else streak_start
            streak = 0
            streak_start = None
    
    # Check if current streak is at the end
    if streak > 0:
        current_streak = streak
        current_start = streak_start
        current_end = sorted_days[-1]["date"]
        if streak > longest_streak:
            longest_streak = streak
            longest_start = streak_start
            longest_end = sorted_days[-1]["date"]
    
    # If longest was found before current
    if longest_start is None:
        longest_start = current_start
        longest_end = current_end
        longest_streak = current_streak
    
    # Find date range
    first_date = sorted_days[0]["date"] if sorted_days else ""
    
    return {
        "current": current_streak,
        "current_start": current_start,
        "current_end": current_end,
        "longest": longest_streak,
        "longest_start": longest_start,
        "longest_end": longest_end,
        "first_date": first_date,
    }


def fmt_date(date_str):
    """Format date string to 'Mon DD' format."""
    if not date_str:
        return ""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d.strftime("%b %d").replace(" 0", " ")
    except:
        return date_str


def fmt_date_range(start, end):
    """Format date range."""
    if not start or not end:
        return ""
    return f"{fmt_date(start)} - {fmt_date(end)}"


def generate_streak_svg(total, streaks, first_date):
    """Generate streak stats SVG matching the black-ice theme with green colors."""
    W, H = 495, 195
    
    current_date = fmt_date(streaks["current_end"]) if streaks["current_end"] else "Today"
    longest_range = fmt_date_range(streaks["longest_start"], streaks["longest_end"])
    total_range = f"{fmt_date(first_date)} - Present"
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
        style="isolation: isolate" viewBox="0 0 {W} {H}" width="{W}px" height="{H}px" direction="ltr">
    <style>
        @keyframes currstreak {{
            0% {{ font-size: 3px; opacity: 0.2; }}
            80% {{ font-size: 34px; opacity: 1; }}
            100% {{ font-size: 28px; opacity: 1; }}
        }}
        @keyframes fadein {{
            0% {{ opacity: 0; }}
            100% {{ opacity: 1; }}
        }}
    </style>
    <defs>
        <clipPath id="outer_rectangle">
            <rect width="{W}" height="{H}" rx="4.5"/>
        </clipPath>
        <mask id="mask_out_ring_behind_fire">
            <rect width="{W}" height="{H}" fill="white"/>
            <ellipse id="mask-ellipse" cx="247.5" cy="32" rx="13" ry="18" fill="black"/>
        </mask>
    </defs>
    <g clip-path="url(#outer_rectangle)">
        <g style="isolation: isolate">
            <rect stroke="#000000" stroke-opacity="0" fill="{BG}" rx="4.5" x="0.5" y="0.5" width="494" height="194"/>
        </g>
        <g style="isolation: isolate">
            <line x1="165" y1="28" x2="165" y2="170" vector-effect="non-scaling-stroke" stroke-width="1" stroke="{GRAY}" stroke-opacity="0.3" stroke-linejoin="miter" stroke-linecap="square" stroke-miterlimit="3"/>
            <line x1="330" y1="28" x2="330" y2="170" vector-effect="non-scaling-stroke" stroke-width="1" stroke="{GRAY}" stroke-opacity="0.3" stroke-linejoin="miter" stroke-linecap="square" stroke-miterlimit="3"/>
        </g>
        <!-- Total Contributions -->
        <g style="isolation: isolate">
            <g transform="translate(82.5, 48)">
                <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="{GREEN}" stroke="none" font-family="\'Segoe UI\', Ubuntu, sans-serif" font-weight="700" font-size="28px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.6s">
                    {total}
                </text>
            </g>
            <g transform="translate(82.5, 84)">
                <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="{GREEN}" stroke="none" font-family="\'Segoe UI\', Ubuntu, sans-serif" font-weight="400" font-size="14px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.7s">
                    Total Contributions
                </text>
            </g>
            <g transform="translate(82.5, 114)">
                <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="{GRAY_LIGHT}" stroke="none" font-family="\'Segoe UI\', Ubuntu, sans-serif" font-weight="400" font-size="12px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.8s">
                    {total_range}
                </text>
            </g>
        </g>
        <!-- Current Streak -->
        <g style="isolation: isolate">
            <g transform="translate(247.5, 108)">
                <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="{GREEN}" stroke="none" font-family="\'Segoe UI\', Ubuntu, sans-serif" font-weight="700" font-size="14px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.9s">
                    Current Streak
                </text>
            </g>
            <g transform="translate(247.5, 145)">
                <text x="0" y="21" stroke-width="0" text-anchor="middle" fill="{GRAY_LIGHT}" stroke="none" font-family="\'Segoe UI\', Ubuntu, sans-serif" font-weight="400" font-size="12px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.9s">
                    {current_date}
                </text>
            </g>
            <g mask="url(#mask_out_ring_behind_fire)">
                <circle cx="247.5" cy="71" r="40" fill="none" stroke="{GREEN}" stroke-width="5" style="opacity: 0; animation: fadein 0.5s linear forwards 0.4s"></circle>
            </g>
            <!-- Fire icon -->
            <g transform="translate(247.5, 19.5)" stroke-opacity="0" style="opacity: 0; animation: fadein 0.5s linear forwards 0.6s">
                <path d="M -12 -0.5 L 15 -0.5 L 15 23.5 L -12 23.5 L -12 -0.5 Z" fill="none"/>
                <path d="M 1.5 0.67 C 1.5 0.67 2.24 3.32 2.24 5.47 C 2.24 7.53 0.89 9.2 -1.17 9.2 C -3.23 9.2 -4.79 7.53 -4.79 5.47 L -4.76 5.11 C -6.78 7.51 -8 10.62 -8 13.99 C -8 18.41 -4.42 22 0 22 C 4.42 22 8 18.41 8 13.99 C 8 8.6 5.41 3.79 1.5 0.67 Z M -0.29 19 C -2.07 19 -3.51 17.6 -3.51 15.86 C -3.51 14.24 -2.46 13.1 -0.7 12.74 C 1.07 12.38 2.9 11.53 3.92 10.16 C 4.31 11.45 4.51 12.81 4.51 14.2 C 4.51 16.85 2.36 19 -0.29 19 Z" fill="{GREEN}" stroke-opacity="0"/>
            </g>
            <g transform="translate(247.5, 48)">
                <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="{WHITE}" stroke="none" font-family="\'Segoe UI\', Ubuntu, sans-serif" font-weight="700" font-size="28px" style="animation: currstreak 0.6s linear forwards">
                    {streaks["current"]}
                </text>
            </g>
        </g>
        <!-- Longest Streak -->
        <g style="isolation: isolate">
            <g transform="translate(412.5, 48)">
                <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="{GREEN}" stroke="none" font-family="\'Segoe UI\', Ubuntu, sans-serif" font-weight="700" font-size="28px" style="opacity: 0; animation: fadein 0.5s linear forwards 1.2s">
                    {streaks["longest"]}
                </text>
            </g>
            <g transform="translate(412.5, 84)">
                <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="{GREEN}" stroke="none" font-family="\'Segoe UI\', Ubuntu, sans-serif" font-weight="400" font-size="14px" style="opacity: 0; animation: fadein 0.5s linear forwards 1.3s">
                    Longest Streak
                </text>
            </g>
            <g transform="translate(412.5, 114)">
                <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="{GRAY_LIGHT}" stroke="none" font-family="\'Segoe UI\', Ubuntu, sans-serif" font-weight="400" font-size="12px" style="opacity: 0; animation: fadein 0.5s linear forwards 1.4s">
                    {longest_range}
                </text>
            </g>
        </g>
    </g>
</svg>'''
    return svg


def generate_activity_graph_svg(days, username):
    """Generate contribution activity graph SVG matching the green theme."""
    # Get last 31 days of data
    sorted_days = sorted(days, key=lambda d: d["date"])
    recent = sorted_days[-31:] if len(sorted_days) >= 31 else sorted_days
    
    W, H = 850, 320
    PADDING_LEFT = 55
    PADDING_RIGHT = 30
    PADDING_TOP = 60
    PADDING_BOTTOM = 50
    GRAPH_W = W - PADDING_LEFT - PADDING_RIGHT
    GRAPH_H = H - PADDING_TOP - PADDING_BOTTOM
    
    counts = [d["count"] for d in recent]
    max_count = max(counts) if counts else 1
    if max_count == 0:
        max_count = 1
    
    # Y-axis: round up max to nice number
    y_max = max_count + 1
    y_steps = min(y_max, 6)
    
    # Build points
    points = []
    dot_positions = []
    n = len(recent)
    for i, day in enumerate(recent):
        x = PADDING_LEFT + (i / max(n - 1, 1)) * GRAPH_W
        y = PADDING_TOP + GRAPH_H - (day["count"] / y_max) * GRAPH_H
        points.append(f"{x:.1f},{y:.1f}")
        dot_positions.append((x, y, day["count"], day["date"]))
    
    polyline = " ".join(points)
    
    # Area fill (polygon closing to bottom)
    area_points = points.copy()
    area_points.append(f"{PADDING_LEFT + GRAPH_W:.1f},{PADDING_TOP + GRAPH_H:.1f}")
    area_points.append(f"{PADDING_LEFT:.1f},{PADDING_TOP + GRAPH_H:.1f}")
    area_polygon = " ".join(area_points)
    
    # Grid lines
    grid_lines = []
    for i in range(y_steps + 1):
        y_val = (i / y_steps) * y_max
        y_pos = PADDING_TOP + GRAPH_H - (y_val / y_max) * GRAPH_H
        grid_lines.append(f'<line x1="{PADDING_LEFT}" y1="{y_pos:.1f}" x2="{W - PADDING_RIGHT}" y2="{y_pos:.1f}" stroke="{GRAY}" stroke-opacity="0.15" stroke-width="1"/>')
        grid_lines.append(f'<text x="{PADDING_LEFT - 10}" y="{y_pos + 4:.1f}" fill="{GRAY}" font-family="\'Segoe UI\', sans-serif" font-size="11" text-anchor="end">{int(y_val)}</text>')
    
    # X-axis labels (every ~5 days)
    x_labels = []
    step = max(1, n // 6)
    for i in range(0, n, step):
        day = recent[i]
        x = PADDING_LEFT + (i / max(n - 1, 1)) * GRAPH_W
        try:
            d = datetime.strptime(day["date"], "%Y-%m-%d")
            label = d.strftime("%b %d").replace(" 0", " ")
        except:
            label = day["date"][-5:]
        x_labels.append(f'<text x="{x:.1f}" y="{PADDING_TOP + GRAPH_H + 25}" fill="{GRAY}" font-family="\'Segoe UI\', sans-serif" font-size="11" text-anchor="middle">{label}</text>')
    
    # Dots
    dots = []
    for x, y, count, date in dot_positions:
        r = "4" if count > 0 else "3"
        opacity = "1" if count > 0 else "0.5"
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{GREEN}" opacity="{opacity}"/>')
    
    title = f"{username}'s Contribution Graph"
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
    <style>
        @keyframes drawLine {{
            0% {{ stroke-dashoffset: 2000; }}
            100% {{ stroke-dashoffset: 0; }}
        }}
        @keyframes fadeIn {{
            0% {{ opacity: 0; }}
            100% {{ opacity: 1; }}
        }}
    </style>
    <rect width="{W}" height="{H}" rx="6" fill="{BG}"/>
    
    <!-- Title -->
    <text x="{W/2}" y="35" fill="{GRAY}" font-family="\'Segoe UI\', sans-serif" font-size="14" font-weight="600" text-anchor="middle" style="opacity:0; animation: fadeIn 0.5s forwards 0.2s">{title}</text>
    
    <!-- Y-axis label -->
    <text x="15" y="{PADDING_TOP + GRAPH_H/2}" fill="{GRAY}" font-family="\'Segoe UI\', sans-serif" font-size="11" text-anchor="middle" transform="rotate(-90, 15, {PADDING_TOP + GRAPH_H/2})">Contributions</text>
    
    <!-- Grid -->
    {"".join(grid_lines)}
    
    <!-- X labels -->
    {"".join(x_labels)}
    
    <!-- X-axis label -->
    <text x="{W/2}" y="{H - 8}" fill="{GRAY}" font-family="\'Segoe UI\', sans-serif" font-size="11" text-anchor="middle">Days</text>
    
    <!-- Area fill -->
    <polygon points="{area_polygon}" fill="{GREEN}" opacity="0.1" style="opacity:0; animation: fadeIn 0.8s forwards 0.5s"/>
    
    <!-- Line -->
    <polyline points="{polyline}" fill="none" stroke="{GREEN}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" stroke-dasharray="2000" style="animation: drawLine 2s ease forwards"/>
    
    <!-- Dots -->
    <g style="opacity:0; animation: fadeIn 0.5s forwards 1.5s">
        {"".join(dots)}
    </g>
</svg>'''
    return svg


def main():
    username = os.environ.get("GITHUB_USERNAME", "cjgpedroso-coder")
    token = os.environ.get("GITHUB_TOKEN", "")
    out = os.environ.get("OUTPUT_DIR", "dist")
    os.makedirs(out, exist_ok=True)

    if not token:
        print("❌ No GITHUB_TOKEN — cannot generate stats")
        return

    print(f"📊 Fetching contributions for {username}...")
    try:
        total, days = fetch_contributions(username, token)
        print(f"✅ Total contributions: {total}")
        print(f"   Days of data: {len(days)}")
    except Exception as e:
        print(f"❌ API ERROR: {e}")
        return

    # Calculate streaks
    streaks = calc_streaks(days)
    first_date = days[0]["date"] if days else ""
    print(f"   Current streak: {streaks['current']}")
    print(f"   Longest streak: {streaks['longest']}")

    # Generate Streak Stats SVG
    print("🎨 Generating streak stats...")
    streak_svg = generate_streak_svg(total, streaks, first_date)
    streak_path = os.path.join(out, "streak-stats.svg")
    with open(streak_path, "w") as f:
        f.write(streak_svg)
    print(f"✅ {streak_path} ({len(streak_svg):,}b)")

    # Generate Activity Graph SVG
    print("📈 Generating activity graph...")
    graph_svg = generate_activity_graph_svg(days, username)
    graph_path = os.path.join(out, "activity-graph.svg")
    with open(graph_path, "w") as f:
        f.write(graph_svg)
    print(f"✅ {graph_path} ({len(graph_svg):,}b)")

    print("🚀 Stats generation complete!")


if __name__ == "__main__":
    main()
