# SPDX-License-Identifier: GPL-3.0-or-later
"""Collision for RusticEngine, set up the Blender way: the Rigid Body settings (Physics properties).

Passive = a static collider (floors, walls), Active = a physics object that falls and gets pushed, Animated
(Passive + Animated) = a moving platform. The rigid body's Shape (Box, Sphere, Capsule, Cylinder, Cone, Convex
Hull, Mesh), Mass, Friction and Bounciness go along as RUSTIC_blender_collision on the object's glTF node.
Two things Blender's rigid bodies don't have: Trigger (an Area that detects things entering, no collision) and
Collision Only (an invisible collider, e.g. a simple box around a detailed statue).
"""
import bpy
from bpy.props import BoolProperty, EnumProperty

EXT = "RUSTIC_blender_collision"


def collision_data(ob):
    rb = ob.rigid_body
    trigger = getattr(ob, "rustic_trigger", False)
    if rb is None and not trigger:
        return None
    d = {
        "body": "trigger" if trigger else ("kinematic" if rb and (rb.type == "PASSIVE" and rb.kinematic) else
                                            ("rigid" if rb and rb.type == "ACTIVE" else "static")),
        "shape": rb.collision_shape if rb else "BOX",
        "collision_only": bool(getattr(ob, "rustic_collision_only", False)),
    }
    if rb:
        d.update(mass=rb.mass, friction=rb.friction, bounce=rb.restitution, enabled=rb.enabled)
    return d


class RUSTIC_OT_add_collision(bpy.types.Operator):
    """Give the selected objects collision for the game (a Blender Rigid Body you can simulate here too)"""
    bl_idname = "rustic.add_collision"
    bl_label = "Add Collision"
    bl_options = {"REGISTER", "UNDO"}

    kind: EnumProperty(items=[
        ("STATIC", "Static", "Doesn't move: floors, walls, rocks (Passive rigid body)"),
        ("PHYSICS", "Physics Object", "Falls, tumbles and gets pushed: crates, barrels (Active rigid body)"),
        ("TRIGGER", "Trigger Zone", "Detects the player entering, no collision: doors, checkpoints, traps"),
    ], default="STATIC")

    def execute(self, context):
        done = 0
        for ob in context.selected_objects:
            if ob.type != "MESH":
                continue
            context.view_layer.objects.active = ob
            if ob.rigid_body is None:
                bpy.ops.rigidbody.object_add()
            rb = ob.rigid_body
            rb.type = "ACTIVE" if self.kind == "PHYSICS" else "PASSIVE"
            # Static scenery can use its exact shape; moving objects need a simple one (fast and stable).
            rb.collision_shape = "MESH" if self.kind == "STATIC" else ("CONVEX_HULL" if self.kind == "PHYSICS" else "BOX")
            ob.rustic_trigger = self.kind == "TRIGGER"
            if self.kind == "TRIGGER":
                ob.display_type = "WIRE"
                ob.rustic_collision_only = True
            done += 1
        self.report({"INFO"}, f"Collision added to {done} object(s); fine-tune it in Physics properties > Rigid Body")
        return {"FINISHED"}


def draw_panel(layout, context):
    ob = context.object
    if ob is None or ob.type != "MESH":
        return
    box = layout.box()
    box.label(text=f"Collision: {ob.name}", icon="MOD_PHYSICS")
    rb = ob.rigid_body
    if rb is None:
        row = box.row(align=True)
        for kind, label in (("STATIC", "Static"), ("PHYSICS", "Physics"), ("TRIGGER", "Trigger")):
            row.operator(RUSTIC_OT_add_collision.bl_idname, text=label).kind = kind
        return
    col = box.column(align=True)
    if ob.rustic_trigger:
        col.label(text="Trigger zone (detects, doesn't collide)")
    else:
        col.prop(rb, "type", text="Body")
        if rb.type == "PASSIVE":
            col.prop(rb, "kinematic", text="Moves (animated platform)")
    col.prop(rb, "collision_shape", text="Shape")
    if not ob.rustic_trigger:
        if rb.type == "ACTIVE":
            col.prop(rb, "mass")
        col.prop(rb, "friction")
        col.prop(rb, "restitution", text="Bounciness")
        if rb.type == "ACTIVE" and rb.collision_shape == "MESH":
            col.label(text="Moving objects can't use Mesh: sent as Convex Hull", icon="INFO")
    box.prop(ob, "rustic_collision_only")
    box.prop(ob, "rustic_trigger")


classes = (RUSTIC_OT_add_collision,)


def register():
    bpy.types.Object.rustic_trigger = BoolProperty(
        name="Trigger Zone", default=False,
        description="In the game this is an Area: it detects bodies entering and leaving, nothing bumps into it")
    bpy.types.Object.rustic_collision_only = BoolProperty(
        name="Collision Only (invisible)", default=False,
        description="Send only the collision shape, not the visible mesh: invisible walls, or a simple collider around a detailed model")


def unregister():
    del bpy.types.Object.rustic_trigger
    del bpy.types.Object.rustic_collision_only
