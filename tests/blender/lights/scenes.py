# Run: blender -b --factory-startup --python scenes.py -- OUT_DIR
# One scene per case: a white plane, one light (or a world HDRI), an orthographic camera. Each is rendered with
# Cycles (linear EXR, mean of the centre) and exported with the add-on to OUT_DIR/proj/<case>.glb.
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "blender"))
OUT = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
import rustic_link


def base(world_strength=0.0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if not hasattr(bpy.types.Scene, "rustic"):
        rustic_link.register()
    if "rustic_link" not in bpy.context.preferences.addons:
        bpy.context.preferences.addons.new().module = "rustic_link"
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.samples = 128; sc.cycles.device = "CPU"
    sc.view_settings.view_transform = "Standard"
    sc.render.resolution_x = sc.render.resolution_y = 64
    w = bpy.data.worlds.new("World"); w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0, 0, 0, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = world_strength
    sc.world = w
    bpy.ops.mesh.primitive_plane_add(size=20)
    m = bpy.data.materials.new("White"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (1, 1, 1, 1); b.inputs["Roughness"].default_value = 1.0
    b.inputs["Specular IOR Level"].default_value = 0.0
    bpy.context.object.data.materials.append(m)
    cam = bpy.data.cameras.new("Cam"); cam.type = "ORTHO"; cam.ortho_scale = 0.05
    co = bpy.data.objects.new("Cam", cam); co.location = (0, 0, 0.5); sc.collection.objects.link(co); sc.camera = co
    return sc


def light(kind, rot=(0, 0, 0), **kw):
    ld = bpy.data.lights.new("L", kind)
    for k, v in kw.items():
        setattr(ld, k, v)
    lo = bpy.data.objects.new("L", ld); lo.location = (0, 0, 2); lo.rotation_euler = rot
    bpy.context.scene.collection.objects.link(lo)


def finish(name):
    sc = bpy.context.scene
    sc.render.image_settings.file_format = "OPEN_EXR"
    sc.render.filepath = os.path.join(OUT, "cycles_" + name + ".exr")
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(sc.render.filepath)
    a = np.array(img.pixels[:]).reshape(64, 64, 4)[24:40, 24:40, :3]
    print(f"CYCLES {name} {a.mean(axis=(0, 1)).round(4).tolist()}")
    rustic_link.export_glb(os.path.join(OUT, "proj", name + ".glb"))


base(); light("SUN", rot=(math.radians(30), 0, 0), energy=1.0); finish("sun")
base(); light("POINT", energy=20.0, shadow_soft_size=0.0); finish("point")
base(); light("SPOT", energy=20.0, shadow_soft_size=0.0, spot_size=math.radians(60)); finish("spot")
base(); light("AREA", energy=5.0, size=0.5); finish("area")
base(); light("POINT", energy=10.0, color=(1.0, 0.4, 0.1), shadow_soft_size=0.0); finish("point_orange")

# Sky Texture (Blender's physical sky, baked by the add-on): sun at 30 degrees, rotation 90.
def sky_world(sc, elev=30, rot=90):
    nt = sc.world.node_tree
    sky = nt.nodes.new("ShaderNodeTexSky"); sky.sun_elevation = math.radians(elev); sky.sun_rotation = math.radians(rot)
    nt.links.new(sky.outputs[0], nt.nodes["Background"].inputs["Color"])
    nt.nodes["Background"].inputs["Strength"].default_value = 0.02   # what a scene would use with exposure 0
    sc.view_settings.view_transform = "Standard"

sc = base(); sky_world(sc); finish("stex_floor")
for name, normal_rot in (("stex_wall_back", (0, math.radians(-90), 0)), ("stex_wall_sun", (0, math.radians(90), 0))):
    sc = base(); sky_world(sc)
    pl = bpy.data.objects["Plane"]; pl.scale = (0.05, 0.05, 0.05); pl.rotation_euler = normal_rot   # normal -X, then +X
    cam = sc.camera; n = 1 if name.endswith("sun") else -1
    cam.location = (n * 0.5, 0, 0); cam.rotation_euler = (math.radians(90), 0, math.radians(90 if n > 0 else -90))   # look back at the wall
    finish(name)

# World HDRI: an equirect whose colour marks direction (red faces Blender +X, green +Y, blue -X, white -Y).
sc = base()
W, H = 256, 128
u = (np.arange(W) + 0.5) / W
ang = -(u - 0.5) * 2 * math.pi          # Blender: u = -atan2(y, x) / 2pi + 0.5
cols = np.zeros((H, W, 4), np.float32); cols[..., 3] = 1
for i, a in enumerate(ang):
    d = (math.cos(a), math.sin(a))
    k = max(range(4), key=lambda j: [d[0], d[1], -d[0], -d[1]][j])
    cols[:, i, :3] = [(0.8, 0.05, 0.05), (0.05, 0.8, 0.05), (0.05, 0.05, 0.8), (0.8, 0.8, 0.8)][k]
# Written by hand as Radiance .hdr (RGBE, linear, no colour-space tags), read the same way by Blender and Godot.
def write_hdr(path, rgb):
    h, w, _ = rgb.shape
    m = rgb.max(axis=2)
    e = np.where(m > 1e-32, np.ceil(np.log2(np.maximum(m, 1e-32))), -128).astype(np.int32)
    scale = np.where(m > 1e-32, 256.0 / np.exp2(e), 0.0)
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = np.clip(rgb * scale[..., None], 0, 255).astype(np.uint8)
    out[..., 3] = np.where(m > 1e-32, e + 128, 0).astype(np.uint8)
    with open(path, "wb") as f:
        f.write(b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n" + f"-Y {h} +X {w}\n".encode() + out.tobytes())
hdr_path = os.path.join(OUT, "proj", "dirs.hdr")
write_hdr(hdr_path, cols[::-1, :, :3])   # .hdr rows go top to bottom; Blender pixels bottom to top
nt = sc.world.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(hdr_path)
nt.links.new(env.outputs["Color"], nt.nodes["Background"].inputs["Color"])
nt.nodes["Background"].inputs["Strength"].default_value = 1.0
bpy.data.objects.remove(bpy.data.objects["Plane"])
cam = sc.camera; cam.data.type = "PERSP"; cam.data.lens = 50
for name, rot in (("sky_px", (90, 0, -90)), ("sky_py", (90, 0, 0))):  # camera looking along +X, then +Y
    cam.rotation_euler = [math.radians(r) for r in rot]
    finish(name)
print("SCENES_DONE")
