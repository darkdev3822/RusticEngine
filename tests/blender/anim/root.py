# Run: blender -b --factory-startup --python root.py -- PROJECT_DIR
# A walker: a non-deforming "root" bone that travels 2 m forward (-Y in Blender) over a 1 s cyclic Walk.
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
arm = bpy.data.armatures.new("WalkerRig")
rig = bpy.data.objects.new("Walker", arm)
sc.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
root = arm.edit_bones.new("root"); root.head = (0, 0, 0); root.tail = (0, 0.3, 0); root.use_deform = False
body = arm.edit_bones.new("body"); body.head = (0, 0, 0.5); body.tail = (0, 0, 1.5); body.parent = root
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.mesh.primitive_cube_add(size=0.5, location=(0, 0, 1))
box = bpy.context.object
box.parent = rig
box.modifiers.new("Armature", "ARMATURE").object = rig
box.vertex_groups.new(name="body").add(list(range(len(box.data.vertices))), 1.0, "REPLACE")
rig.animation_data_create()
act = bpy.data.actions.new("Walk")
rig.animation_data.action = act
pb = rig.pose.bones["root"]
# 2 m along world -Y (forward in Blender), written in the bone's own axes
import mathutils
local = rig.data.bones["root"].matrix_local.to_3x3().inverted() @ mathutils.Vector((0, -2, 0))
pb.location = (0, 0, 0); pb.keyframe_insert("location", frame=1)
pb.location = local; pb.keyframe_insert("location", frame=25)
fcurves = act.fcurves if getattr(act, "fcurves", None) else [fc for l in act.layers for st in l.strips for bag in st.channelbags for fc in bag.fcurves]
for fc in fcurves:
    for k in fc.keyframe_points:
        k.interpolation = "LINEAR"
act.use_frame_range = True; act.frame_start, act.frame_end = 1, 25; act.use_cyclic = True
sc.frame_set(25)
print("ROOT_BLENDER travel_end", tuple(round(c, 3) for c in (rig.matrix_world @ rig.pose.bones["root"].head)))
sc.frame_set(1)
rustic_link.export_glb(os.path.join(PROJ, "walker.glb"))
print("ROOT_DONE")
