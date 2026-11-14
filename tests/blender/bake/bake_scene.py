# Run: blender -b --factory-startup --python bake_scene.py -- PROJECT_DIR STAGE
# Stage 1: a crate whose material RusticEngine can't rebuild (4D Voronoi color, noise roughness, bump) plus a
#          plain red material on a second object; exports (no report yet, so nothing is baked).
# Stage 2 (after the editor imported it and wrote its report): exports again -> the crate material is baked.
# Stage 3: exports again with nothing changed -> the bake comes from the cache.
import json
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "blender"))
argv = sys.argv[sys.argv.index("--") + 1:]
PROJ, STAGE = os.path.abspath(argv[0]), argv[1]
BLEND = os.path.join(os.path.dirname(PROJ), "blend", "crate.blend")
GLB = os.path.join(PROJ, "art", "crate.glb")

import rustic_link

if STAGE == "1":
    bpy.ops.wm.read_factory_settings(use_empty=True)   # before registering: it resets the add-on list
rustic_link.register()
if "rustic_link" not in bpy.context.preferences.addons:
    bpy.context.preferences.addons.new().module = "rustic_link"

if STAGE == "1":
    bpy.ops.mesh.primitive_cube_add()
    crate = bpy.context.object
    crate.name = "Crate"
    mat = bpy.data.materials.new("Weird")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.voronoi_dimensions = "4D"
    vor.inputs["Scale"].default_value = 3.0
    nt.links.new(vor.outputs["Color"], bsdf.inputs["Base Color"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(nz.outputs["Fac"], bsdf.inputs["Roughness"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.3   # 5.x default (1 mm) bakes to an almost flat normal map
    nt.links.new(vor.outputs["Distance"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    crate.data.materials.append(mat)
    bpy.ops.mesh.primitive_uv_sphere_add(location=(3, 0, 0))
    red = bpy.data.materials.new("Red")
    red.use_nodes = True
    red.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.05, 0.05, 1)
    bpy.context.object.data.materials.append(red)
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
else:
    bpy.ops.wm.open_mainfile(filepath=BLEND)

t0 = time.time()
rustic_link.export_glb(GLB)
note = bpy.context.window_manager.rustic_bake_note
print(f"BAKE_STAGE {STAGE} note=[{note}] seconds={time.time() - t0:.1f}")
print("BAKE_PLAIN", json.dumps(rustic_link.bake.plain_materials(GLB)))
print("BAKE_AUTO", [m.name for m in bpy.data.materials if m.get("rustic_auto_baked")])
print("BAKE_LEFTOVERS", [m.name for m in bpy.data.materials if "baked" in m.name], [o.name for o in bpy.data.objects if "tmp" in o.name],
      bpy.data.objects["Crate"].material_slots[0].link, bpy.data.objects["Crate"].material_slots[0].material.name)
bpy.ops.wm.save_mainfile()
