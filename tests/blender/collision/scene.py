# Run: blender -b --factory-startup --python scene.py -- PROJECT_DIR
# Floor (static, exact mesh), a crate and a ball (physics, dropped from above), a scaled pillar (static
# cylinder), an invisible wall (collision only), a trigger zone and a moving platform; exports with the add-on.
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


def add(kind_op, name, loc, collision, **kw):
    kind_op(location=loc, **kw)
    ob = bpy.context.object
    ob.name = name
    if collision:
        bpy.ops.rustic.add_collision(kind=collision)
    return ob

floor = add(bpy.ops.mesh.primitive_plane_add, "Floor", (0, 0, 0), "STATIC", size=20)
crate = add(bpy.ops.mesh.primitive_cube_add, "Crate", (0, 0, 3), "PHYSICS", size=1)
crate.rigid_body.collision_shape = "BOX"; crate.rigid_body.mass = 5; crate.rigid_body.friction = 0.8; crate.rigid_body.restitution = 0.3
ball = add(bpy.ops.mesh.primitive_uv_sphere_add, "Ball", (3, 0, 4), "PHYSICS", radius=0.5)
ball.rigid_body.collision_shape = "SPHERE"
pillar = add(bpy.ops.mesh.primitive_cylinder_add, "Pillar", (-3, 0, 1), "STATIC", radius=0.5, depth=2)
pillar.scale = (2, 2, 1.5); pillar.rigid_body.collision_shape = "CYLINDER"
wall = add(bpy.ops.mesh.primitive_cube_add, "InvisibleWall", (0, 5, 1), "STATIC", size=2)
wall.rigid_body.collision_shape = "BOX"; wall.rustic_collision_only = True
zone = add(bpy.ops.mesh.primitive_cube_add, "Checkpoint", (0, -5, 1), "TRIGGER", size=2)
plat = add(bpy.ops.mesh.primitive_cube_add, "Platform", (6, 0, 1), "STATIC", size=1)
plat.rigid_body.collision_shape = "BOX"; plat.rigid_body.kinematic = True
named = add(bpy.ops.mesh.primitive_cube_add, "Wall-col", (-6, 0, 1), None, size=1)   # Godot's own naming convention
deco = add(bpy.ops.mesh.primitive_monkey_add, "Decoration", (0, 0, 8), None)   # no collision: stays a plain mesh
rustic_link.export_glb(os.path.join(PROJ, "level.glb"))
print("COLLISION_EXPORTED")
