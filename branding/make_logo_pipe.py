#!/usr/bin/env python3
"""RusticEngine logo: a corroded L-shaped (elbow) pipe with a rusted gear in its crook.
Transparent background. Usage: python3 make_logo_pipe.py OUT.svg"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rustlib import corrosion, gear, ring, rivets, RUST, IRON  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "logo-pipe-gear.svg"
DARK = "#0f0b09"

# darker, iron-heavy oxide for the pipe so it reads apart from the orange gear
PIPE = dict(R=(0.11, 0.17, 0.26, 0.37, 0.47, 0.30, 0.17), G=(0.09, 0.115, 0.15, 0.20, 0.255, 0.17, 0.10),
            B=(0.08, 0.085, 0.10, 0.12, 0.145, 0.10, 0.075))

FILTERS = (corrosion("pipe", 61, flake=0.6, pits=0.6, rough=2.0, bump=7, blur=9, **PIPE)
           + corrosion("rust", 11, flake=1.0, pits=0.55, rough=2.5, **RUST)
           + corrosion("iron", 37, flake=0.0, pits=0.8, rough=1.5, bump=4, **IRON))

# pipe centreline: down the left, round the elbow, out to the right
PIPE_D = "M60,34 L60,166 A34,34 0 0 0 94,200 L222,200"
W = 42

# gear sitting in the crook of the L, with lightening holes
GX, GY, RO, RI, TEETH = 152, 108, 64, 52, 11


def holes(cx, cy, r, n, size, rot):
    out = []
    for i in range(n):
        a = rot + i * 2 * math.pi / n
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        out.append(f"M{x + size:.2f},{y:.2f} A{size},{size} 0 1,0 {x - size:.2f},{y:.2f} "
                   f"A{size},{size} 0 1,0 {x + size:.2f},{y:.2f} Z")
    return " ".join(out)


def flange(x, y, w, h, bolts_xy):
    b = "".join(rivets(bx, by, 0, 1, 2.6) for bx, by in bolts_xy)
    return (f'<rect x="{x - 2}" y="{y - 2}" width="{w + 4}" height="{h + 4}" rx="4" fill="{DARK}"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="#000" filter="url(#rust)"/>{b}')


gear_d = gear(GX, GY, RO, RI, TEETH, 0.05) + " " + holes(GX, GY, 38, 5, 8.5, -math.pi / 2) + " " + \
    f"M{GX + 23},{GY} A23,23 0 1,0 {GX - 23},{GY} A23,23 0 1,0 {GX + 23},{GY} Z"
gear_outline = gear(GX, GY, RO + 2.2, RI + 2.2, TEETH, 0.05)

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
<defs>{FILTERS}
  <filter id="drop" x="-20%" y="-20%" width="140%" height="140%">
    <feDropShadow dx="1.5" dy="3" stdDeviation="2.5" flood-color="#000" flood-opacity=".5"/>
  </filter>
</defs>
<g filter="url(#drop)">
  <path d="{PIPE_D}" fill="none" stroke="{DARK}" stroke-width="{W + 6}"/>
  <path d="{PIPE_D}" fill="none" stroke="#000" stroke-width="{W}" filter="url(#pipe)"/>
  {flange(32, 22, 56, 18, [(41, 31), (79, 31)])}
  {flange(214, 174, 18, 52, [(223, 183), (223, 217)])}
</g>
<g filter="url(#drop)">
  <path d="{gear_outline} {holes(GX, GY, 38, 5, 6.3, -math.pi / 2)}" fill="{DARK}" fill-rule="evenodd"/>
  <path d="{gear_d}" fill="#000" fill-rule="evenodd" filter="url(#rust)"/>
  <circle cx="{GX}" cy="{GY}" r="25" fill="{DARK}"/>
  <path fill-rule="evenodd" fill="#000" filter="url(#iron)" d="{ring(GX, GY, 23, 8)}"/>
  <circle cx="{GX}" cy="{GY}" r="7" fill="{DARK}"/>
</g>
</svg>"""

open(OUT, "w").write(svg)
print("ok")
