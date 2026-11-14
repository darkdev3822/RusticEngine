# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender lights, world and colour management for RusticEngine.

glTF lights can't carry what a Blender light really is (watts, area lights, soft size, blend), and glTF has
no world at all, so these go along as RUSTIC_blender_light (on light nodes) and RUSTIC_blender_world (on the
scene). RusticEngine rebuilds them with brightness factors measured against Cycles.
"""
import bpy

from . import graph

LIGHT_EXT = "RUSTIC_blender_light"
WORLD_EXT = "RUSTIC_blender_world"
ACTIONS_EXT = "RUSTIC_blender_actions"


def _cyclic(act):
    """Blender's Cyclic Animation flag, Cycles modifiers on every curve, or a name ending in loop."""
    if getattr(act, "use_cyclic", False):
        return True
    name = act.name.lower()
    if name.endswith(("loop", "_cycle", "-cycle")):
        return True
    curves = list(getattr(act, "fcurves", []) or [])
    if not curves:   # Blender 4.4+ slotted actions keep curves in layers/strips/channelbags
        for layer in getattr(act, "layers", []):
            for strip in layer.strips:
                for bag in getattr(strip, "channelbags", []):
                    curves += list(bag.fcurves)
    return bool(curves) and all(any(m.type == "CYCLES" for m in fc.modifiers) for fc in curves)


def actions_data(scene):
    """Per action (glTF animations are named after them): loop or not, and Blender's frame range and fps."""
    fps = scene.render.fps / scene.render.fps_base
    return {"fps": fps, "actions": {a.name: {"loop": _cyclic(a), "start": a.frame_range[0], "end": a.frame_range[1]}
                                     for a in bpy.data.actions}}


def light_data(light):
    d = {
        "type": light.type,
        "energy": light.energy,
        "color": list(light.color),
        "shadow": bool(getattr(light, "use_shadow", True)),
        "diffuse": getattr(light, "diffuse_factor", 1.0),
        "specular": getattr(light, "specular_factor", 1.0),
        "volume": getattr(light, "volume_factor", 1.0),
    }
    if light.type == "SUN":
        d["angle"] = light.angle
    elif light.type == "AREA":
        d.update(size=light.size, size_y=light.size_y if light.shape in {"RECTANGLE", "ELLIPSE"} else light.size,
                 shape=light.shape, spread=getattr(light, "spread", 3.14159265))
    else:
        d["radius"] = light.shadow_soft_size
        if light.type == "SPOT":
            d.update(spot_size=light.spot_size, spot_blend=light.spot_blend)
    if getattr(light, "use_custom_distance", False):
        d["cutoff"] = light.cutoff_distance
    return d


def _from(sock):
    return sock.links[0].from_node if sock.is_linked else None


def world_data(scene, ctx):
    vs = scene.view_settings
    d = {"view_transform": vs.view_transform, "look": vs.look, "exposure": vs.exposure, "gamma": vs.gamma,
         "export": bool(scene.rustic.export_world)}
    world = scene.world
    bg = {"kind": "color", "color": [0.05, 0.05, 0.05], "strength": 1.0}
    if world is not None and not world.use_nodes:
        bg["color"] = list(world.color)
    elif world is not None:
        nt = world.node_tree
        out = nt.get_output_node("CYCLES") or nt.get_output_node("ALL")
        node = _from(out.inputs["Surface"]) if out else None
        if node is not None and node.bl_idname == "ShaderNodeBackground":
            bg["strength"] = node.inputs["Strength"].default_value
            src = _from(node.inputs["Color"])
            if src is None:
                bg["color"] = list(node.inputs["Color"].default_value)[:3]
            elif src.bl_idname == "ShaderNodeTexEnvironment" and src.image is not None:
                bg["kind"] = "image"
                bg["image"] = graph._image_entry(src.image, ctx)
                mapping = _from(src.inputs["Vector"])
                if mapping is not None and mapping.bl_idname == "ShaderNodeMapping" and "Rotation" in mapping.inputs:
                    bg["rotation_z"] = mapping.inputs["Rotation"].default_value[2]
            elif src.bl_idname == "ShaderNodeTexSky":
                bg["kind"] = "sky"
                bg["sky_type"] = src.sky_type
            else:
                bg["note"] = f"{src.bl_idname} into the world color isn't rebuilt; using a dark color"
        elif node is not None:
            bg["note"] = f"world uses {node.bl_idname}; only Background is rebuilt"
    d["background"] = bg
    # Blender's untouched default world (flat dark grey) says nothing about the game: props keep it, and
    # a WorldEnvironment in every prop would fight the level's. Only a world someone set up is sent.
    if bg["kind"] == "color" and bg.get("strength", 1.0) == 1.0 and all(abs(c - 0.0509) < 0.002 for c in bg["color"][:3]):
        d["export"] = False
        d["skipped"] = "default world"
    return d
