# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender lights, world and colour management for RusticEngine.

glTF lights can't carry what a Blender light really is (watts, area lights, soft size, blend), and glTF has
no world at all, so these go along as RUSTIC_blender_light (on light nodes) and RUSTIC_blender_world (on the
scene). RusticEngine rebuilds them with brightness factors measured against Cycles.
"""
import os

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
                baked = bake_sky(src, bg["strength"], ctx)
                if baked:
                    bg.update(baked)   # kind "image" (the sky as a panorama) + "sun" (its sun as a light)
                else:
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


SKY_PROPS = ("sky_type", "sun_disc", "sun_size", "sun_intensity", "sun_elevation", "sun_rotation", "altitude",
             "air_density", "aerosol_density", "ozone_density", "turbidity", "ground_albedo")


def bake_sky(sky, strength, ctx):
    """Blender's Sky Texture, exactly: Cycles renders the sky (without its sun disc) into an equirect HDR the
    engine uses like an HDRI, and measures the sun disc's light on a white floor, which becomes a sun light.
    Cached in <glb>_textures/ by the sky's settings. Returns None if it can't render (no texture folder)."""
    import hashlib
    import json
    import math
    import os
    out_dir = ctx.get("texture_dir")
    if not out_dir:
        return None
    params = {p: (round(getattr(sky, p), 6) if isinstance(getattr(sky, p), float) else getattr(sky, p)) for p in SKY_PROPS if hasattr(sky, p)}
    key = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]
    os.makedirs(out_dir, exist_ok=True)
    img_path = os.path.join(out_dir, f"sky_{key}.exr")
    meta_path = os.path.join(out_dir, f"sky_{key}.json")
    if not (os.path.isfile(img_path) and os.path.isfile(meta_path)):
        sun = _render_sky(sky, img_path)
        with open(meta_path, "w") as f:
            json.dump({"params": params, "sun": sun}, f)
    with open(meta_path) as f:
        sun = json.load(f)["sun"]
    entry = {"name": os.path.basename(img_path), "path": img_path,
             "relative_path": os.path.relpath(img_path, ctx["glb_dir"]).replace(os.sep, "/") if ctx.get("glb_dir") else ""}
    out = {"kind": "image", "image": entry, "sky_type": sky.sky_type, "baked_sky": True}
    if sun and params.get("sun_disc", True):
        e, r = sky.sun_elevation, sky.sun_rotation
        # Blender: rotation 0 puts the sun toward +Y, 90 degrees toward +X (measured against Cycles).
        out["sun"] = {"elevation": e, "rotation": r,
                      "direction": [math.sin(r) * math.cos(e), math.cos(r) * math.cos(e), math.sin(e)],
                      "size": getattr(sky, "sun_size", 0.0095),
                      "energy_rgb": [c * strength for c in sun]}   # light energy (linear, per channel) that lights a white floor like Cycles
    return out


def _render_sky(sky, img_path):
    """Renders the panorama, and returns the sun disc's irradiance (facing the sun) per channel, or None."""
    import math
    import numpy as np
    sc = bpy.data.scenes.new("rustic_sky_bake")
    world = bpy.data.worlds.new("rustic_sky_bake")
    objs, meshes, cams, mats = [], [], [], []
    try:
        sc.render.engine = "CYCLES"
        sc.cycles.samples = 16
        sc.cycles.device = "CPU"
        sc.view_settings.view_transform = "Standard"
        sc.world = world
        world.use_nodes = True
        nt = world.node_tree
        node = nt.nodes.new("ShaderNodeTexSky")
        for p in SKY_PROPS:
            if hasattr(sky, p):
                try:
                    setattr(node, p, getattr(sky, p))
                except (AttributeError, TypeError):
                    pass
        node.sun_disc = False
        nt.links.new(node.outputs[0], nt.nodes["Background"].inputs[0])
        cam = bpy.data.cameras.new("rustic_sky_cam"); cams.append(cam)
        cam.type = "PANO"
        cam.panorama_type = "EQUIRECTANGULAR"
        co = bpy.data.objects.new("rustic_sky_cam", cam); objs.append(co)
        co.rotation_euler = (math.pi / 2, 0, -math.pi / 2)   # centre of the image = +X, like a world HDRI
        sc.collection.objects.link(co)
        sc.camera = co
        sc.render.resolution_x, sc.render.resolution_y = 512, 256
        sc.render.image_settings.file_format = "OPEN_EXR"
        sc.render.image_settings.color_depth = "16"
        sc.render.filepath = img_path
        bpy.ops.render.render(write_still=True, scene=sc.name)

        if not getattr(sky, "sun_disc", False) or sky.sun_elevation <= 0:
            return None
        # Sun irradiance: a white floor lit with and without the sun disc; the difference / sin(elevation).
        me = bpy.data.meshes.new("rustic_sky_floor"); meshes.append(me)
        me.from_pydata([(-500, -500, 0), (500, -500, 0), (500, 500, 0), (-500, 500, 0)], [], [(0, 1, 2, 3)])
        fl = bpy.data.objects.new("rustic_sky_floor", me); objs.append(fl)
        m = bpy.data.materials.new("rustic_sky_white"); mats.append(m)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (1, 1, 1, 1)
        b.inputs["Roughness"].default_value = 1.0
        b.inputs["Specular IOR Level"].default_value = 0.0
        me.materials.append(m)
        sc.collection.objects.link(fl)
        cam.type = "ORTHO"; cam.ortho_scale = 0.1
        co.location = (0, 0, 1); co.rotation_euler = (0, 0, 0)
        sc.render.resolution_x = sc.render.resolution_y = 8
        sc.cycles.samples = 64
        vals = []
        for disc in (True, False):
            node.sun_disc = disc
            path = img_path + (".disc.exr" if disc else ".nodisc.exr")
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True, scene=sc.name)
            im = bpy.data.images.load(path, check_existing=False)
            vals.append(np.array(im.pixels[:]).reshape(-1, 4)[:, :3].mean(0))
            bpy.data.images.remove(im)
            os.remove(path)
        # White Lambert floor: radiance = irradiance / pi, Godot draws albedo * energy * cos -> energy = radiance diff / sin(e)
        return [float(max(v, 0.0)) / math.sin(sky.sun_elevation) for v in (vals[0] - vals[1])]
    finally:
        for o in objs:
            bpy.data.objects.remove(o)
        for me in meshes:
            bpy.data.meshes.remove(me)
        for c in cams:
            bpy.data.cameras.remove(c)
        for m in mats:
            bpy.data.materials.remove(m)
        bpy.data.scenes.remove(sc)
        bpy.data.worlds.remove(world)
