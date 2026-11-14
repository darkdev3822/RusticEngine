# SPDX-License-Identifier: GPL-3.0-or-later
"""Levels of detail made in Blender: objects named <Name>_LOD0, <Name>_LOD1, ...

RusticEngine already simplifies every mesh automatically; hand-made LODs are for when that isn't good enough
(trees, foliage cards, characters' faces). Each LOD object goes along with RUSTIC_blender_lod {group, level,
begin, end}: the engine shows it between those camera distances (with a margin so it doesn't flicker), puts
it where LOD0 is (LODs laid out side by side in Blender for comparison still line up), and keeps it inside
LOD0's physics body if LOD0 has collision.
"""
import re

import bpy
from bpy.props import FloatProperty, IntProperty

EXT = "RUSTIC_blender_lod"
NAME = re.compile(r"^(.*)_LOD(\d+)$")
# Where LOD n starts, in multiples of the object's size (bounding box diagonal): a 1 m crate switches at
# ~10 m, 26 m, 60 m; a 12 m tree at ~70 m, 180 m.
AUTO = (0.0, 6.0, 15.0, 35.0, 80.0, 160.0)


def group_of(ob):
    """(base name, level) for an LOD object, else None."""
    m = NAME.match(ob.name)
    return (m.group(1), int(m.group(2))) if m else None


def members(base, scene=None):
    objs = (scene or bpy.context.scene).objects
    out = {}
    for o in objs:
        g = group_of(o)
        if g and g[0] == base:
            out[g[1]] = o
    return [out[k] for k in sorted(out)]


def _size(ob):
    d = ob.dimensions
    return max((d.x ** 2 + d.y ** 2 + d.z ** 2) ** 0.5, 0.01)


def lod_data(ob):
    g = group_of(ob)
    if not g or ob.type != "MESH":
        return None
    base, level = g
    lods = members(base)
    if len(lods) < 2:
        return None
    size = _size(lods[0])

    def begin(o, i):
        return o.rustic_lod_distance if o.rustic_lod_distance > 0 else size * AUTO[min(i, len(AUTO) - 1)]

    starts = [0.0] + [begin(o, i) for i, o in enumerate(lods) if i > 0]
    i = lods.index(ob)
    end = starts[i + 1] if i + 1 < len(lods) else lods[0].rustic_lod_cull
    return {"group": base, "level": level, "index": i, "begin": starts[i], "end": end, "lod0": lods[0].name}


def triangles(ob):
    me = ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    return sum(len(p.vertices) - 2 for p in me.polygons)


class RUSTIC_OT_make_lods(bpy.types.Operator):
    """Make simpler copies of this object for far away (Name_LOD1, _LOD2 with Decimate modifiers you can tweak)"""
    bl_idname = "rustic.make_lods"
    bl_label = "Make LODs"
    bl_options = {"REGISTER", "UNDO"}

    count: IntProperty(name="Extra Levels", default=2, min=1, max=4)

    def execute(self, context):
        ob = context.object
        if ob is None or ob.type != "MESH":
            return {"CANCELLED"}
        g = group_of(ob)
        if g is None:
            ob.name = ob.name + "_LOD0"
            g = (ob.name[:-5], 0)
        base = g[0]
        existing = members(base)
        src = existing[0]
        ratio = 1.0
        for k in range(self.count):
            level = len(existing) + k
            ratio *= 0.4
            copy = src.copy()
            copy.data = src.data.copy()
            copy.name = f"{base}_LOD{level}"
            rbw = context.scene.rigidbody_world.collection if context.scene.rigidbody_world else None
            for c in src.users_collection:
                if c != rbw and copy.name not in c.objects:   # a rigid-body copy already joined the physics world
                    c.objects.link(copy)
            if copy.rigid_body is not None:        # only LOD0 collides
                context.view_layer.objects.active = copy
                bpy.ops.rigidbody.object_remove()
            dec = copy.modifiers.new("LOD Decimate", "DECIMATE")
            dec.ratio = ratio
            copy.location.x += _size(src) * (level) * 0.8   # side by side to compare; the game lines them up
        context.view_layer.objects.active = ob
        self.report({"INFO"}, f"Made {self.count} LOD(s) of {base}: adjust each one's Decimate ratio, or model it by hand")
        return {"FINISHED"}


def draw_panel(layout, context):
    ob = context.object
    if ob is None or ob.type != "MESH":
        return
    box = layout.box()
    g = group_of(ob)
    if g is None:
        row = box.row()
        row.label(text="LODs: automatic", icon="MOD_DECIM")
        row.operator(RUSTIC_OT_make_lods.bl_idname, text="Make LODs")
        return
    lods = members(g[0])
    box.label(text=f"LODs: {g[0]}", icon="MOD_DECIM")
    for o in lods:
        d = lod_data(o) if len(lods) > 1 else None
        row = box.row()
        row.label(text=f"{o.name}: {triangles(o)} tris")
        if d:
            row.label(text=f"{d['begin']:.0f}-{d['end']:.0f} m" if d["end"] else f"{d['begin']:.0f} m +")
    box.prop(ob, "rustic_lod_distance", text="This LOD from (0 = auto)")
    if lods and ob == lods[0]:
        box.prop(ob, "rustic_lod_cull", text="Hide beyond (0 = never)")
    if len(lods) > 1:
        box.operator(RUSTIC_OT_make_lods.bl_idname, text="Add LOD").count = 1


classes = (RUSTIC_OT_make_lods,)


def register():
    bpy.types.Object.rustic_lod_distance = FloatProperty(
        name="LOD Distance", default=0.0, min=0.0, unit="LENGTH",
        description="Camera distance where this LOD takes over (0 = from the object's size)")
    bpy.types.Object.rustic_lod_cull = FloatProperty(
        name="Hide Beyond", default=0.0, min=0.0, unit="LENGTH",
        description="On LOD0: hide the object completely beyond this distance (0 = never)")


def unregister():
    del bpy.types.Object.rustic_lod_distance
    del bpy.types.Object.rustic_lod_cull
