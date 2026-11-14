# Run: blender -b --factory-startup --python ask.py -- PROJECT_DIR QUESTION
# Builds a small scene (a beveled crate in Edit Mode with its top edges selected), asks Ember through the
# add-on's Ember panel operator, and waits for the editor's reply (timers don't run in -b, so poll here).
import os
import sys
import time

import bpy
import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "blender"))
argv = sys.argv[sys.argv.index("--") + 1:]
PROJ, QUESTION = os.path.abspath(argv[0]), argv[1]

import rustic_link
from rustic_link import ember
rustic_link.register()
if "rustic_link" not in bpy.context.preferences.addons:
    bpy.context.preferences.addons.new().module = "rustic_link"

bpy.ops.wm.read_factory_settings(use_empty=True)
rustic_link.register() if not hasattr(bpy.types.Scene, "rustic") else None
bpy.ops.mesh.primitive_cube_add()
ob = bpy.context.object
ob.name = "Crate"
ob.scale = (1, 1, 0.5)
ob.modifiers.new("Bevel", "BEVEL")
bpy.context.scene.rustic.target = os.path.join(PROJ, "art", "blender", "crate.glb")
bpy.ops.object.mode_set(mode="EDIT")
bpy.context.tool_settings.mesh_select_mode = (False, True, False)
bm = bmesh.from_edit_mesh(ob.data)
for el in (*bm.verts, *bm.edges, *bm.faces):
    el.select = False
for e in bm.edges:
    if all(v.co.z > 0 for v in e.verts):
        e.select = True
        for v in e.verts:
            v.select = True
bmesh.update_edit_mesh(ob.data)

print("EMBER_CONTEXT", ember.describe(bpy.context))
for _ in range(60):          # wait for the editor to say it's alive
    if ember._connected(PROJ):
        break
    time.sleep(1)
r = bpy.ops.rustic.ember_ask(question=QUESTION)
print("EMBER_ASKED", r)
t0 = time.time()
while not ember._state["done"] and time.time() - t0 < 400:
    ember._state["asked_at"] = max(ember._state["asked_at"], t0)  # keep the 8 s pickup check honest
    ember._poll()
    time.sleep(0.5)
print("EMBER_DONE", ember._state["done"], round(time.time() - t0), "s")
print("EMBER_REPLY_BEGIN\n" + ember._state["text"] + "\nEMBER_REPLY_END")
