#!/usr/bin/env python3
"""Collect the concepts behind 3D art from Wikipedia (CC BY-SA 4.0): meshes, normals, UVs, shaders,
baking, noise, terrain, fluids, cartography, plus real-world references for weapons, armour,
architecture and UI. Ember's Blender library uses them to explain WHY a technique works.

Output: corpus/art/concepts.jsonl  {"topic", "title", "url", "sections": {name: text}}
Usage: python3 crawl_art_concepts.py   (polite: one request at a time, retries on maxlag)
"""
import json, re, time, urllib.parse, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "corpus/art/concepts.jsonl"
UA = "RusticEngine-art-crawler/0.1 (open-source game engine research; non-commercial)"
API = "https://en.wikipedia.org/w/api.php"

TOPICS = {
    "mesh": "3D modeling|Polygon mesh|Polygonal modeling|Vertex (computer graphics)|Edge loop|Triangle mesh|Normal (geometry)|Vertex normal|"
            "Subdivision surface|Catmull–Clark subdivision surface|Box modeling|Digital sculpting|Retopology|Low poly|Level of detail (computer graphics)|"
            "Constructive solid geometry|Non-uniform rational B-spline|Bézier curve|Chamfer|Bevel|Geometry instancing|Procedural modeling|Manifold|Triangulation (geometry)",
    "texturing": "Texture mapping|UV mapping|Texture atlas|Texel (graphics)|Mipmap|Texture filtering|Normal mapping|Bump mapping|Displacement mapping|"
                 "Parallax mapping|Ambient occlusion|Lightmap|Procedural texture|Perlin noise|Simplex noise|Worley noise|Value noise|Gradient noise|"
                 "Brownian surface|Fractal|Seamless texture|Texture synthesis|Photogrammetry",
    "shading": "Shader|Physically based rendering|Bidirectional reflectance distribution function|Specular highlight|Fresnel equations|Subsurface scattering|"
               "Albedo|Diffuse reflection|Emission (electromagnetic radiation)|Gamma correction|SRGB|High-dynamic-range rendering|Image-based lighting|"
               "Global illumination|Ray tracing (graphics)|Rasterisation|Back-face culling|Alpha compositing|Toon shading|Cel shading|Rendering (computer graphics)",
    "animation": "Skeletal animation|Inverse kinematics|Morph target animation|Key frame|Inbetweening|Twelve basic principles of animation",
    "art": "Concept art|Model sheet|Multiview orthographic projection|Silhouette|Color theory|Color wheel|Complementary colors|Lightness|Aerial perspective|"
           "Rule of thirds|Texture (visual arts)|Weathering|Rust|Patina|Wood grain|Sprite (computer graphics)|Billboard (computer graphics)|Set dressing|Prop|Environmental storytelling",
    "terrain": "Heightmap|Fractal landscape|Diamond-square algorithm|Terrain rendering|Digital elevation model|Erosion|Drainage basin|Meander|River delta|"
               "L-system|Procedural generation|Particle system|Biome|Rain shadow|Köppen climate classification|Plate tectonics|Tree|Grass",
    "fluids": "Fluid simulation|Smoothed-particle hydrodynamics|Caustic (optics)|Refraction|Snell's law|Wind wave|Trochoidal wave|Sea foam|Lava|Pāhoehoe|Black-body radiation|Waterfall",
    "cartography": "Cartography|Map projection|Contour line|Terrain cartography|Hachure map|Topographic map|Raised-relief map|Compass rose|Cartouche (cartography)|"
                   "Fantasy map|Mappa mundi|Portolan chart|Coastline paradox|Worldbuilding|Map symbolization|Scale (map)",
    "architecture": "Medieval architecture|Romanesque architecture|Gothic architecture|Timber framing|Castle|Arch|Column|Buttress|Vault (architecture)|"
                    "Roof|Thatching|Masonry|Ashlar|Modular design",
    "weapons": "Sword|Longsword|Arming sword|Katana|Hilt|Fuller (weapon)|Crossguard|Pommel|Axe|Mace (bludgeon)|Spear|Bow and arrow|Crossbow|Staff (stick)",
    "armour": "Plate armour|Chain mail|Gambeson|Helmet|Pauldron|Gauntlet (glove)|Shield|Heater shield|Components of medieval armour|Lamellar armour|Brigandine",
    "ui": "Graphical user interface|Heads-up display (video games)|Icon (computing)|Skeuomorphism|Flat design|9-slice scaling|Typography|Kerning",
}
SKIP = re.compile(r"^(see also|references|external links|further reading|notes|bibliography|sources|citations|gallery|footnotes)$", re.I)


def get(params):
    params = {**params, "format": "json", "formatversion": "2", "maxlag": "5"}
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.load(r)
            if d.get("error", {}).get("code") == "maxlag":
                time.sleep(5); continue
            return d
        except Exception:
            time.sleep(2 + attempt * 3)
    return {}


def sections(text):
    out, name, buf = {}, "Intro", []
    for line in text.splitlines():
        m = re.match(r"^(=+)\s*(.+?)\s*=+$", line)
        if m:
            if buf: out[name] = "\n".join(buf).strip()
            name, buf = m.group(2), []
        else:
            buf.append(line)
    if buf: out[name] = "\n".join(buf).strip()
    return {k: re.sub(r"\n{3,}", "\n\n", v) for k, v in out.items() if v and not SKIP.match(k)}


def main():
    done = set()
    if OUT.exists():
        done = {json.loads(l)["query"] for l in OUT.read_text().splitlines() if l.strip()}
    with OUT.open("a") as f:
        for topic, titles in TOPICS.items():
            for t in titles.split("|"):
                if t in done: continue
                d = get({"action": "query", "prop": "extracts|info", "inprop": "url", "explaintext": "1",
                         "exsectionformat": "wiki", "redirects": "1", "titles": t})
                pages = d.get("query", {}).get("pages", [])
                if not pages or pages[0].get("missing") or not pages[0].get("extract"):
                    print("missing:", t); continue
                p = pages[0]
                f.write(json.dumps({"query": t, "topic": topic, "title": p["title"], "url": p.get("fullurl", ""),
                                    "sections": sections(p["extract"])}, ensure_ascii=False) + "\n")
                f.flush()
                print("ok:", topic, p["title"])
                time.sleep(1.0)


if __name__ == "__main__":
    main()
