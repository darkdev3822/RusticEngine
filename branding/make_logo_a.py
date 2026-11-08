#!/usr/bin/env python3
"""RusticEngine logo A ("Crank") with a naturalistic corroded-metal finish.
Usage: make_logo_a.py OUT.svg"""
import math, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "logo-a-crank-rust.svg"


def ramp(*vals):
    return " ".join(f"{v:.3f}" for v in vals)


def corrosion(fid, seed, R, G, B, flake=0.0, pits=1.0, streaks=False, rough=3.0, bump=5.0):
    """A filter that paints the shape's silhouette with mottled oxidation.
    R/G/B: colour ramps (dark pits -> orange rust -> pale ochre) indexed by low-frequency noise."""
    streak = f"""
    <feTurbulence type="fractalNoise" baseFrequency="0.13 0.011" numOctaves="3" seed="{seed + 3}" result="st"/>
    <feColorMatrix in="st" type="matrix"
      values="0 0 0 0 0.34  0 0 0 0 0.14  0 0 0 0 0.06  3.4 0 0 0 -2.05" result="streak"/>""" if streaks else ""
    return f"""
  <filter id="{fid}" x="-8%" y="-8%" width="116%" height="116%" color-interpolation-filters="sRGB">
    <feTurbulence type="fractalNoise" baseFrequency="0.022" numOctaves="5" seed="{seed}" result="lo"/>
    <feColorMatrix in="lo" type="matrix" result="lum"
      values="2.3 0 0 0 -0.65  2.3 0 0 0 -0.65  2.3 0 0 0 -0.65  0 0 0 0 1"/>
    <feComponentTransfer in="lum" result="col">
      <feFuncR type="table" tableValues="{ramp(*R)}"/>
      <feFuncG type="table" tableValues="{ramp(*G)}"/>
      <feFuncB type="table" tableValues="{ramp(*B)}"/>
      <feFuncA type="linear" slope="0" intercept="1"/>
    </feComponentTransfer>{streak}
    <feTurbulence type="fractalNoise" baseFrequency="0.09" numOctaves="3" seed="{seed + 1}" result="fl"/>
    <feColorMatrix in="fl" type="matrix"
      values="0 0 0 0 0.40  0 0 0 0 0.36  0 0 0 0 0.33  {7 * flake:.2f} 0 0 0 {-4.3 * flake:.2f}" result="flake"/>
    <feTurbulence type="fractalNoise" baseFrequency="0.55" numOctaves="2" seed="{seed + 2}" result="hi"/>
    <feColorMatrix in="hi" type="matrix"
      values="0 0 0 0 0.06  0 0 0 0 0.03  0 0 0 0 0.02  {4.2 * pits:.2f} 0 0 0 {-2.45 * pits:.2f}" result="pit"/>
    <feMerge result="tex">
      <feMergeNode in="col"/>{'<feMergeNode in="streak"/>' if streaks else ''}
      <feMergeNode in="flake"/><feMergeNode in="pit"/>
    </feMerge>
    <feGaussianBlur in="SourceAlpha" stdDeviation="2.2" result="blur"/>
    <feComposite in="blur" in2="hi" operator="arithmetic" k2="1" k3="0.22" result="height"/>
    <feDiffuseLighting in="height" surfaceScale="{bump}" diffuseConstant="1.1" lighting-color="#fff4e6" result="light">
      <feDistantLight azimuth="235" elevation="50"/>
    </feDiffuseLighting>
    <feComposite in="tex" in2="light" operator="arithmetic" k1="1.12" result="lit"/>
    <feSpecularLighting in="height" surfaceScale="{bump}" specularConstant=".35" specularExponent="18"
      lighting-color="#ffd9a8" result="spec">
      <feDistantLight azimuth="235" elevation="55"/>
    </feSpecularLighting>
    <feComposite in="spec" in2="SourceAlpha" operator="in" result="spec2"/>
    <feComposite in="lit" in2="spec2" operator="arithmetic" k2="1" k3="0.5" result="shine"/>
    <feDisplacementMap in="SourceAlpha" in2="lo" scale="{rough}" xChannelSelector="R" yChannelSelector="G" result="edge"/>
    <feComposite in="shine" in2="edge" operator="in"/>
  </filter>"""


# colour ramps: deep oxide -> orange rust -> pale ochre (+ a dark return so it mottles)
RUST = dict(R=(0.15, 0.26, 0.40, 0.57, 0.71, 0.50, 0.30), G=(0.075, 0.105, 0.165, 0.26, 0.37, 0.23, 0.13),
            B=(0.05, 0.05, 0.065, 0.10, 0.16, 0.10, 0.07))
IRON = dict(R=(0.13, 0.20, 0.29, 0.40, 0.31, 0.22), G=(0.12, 0.16, 0.19, 0.23, 0.20, 0.16),
            B=(0.11, 0.13, 0.14, 0.15, 0.15, 0.13))
PLATE = dict(R=(0.06, 0.09, 0.13, 0.17, 0.12), G=(0.055, 0.075, 0.095, 0.11, 0.09),
             B=(0.05, 0.065, 0.08, 0.09, 0.075))

FILTERS = (corrosion("rust", 11, flake=1.0, pits=0.55, rough=3.5, **RUST)
           + corrosion("rust2", 23, flake=0.9, pits=0.55, rough=2.5, **RUST)
           + corrosion("iron", 37, flake=0.0, pits=0.8, rough=2.0, bump=4, **IRON)
           + corrosion("plate", 51, flake=0.0, pits=0.6, streaks=True, rough=0, bump=2, **PLATE))


def gear(cx, cy, r_out, r_in, teeth, rot=0.0):
    pts, step = [], 2 * math.pi / teeth
    for i in range(teeth):
        a = rot + i * step
        for frac, r in ((0.0, r_in), (0.12, r_out), (0.42, r_out), (0.54, r_in)):
            t = a + frac * step
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts) + " Z"


def ring(cx, cy, r_out, r_in):
    c = lambda r: f"M{cx + r},{cy} A{r},{r} 0 1,0 {cx - r},{cy} A{r},{r} 0 1,0 {cx + r},{cy} Z"
    return c(r_out) + " " + c(r_in)


def rivets(cx, cy, r, n, size, rot=0.0):
    out = []
    for i in range(n):
        a = rot + i * 2 * math.pi / n
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{size + 1}" fill="#0e0a08" opacity=".8"/>'
                   f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{size}" fill="#6a3a22"/>'
                   f'<circle cx="{x - size * .35:.2f}" cy="{y - size * .35:.2f}" r="{size * .4:.2f}" fill="#c98a5a" opacity=".55"/>')
    return "".join(out)


GX, GY, PX, PY = 100, 152, 172, 84
DARK = "#0f0b09"
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
<defs>{FILTERS}
  <filter id="drop" x="-20%" y="-20%" width="140%" height="140%">
    <feDropShadow dx="1.5" dy="3" stdDeviation="2.5" flood-color="#000" flood-opacity=".6"/>
  </filter>
  <radialGradient id="vignette" cx="50%" cy="45%" r="55%">
    <stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".55"/>
  </radialGradient>
</defs>
<!-- badge: corroded copper rim around a blackened, rust-streaked plate -->
<g filter="url(#drop)">
  <circle cx="128" cy="128" r="121" fill="{DARK}"/>
  <path fill-rule="evenodd" fill="#000" filter="url(#rust)" d="{ring(128, 128, 120, 108)}"/>
  <circle cx="128" cy="128" r="107" fill="#000" filter="url(#plate)"/>
  <circle cx="128" cy="128" r="107" fill="url(#vignette)"/>
  {rivets(128, 128, 114, 12, 2.3, math.pi / 12)}
</g>
<!-- connecting rod -->
<g filter="url(#drop)">
  <path d="M{GX},{GY} L{PX},{PY}" stroke="{DARK}" stroke-width="31" stroke-linecap="round"/>
  <path d="M{GX},{GY} L{PX},{PY}" stroke="#000" stroke-width="23" stroke-linecap="round" filter="url(#iron)"/>
</g>
<!-- drive gear -->
<g filter="url(#drop)">
  <path d="{gear(GX, GY, 52, 42, 10, 0.1)}" fill="{DARK}"/>
  <path d="{gear(GX, GY, 50, 40, 10, 0.1)}" fill="#000" filter="url(#rust2)"/>
  <circle cx="{GX}" cy="{GY}" r="27" fill="{DARK}"/>
  <path fill-rule="evenodd" fill="#000" filter="url(#iron)" d="{ring(GX, GY, 24, 9)}"/>
  <circle cx="{GX}" cy="{GY}" r="8" fill="{DARK}"/>
  {rivets(GX, GY, 31, 6, 2.4, 0.3)}
</g>
<!-- crank pin -->
<g filter="url(#drop)">
  <circle cx="{PX}" cy="{PY}" r="28" fill="{DARK}"/>
  <circle cx="{PX}" cy="{PY}" r="26" fill="#000" filter="url(#rust)"/>
  <circle cx="{PX}" cy="{PY}" r="12" fill="{DARK}"/>
  <circle cx="{PX}" cy="{PY}" r="10" fill="#000" filter="url(#iron)"/>
</g>
</svg>"""

open(OUT, "w").write(svg)
print("ok")
