# Run: blender -b --factory-startup --python live_scene.py -- PROJECT_DIR STAGE
# Stage 1: new level.blend (Cube with a Noise material), turns on Live Link and saves -> exported by the add-on.
# Stage 2: reopens it, moves the Cube, adds a Ball, recolours the material, saves again.
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "blender"))
argv = sys.argv[sys.argv.index("--") + 1:]
PROJ, STAGE = os.path.abspath(argv[0]), argv[1]
BLEND = os.path.join(os.path.dirname(PROJ), "blend", "level.blend")   # outside the project

import rustic_link
rustic_link.register()
if "rustic_link" not in bpy.context.preferences.addons:
    bpy.context.preferences.addons.new().module = "rustic_link"

if STAGE == "1":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    bpy.context.object.name = "Cube"
    mat = bpy.data.materials.new("Paint")
    mat.use_nodes = True
    nt = mat.node_tree
    noise = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(noise.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    bpy.context.object.data.materials.append(mat)
    scene = bpy.context.scene
    scene.rustic.live = True
    scene.rustic.target = os.path.join(PROJ, "art", "blender", "level.glb")
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
else:
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    bpy.data.objects["Cube"].location = (3, 0, 0)          # Blender x -> Godot x
    bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, 2))
    bpy.context.object.name = "Ball"
    rgb = bpy.data.materials["Paint"].node_tree.nodes.new("ShaderNodeRGB")
    rgb.outputs[0].default_value = (1, 0, 0, 1)
    bpy.data.materials["Paint"].node_tree.links.new(
        rgb.outputs[0], bpy.data.materials["Paint"].node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    bpy.ops.wm.save_mainfile()
print("LIVE_STAGE_DONE", STAGE, os.path.exists(os.path.join(PROJ, "art", "blender", "level.glb")))
