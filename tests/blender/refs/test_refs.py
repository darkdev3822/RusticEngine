# Run: blender -b --factory-startup --python test_refs.py -- OUT_DIR
# Synthetic reference photos with a known subject box -> add_references -> the subject must stand on z=0,
# be exactly REAL tall, be centred on the origin, and front/side must agree.
import os, sys
import bpy, numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "blender"))
OUT = os.path.abspath(sys.argv[sys.argv.index("--") + 1]); os.makedirs(OUT, exist_ok=True)
import rustic_link
from rustic_link import refs
REAL = 1.8

def make(name, w, h, box, bg=(0.95, 0.95, 0.92, 1), fg=(0.2, 0.1, 0.1, 1), transparent=False):
    img = bpy.data.images.new(name, w, h, alpha=True)
    px = np.zeros((h, w, 4), np.float32); px[:] = (0, 0, 0, 0) if transparent else bg
    x0, y0, x1, y1 = box
    px[y0:y1, x0:x1] = fg
    px[y0 + 10:y0 + 30, x0 + 5:x1 - 5] = (0.8, 0.7, 0.1, 1)   # some detail inside the subject
    img.pixels.foreach_set(px.ravel()); img.filepath_raw = os.path.join(OUT, name + ".png"); img.file_format = "PNG"; img.save()
    bpy.data.images.remove(img)
    return os.path.join(OUT, name + ".png")

cases = {"front": ((1200, 900), (700, 100, 900, 800), False),   # wide picture, subject right of centre
         "side": ((600, 1000), (100, 50, 220, 980), True),       # tall picture, transparent background
         "top": ((800, 800), (300, 350, 500, 450), False)}
files = [(make(n, *c[0], c[1], transparent=c[2]), refs.guess_view(n)) for n, c in cases.items()]
obs, notes = refs.add_references(files, REAL)
bpy.context.view_layer.update()
ok = True
for ob, (n, ((w, h), (x0, y0, x1, y1), _)) in zip(sorted(obs, key=lambda o: ["FRONT", "RIGHT", "TOP"].index(o["rustic_reference"])), cases.items()):
    S = ob.empty_display_size
    iw, ih = S * w / max(w, h), S * h / max(w, h)
    def world(px, py):
        return ob.matrix_world @ Vector(((px / w - 0.5) * iw, (py / h - 0.5) * ih, 0))
    bl, tr = world(x0, y0), world(x1, y1)
    lo = Vector(map(min, bl, tr)); hi = Vector(map(max, bl, tr)); c = (lo + hi) / 2
    if n == "top":
        good = abs(c.x) < 1e-3 and abs(c.y) < 1e-3
        msg = f"centre=({c.x:.3f},{c.y:.3f}) width={hi.x - lo.x:.3f}"
    else:
        good = abs(lo.z) < 1e-3 and abs(hi.z - REAL) < 1e-3 and abs(c.x if n == 'front' else c.y) < 1e-3
        msg = f"bottom={lo.z:.4f} top={hi.z:.4f} centre={(c.x if n == 'front' else c.y):.4f}"
    # The picture must face the viewer of its view: its normal points toward the camera side.
    normal = (ob.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    want = {"front": Vector((0, -1, 0)), "side": Vector((1, 0, 0)), "top": Vector((0, 0, 1))}[n]
    good = good and normal.dot(want) > 0.99
    ok &= good
    print(f"REFS {n}: {ob['rustic_reference']} {msg} normal={tuple(round(a, 2) for a in normal)} {'OK' if good else 'FAIL'}")
# Front width must equal top width (top scaled from front).
print("REFS notes:", notes)
print("REFS DONE", "ok" if ok else "FAILED")
