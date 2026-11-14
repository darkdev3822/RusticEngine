# Run: blender -b --factory-startup --python rig.py -- PROJECT_DIR
# A skinned 2-bone arm with actions Walk (cyclic) and Wave (one-shot) and a shape key Smile; exports it with the
# add-on and prints where the tip bone's head is (world space, Godot axes) at a few frames of each action.
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "blender"))
PROJ = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
import rustic_link

bpy.ops.wm.read_factory_settings(use_empty=True)
rustic_link.register()
if "rustic_link" not in bpy.context.preferences.addons:
    bpy.context.preferences.addons.new().module = "rustic_link"
sc = bpy.context.scene
sc.render.fps = 24

arm_data = bpy.data.armatures.new("ArmRig")
rig = bpy.data.objects.new("Rig", arm_data)
sc.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
b1 = arm_data.edit_bones.new("Upper"); b1.head = (0, 0, 0); b1.tail = (0, 0, 1)
b2 = arm_data.edit_bones.new("Lower"); b2.head = (0, 0, 1); b2.tail = (0, 0, 2); b2.parent = b1; b2.use_connect = True
ctl = arm_data.edit_bones.new("Control"); ctl.head = (1, 0, 0); ctl.tail = (1, 0, 0.5); ctl.use_deform = False
bpy.ops.object.mode_set(mode="OBJECT")

bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=2, location=(0, 0, 1), vertices=8)
arm = bpy.context.object; arm.name = "Arm"
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.subdivide(number_cuts=3); bpy.ops.object.mode_set(mode="OBJECT")
arm.parent = rig
mod = arm.modifiers.new("Armature", "ARMATURE"); mod.object = rig
for name in ("Upper", "Lower"):
    vg = arm.vertex_groups.new(name=name)
    for v in arm.data.vertices:
        if (v.co.z + 1 < 1.0) == (name == "Upper"):
            vg.add([v.index], 1.0, "REPLACE")
arm.shape_key_add(name="Basis")
smile = arm.shape_key_add(name="Smile")
for v in smile.data:
    v.co.x *= 1.5

def action(name, keys, cyclic):
    rig.animation_data_create()
    act = bpy.data.actions.new(name)
    rig.animation_data.action = act
    for f, ang in keys:
        pb = rig.pose.bones["Lower"]
        pb.rotation_mode = "XYZ"; pb.rotation_euler = (math.radians(ang), 0, 0)
        pb.keyframe_insert("rotation_euler", frame=f)
    act.use_frame_range = True
    act.frame_start, act.frame_end = keys[0][0], keys[-1][0]
    act.use_cyclic = cyclic
    act.use_fake_user = True
    return act

walk = action("Walk", [(1, 0), (13, 45), (25, 0)], True)
wave = action("Wave", [(1, 0), (10, -60), (20, 0)], False)
arm.data.shape_keys.animation_data_create()
sk_act = bpy.data.actions.new("Smile")
arm.data.shape_keys.animation_data.action = sk_act
smile.value = 0; smile.keyframe_insert("value", frame=1)
smile.value = 1; smile.keyframe_insert("value", frame=12)
sk_act.use_fake_user = True

def tip(act, frame):
    rig.animation_data.action = act
    sc.frame_set(frame)
    p = rig.matrix_world @ rig.pose.bones["Lower"].tail
    return (round(p.x, 3), round(p.z, 3), round(-p.y, 3))   # Godot axes (Y up)

for act, frames in ((walk, (1, 7, 13)), (wave, (1, 10))):
    for f in frames:
        print(f"ANIM_BLENDER {act.name} t={(f - act.frame_start) / sc.render.fps:.4f} tip={tip(act, f)}")
rig.animation_data.action = walk
sc.frame_set(1)
os.makedirs(os.path.join(os.path.dirname(PROJ), "blend"), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(PROJ), "blend", "arm.blend"))
rustic_link.export_glb(os.path.join(PROJ, "arm.glb"))
print("ANIM_DONE")
