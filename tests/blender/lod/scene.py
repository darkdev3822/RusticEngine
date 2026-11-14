# Run: blender -b --factory-startup --python scene.py -- PROJECT_DIR
# Rock: Make LODs (2 levels, laid out side by side), LOD2 from 40 m, hidden beyond 100 m.
# Barrel: a physics object (rigid body) with Make LODs, dropped from 3 m. Prints the Blender-side numbers.
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "blender"))
PROJ = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
import rustic_link
from rustic_link import lod

bpy.ops.wm.read_factory_settings(use_empty=True)
rustic_link.register()
if "rustic_link" not in bpy.context.preferences.addons:
    bpy.context.preferences.addons.new().module = "rustic_link"

bpy.ops.mesh.primitive_plane_add(size=40)
bpy.context.object.name = "Ground"
bpy.ops.rustic.add_collision(kind="STATIC")

bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=1, location=(0, 0, 1))
bpy.context.object.name = "Rock"
bpy.ops.rustic.make_lods(count=2)
bpy.data.objects["Rock_LOD2"].rustic_lod_distance = 40
bpy.data.objects["Rock_LOD0"].rustic_lod_cull = 100

bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.4, depth=1, location=(5, 0, 3))
bpy.context.object.name = "Barrel"
bpy.ops.rustic.add_collision(kind="PHYSICS")
bpy.ops.rustic.make_lods(count=2)

for o in sorted(bpy.data.objects, key=lambda o: o.name):
    d = lod.lod_data(o)
    if d:
        print(f"LOD_BLENDER {o.name} tris={lod.triangles(o)} begin={d['begin']:.1f} end={d['end']:.1f} rigid={o.rigid_body is not None}")
rustic_link.export_glb(os.path.join(PROJ, "props.glb"))
print("LOD_EXPORTED")
