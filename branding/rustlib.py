#!/usr/bin/env python3
"""Shared corroded-metal SVG material for RusticEngine branding.
"""
import math, sys



def ramp(*vals):
    return " ".join(f"{v:.3f}" for v in vals)


def corrosion(fid, seed, R, G, B, flake=0.0, pits=1.0, streaks=False, rough=3.0, bump=5.0, blur=2.2):
    """A filter that paints the shape's silhouette with mottled oxidation.
    R/G/B: colour ramps (dark pits -> orange rust -> pale ochre) indexed by low-frequency noise."""
    streak = f"""
    <feTurbulence type="fractalNoise" baseFrequency="0.13 0.011" numOctaves="3" seed="{seed + 3}" result="st"/>
    <feColorMatrix in="st" type="matrix"
      values="0 0 0 0 0.34  0 0 0 0 0.14  0 0 0 0 0.06  3.4 0 0 0 -2.05" result="streak"/>""" if streaks else ""
    return f"""
  <filter id="{fid}" filterUnits="userSpaceOnUse" x="0" y="0" width="256" height="256" color-interpolation-filters="sRGB">
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
    <feGaussianBlur in="SourceAlpha" stdDeviation="{blur}" result="blur"/>
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


