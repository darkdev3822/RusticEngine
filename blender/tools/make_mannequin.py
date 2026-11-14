# SPDX-License-Identifier: GPL-3.0-or-later
"""Builds the blocky mannequin bundled with the Animated Character mechanic (CC0, made from code).

Usage: blender -b --factory-startup --python make_mannequin.py -- OUT.glb
A 1.8 m figure of boxes rigidly skinned to 11 bones under a non-deforming "root" bone, with four actions:
Idle (2 s breathing, cyclic), Walk (1 s cycle, root travels 1.4 m: 1.4 m/s), Run (0.6 s, 2.4 m: 4 m/s) and
Fall (arms up, cyclic). Exported with the RusticEngine add-on, so loops and root motion come along.
"""
import math
import os
import sys

import bpy
import mathutils

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
import rustic_link

bpy.ops.wm.read_factory_settings(use_empty=True)
rustic_link.register()
if "rustic_link" not in bpy.context.preferences.addons:
    bpy.context.preferences.addons.new().module = "rustic_link"
sc = bpy.context.scene
sc.render.fps = 30

# name: (head, tail, parent, box size (x, y, z) centred on the bone)
BONES = {
    "hips": ((0, 0, 0.95), (0, 0, 1.1), "root", (0.32, 0.18, 0.2)),
    "spine": ((0, 0, 1.1), (0, 0, 1.45), "hips", (0.36, 0.2, 0.38)),
    "head": ((0, 0, 1.5), (0, 0, 1.78), "spine", (0.22, 0.24, 0.26)),
    "upper_arm.L": ((0.22, 0, 1.42), (0.22, 0, 1.15), "spine", (0.09, 0.09, 0.27)),
    "forearm.L": ((0.22, 0, 1.15), (0.22, 0, 0.88), "upper_arm.L", (0.08, 0.08, 0.27)),
    "upper_arm.R": ((-0.22, 0, 1.42), (-0.22, 0, 1.15), "spine", (0.09, 0.09, 0.27)),
    "forearm.R": ((-0.22, 0, 1.15), (-0.22, 0, 0.88), "upper_arm.R", (0.08, 0.08, 0.27)),
    "thigh.L": ((0.1, 0, 0.92), (0.1, 0, 0.5), "hips", (0.13, 0.13, 0.42)),
    "shin.L": ((0.1, 0, 0.5), (0.1, -0.02, 0.08), "thigh.L", (0.11, 0.11, 0.42)),
    "thigh.R": ((-0.1, 0, 0.92), (-0.1, 0, 0.5), "hips", (0.13, 0.13, 0.42)),
    "shin.R": ((-0.1, 0, 0.5), (-0.1, -0.02, 0.08), "thigh.R", (0.11, 0.11, 0.42)),
}

arm = bpy.data.armatures.new("MannequinRig")
rig = bpy.data.objects.new("Mannequin", arm)
sc.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
root = arm.edit_bones.new("root"); root.head = (0, 0, 0); root.tail = (0, 0.25, 0); root.use_deform = False
for name, (h, t, parent, _s) in BONES.items():
    b = arm.edit_bones.new(name); b.head = h; b.tail = t; b.parent = arm.edit_bones[parent]
bpy.ops.object.mode_set(mode="OBJECT")

# One mesh of boxes, each vertex fully on its bone; feet as small boxes on the shins.
verts, faces, groups = [], [], []
def box(center, size, bone):
    cx, cy, cz = center; sx, sy, sz = (s / 2 for s in size)
    base = len(verts)
    for dx in (-sx, sx):
        for dy in (-sy, sy):
            for dz in (-sz, sz):
                verts.append((cx + dx, cy + dy, cz + dz)); groups.append(bone)
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        faces.append(tuple(base + i for i in f))
for name, (h, t, _p, size) in BONES.items():
    box([(a + b) / 2 for a, b in zip(h, t)], size, name)
for side, x in (("L", 0.1), ("R", -0.1)):
    box((x, -0.05, 0.04), (0.11, 0.24, 0.08), "shin." + side)
me = bpy.data.meshes.new("MannequinBody")
me.from_pydata(verts, [], faces)
body = bpy.data.objects.new("Body", me)
sc.collection.objects.link(body)
body.parent = rig
body.modifiers.new("Armature", "ARMATURE").object = rig
for i, g in enumerate(groups):
    vg = body.vertex_groups.get(g) or body.vertex_groups.new(name=g)
    vg.add([i], 1.0, "REPLACE")
mat = bpy.data.materials.new("Mannequin")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.75, 0.55, 0.35, 1)
mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
me.materials.append(mat)
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True); bpy.context.view_layer.objects.active = body
bpy.ops.object.shade_flat()

rig.animation_data_create()
for pb in rig.pose.bones:
    pb.rotation_mode = "XYZ"


def action(name, frames, pose, travel=0.0, cyclic=True):
    """pose(t in 0..1) -> {bone: (rx, ry, rz) degrees, 'hips_z': offset}; root moves `travel` m along -Y."""
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    rig.animation_data.action = act
    local = rig.data.bones["root"].matrix_local.to_3x3().inverted()
    for f in range(frames + 1):
        t = f / frames
        p = pose(t)
        for pb in rig.pose.bones:
            if pb.name == "root":
                pb.location = local @ mathutils.Vector((0, -travel * t, 0))
                pb.keyframe_insert("location", frame=1 + f)
                continue
            r = p.get(pb.name, (0, 0, 0))
            pb.rotation_euler = [math.radians(a) for a in r]
            pb.keyframe_insert("rotation_euler", frame=1 + f)
            if pb.name == "hips":
                pb.location = (0, 0, p.get("hips_z", 0.0))
                pb.keyframe_insert("location", frame=1 + f)
    act.use_frame_range = True
    act.frame_start, act.frame_end = 1, 1 + frames
    act.use_cyclic = cyclic
    return act


def gait(swing, knee, arm_swing, bounce):
    def pose(t):
        s = math.sin(t * 2 * math.pi)
        return {
            "thigh.L": (swing * s, 0, 0), "thigh.R": (-swing * s, 0, 0),
            "shin.L": (-knee * max(0.0, -math.cos(t * 2 * math.pi + 0.6)), 0, 0),
            "shin.R": (-knee * max(0.0, math.cos(t * 2 * math.pi + 0.6)), 0, 0),
            "upper_arm.L": (-arm_swing * s, 0, 0), "upper_arm.R": (arm_swing * s, 0, 0),
            "forearm.L": (20, 0, 0), "forearm.R": (20, 0, 0),
            "spine": (5 + bounce * 20, 0, 0), "hips_z": -bounce * abs(math.cos(t * 2 * math.pi)),
        }
    return pose


action("Idle", 60, lambda t: {"spine": (2 * math.sin(t * 2 * math.pi), 0, 0), "head": (-2 * math.sin(t * 2 * math.pi), 0, 0),
                              "upper_arm.L": (0, 0, 4), "upper_arm.R": (0, 0, -4), "hips_z": -0.01 * (1 + math.sin(t * 2 * math.pi))})
action("Walk", 30, gait(28, 40, 25, 0.02), travel=1.4)
action("Run", 18, gait(45, 80, 50, 0.05), travel=2.4)
action("Fall", 20, lambda t: {"upper_arm.L": (0, 0, 120 + 5 * math.sin(t * 2 * math.pi)), "upper_arm.R": (0, 0, -120 - 5 * math.sin(t * 2 * math.pi)),
                              "thigh.L": (20, 0, 0), "shin.L": (-40, 0, 0), "thigh.R": (-10, 0, 0), "shin.R": (-20, 0, 0)})
rig.animation_data.action = bpy.data.actions["Idle"]
sc.frame_set(1)
sc.rustic.export_world = False
rustic_link.export_glb(OUT)
print("MANNEQUIN_DONE", OUT, os.path.getsize(OUT))
