#!/usr/bin/env python3
"""Generate RusticEngine logo concepts (SVG). Usage: make_logos.py OUTDIR"""
import math, os, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "."

DEFS = """
<defs>
  <radialGradient id="badge" cx="40%" cy="35%" r="75%">
    <stop offset="0" stop-color="#3a302b"/><stop offset="1" stop-color="#16110f"/>
  </radialGradient>
  <linearGradient id="rust" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#e39a52"/><stop offset=".45" stop-color="#b8541f"/>
    <stop offset="1" stop-color="#6e2a10"/>
  </linearGradient>
  <linearGradient id="iron" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#8a8079"/><stop offset=".5" stop-color="#4d4540"/>
    <stop offset="1" stop-color="#2a2421"/>
  </linearGradient>
  <linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#d98a45"/><stop offset="1" stop-color="#7a3214"/>
  </linearGradient>
  <filter id="grime" x="-10%" y="-10%" width="120%" height="120%">
    <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" seed="7" result="n"/>
    <feColorMatrix in="n" type="matrix"
      values="0 0 0 0 0.16  0 0 0 0 0.09  0 0 0 0 0.05  0 0 0 -2.6 1.45" result="spots"/>
    <feComposite in="spots" in2="SourceGraphic" operator="in" result="s"/>
    <feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="s"/></feMerge>
  </filter>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
    <feDropShadow dx="0" dy="3" stdDeviation="3" flood-color="#000" flood-opacity=".55"/>
  </filter>
</defs>"""


def gear(cx, cy, r_out, r_in, teeth, hole=0.0, rot=0.0):
    """Closed path for a gear (trapezoid teeth), optional centre hole (evenodd)."""
    pts = []
    step = 2 * math.pi / teeth
    for i in range(teeth):
        a = rot + i * step
        for frac, r in ((0.0, r_in), (0.12, r_out), (0.42, r_out), (0.54, r_in)):
            t = a + frac * step
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    d = "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts) + " Z"
    if hole:
        d += f" M{cx + hole},{cy} A{hole},{hole} 0 1,0 {cx - hole},{cy} A{hole},{hole} 0 1,0 {cx + hole},{cy} Z"
    return d


def bolts(cx, cy, r, n, size, rot=0.0, fill="#2a2421"):
    return "".join(
        f'<circle cx="{cx + r * math.cos(rot + i * 2 * math.pi / n):.2f}" '
        f'cy="{cy + r * math.sin(rot + i * 2 * math.pi / n):.2f}" r="{size}" fill="{fill}"/>'
        for i in range(n))


def badge(inner):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">{DEFS}
<g filter="url(#shadow)">
  <circle cx="128" cy="128" r="120" fill="url(#ring)"/>
  <circle cx="128" cy="128" r="110" fill="url(#badge)"/>
  {bolts(128, 128, 115, 12, 2.2, math.pi / 12, "#5a240e")}
</g>
<g filter="url(#grime)">{inner}</g>
</svg>"""


# A: "Crank" - a gear driving a connecting rod to a small pivot (piston linkage)
def crank():
    g = gear(100, 152, 50, 40, 10, hole=0, rot=0.1)
    return badge(f"""
  <path d="M100,152 L172,84" stroke="#1a1411" stroke-width="30" stroke-linecap="round"/>
  <path d="M100,152 L172,84" stroke="url(#iron)" stroke-width="22" stroke-linecap="round"/>
  <path fill="url(#rust)" fill-rule="evenodd" d="{g}"/>
  <circle cx="100" cy="152" r="26" fill="#1a1411"/>
  <circle cx="100" cy="152" r="18" fill="url(#rust)"/>
  <circle cx="100" cy="152" r="7" fill="#1a1411"/>
  <circle cx="172" cy="84" r="27" fill="#1a1411"/>
  <circle cx="172" cy="84" r="21" fill="url(#rust)"/>
  <circle cx="172" cy="84" r="9" fill="url(#iron)"/>
  {bolts(100, 152, 30, 6, 2.6, 0.3)}""")


# B: "Pipe Gear" - a cog with a flanged steam pipe running through it, venting steam
def pipe_gear():
    g = gear(128, 128, 82, 68, 12, hole=30, rot=0.13)
    flange = lambda x: (f'<rect x="{x - 9}" y="98" width="18" height="60" rx="3" fill="url(#rust)" stroke="#1a1411" stroke-width="3"/>'
                        f'<circle cx="{x}" cy="106" r="2.6" fill="#1a1411"/><circle cx="{x}" cy="150" r="2.6" fill="#1a1411"/>')
    return badge(f"""
  <path fill="url(#rust)" fill-rule="evenodd" stroke="#1a1411" stroke-width="3" d="{g}"/>
  {bolts(128, 128, 50, 8, 3)}
  <rect x="36" y="110" width="184" height="36" fill="url(#iron)" stroke="#1a1411" stroke-width="3"/>
  <rect x="36" y="114" width="184" height="6" fill="#a39a92" opacity=".35"/>
  {flange(58)}{flange(198)}
  <circle cx="128" cy="128" r="20" fill="url(#rust)" stroke="#1a1411" stroke-width="3"/>
  <circle cx="128" cy="128" r="7" fill="#1a1411"/>
  <path d="M214,96 q10,-14 0,-26 q-10,-12 2,-26" fill="none" stroke="#e8d4a2" stroke-width="5" stroke-linecap="round" opacity=".55"/>
  <path d="M228,100 q8,-10 0,-20" fill="none" stroke="#e8d4a2" stroke-width="4" stroke-linecap="round" opacity=".35"/>""")


# C: "Valve" - a factory handwheel with an R hub
def valve():
    spokes = "".join(
        f'<path d="M128,128 L{128 + 80 * math.cos(a):.1f},{128 + 80 * math.sin(a):.1f}" stroke="#1a1411" stroke-width="20" stroke-linecap="round"/>'
        f'<path d="M128,128 L{128 + 80 * math.cos(a):.1f},{128 + 80 * math.sin(a):.1f}" stroke="url(#iron)" stroke-width="13" stroke-linecap="round"/>'
        for a in (math.pi / 4 + i * math.pi / 2 for i in range(4)))
    grips = "".join(
        f'<circle cx="{128 + 84 * math.cos(a):.1f}" cy="{128 + 84 * math.sin(a):.1f}" r="5" fill="#5a240e"/>'
        for a in (i * math.pi / 8 for i in range(16)))
    return badge(f"""
  {spokes}
  <circle cx="128" cy="128" r="84" fill="none" stroke="#1a1411" stroke-width="24"/>
  <circle cx="128" cy="128" r="84" fill="none" stroke="url(#rust)" stroke-width="17"/>
  {grips}
  <circle cx="128" cy="128" r="36" fill="#1a1411"/>
  <circle cx="128" cy="128" r="31" fill="url(#rust)"/>
  <text x="128" y="142" text-anchor="middle" font-family="serif" font-weight="bold" font-size="42" fill="#1a1411">R</text>""")


os.makedirs(OUT, exist_ok=True)
for name, fn in (("a-crank", crank), ("b-pipe-gear", pipe_gear), ("c-valve", valve)):
    with open(os.path.join(OUT, f"logo-{name}.svg"), "w") as f:
        f.write(fn())
print("ok")
