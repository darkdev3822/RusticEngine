# SPDX-License-Identifier: GPL-3.0-or-later
"""Serializes Blender shader node trees into the RUSTIC_blender_nodes glTF extension.

The format is deliberately plain: every node with its type (bl_idname), settings and the
default values of unlinked inputs, plus the links between sockets (by socket identifier).
RusticEngine translates this graph into a Godot shader, so procedural materials survive.
"""
import os

import bpy

FORMAT_VERSION = 1

# Node properties that every node has; everything else on bl_rna is a node setting.
_BASE_PROPS = set(bpy.types.ShaderNode.bl_rna.properties.keys()) | {"rna_type"}


def _value(v):
    """Turns a Blender property / socket value into JSON."""
    if isinstance(v, (bool, int, float, str)) or v is None:
        return v
    try:
        return [_value(x) for x in v]
    except TypeError:
        return str(v)


def _image_entry(image, ctx):
    """Where RusticEngine can find an image: a file next to the .glb (packed/generated images
    are saved there) or the original file on disk."""
    if image is None:
        return None
    entry = {
        "name": image.name,
        "colorspace": image.colorspace_settings.name,
        "alpha_mode": image.alpha_mode,
        "size": list(image.size),
        "source": image.source,
    }
    path = bpy.path.abspath(image.filepath, library=image.library) if image.filepath else ""
    needs_copy = image.packed_file is not None or image.source == "GENERATED" or not path or not os.path.isfile(path)
    out_dir = ctx.get("texture_dir")
    if needs_copy and out_dir and image.source in {"FILE", "GENERATED"}:
        os.makedirs(out_dir, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in image.name)
        if not safe.lower().endswith((".png", ".jpg", ".jpeg", ".exr", ".webp")):
            safe += ".png"
        dest = os.path.join(out_dir, safe)
        copy = image.copy()
        try:
            copy.filepath_raw = dest
            copy.file_format = "OPEN_EXR" if safe.lower().endswith(".exr") else "PNG"
            copy.save()
        finally:
            bpy.data.images.remove(copy)
        path = dest
    if path:
        entry["path"] = os.path.abspath(path)
        glb_dir = ctx.get("glb_dir")
        if glb_dir:
            try:
                entry["relative_path"] = os.path.relpath(path, glb_dir).replace(os.sep, "/")
            except ValueError:
                pass
    return entry


def _color_ramp(ramp):
    return {
        "interpolation": ramp.interpolation,
        "color_mode": ramp.color_mode,
        "hue_interpolation": ramp.hue_interpolation,
        "elements": [{"position": e.position, "color": list(e.color)} for e in ramp.elements],
    }


def _curve_mapping(mapping, samples=256):
    """Curves are sampled into lookup tables (0..1 in, per curve)."""
    mapping.initialize()
    lut = []
    for curve in mapping.curves:
        lut.append([mapping.evaluate(curve, i / (samples - 1)) for i in range(samples)])
    return {"samples": samples, "curves": lut, "black_level": list(mapping.black_level), "white_level": list(mapping.white_level)}


def _node_settings(node, ctx):
    props = {}
    for p in node.bl_rna.properties:
        key = p.identifier
        if key in _BASE_PROPS or p.is_readonly and p.type != "POINTER":
            continue
        if p.type in {"BOOLEAN", "INT", "FLOAT", "STRING", "ENUM"}:
            try:
                props[key] = _value(getattr(node, key))
            except Exception:
                pass
    if hasattr(node, "color_ramp") and node.color_ramp is not None:
        props["color_ramp"] = _color_ramp(node.color_ramp)
    if hasattr(node, "mapping") and isinstance(getattr(node, "mapping", None), bpy.types.CurveMapping):
        props["curve_mapping"] = _curve_mapping(node.mapping)
    if getattr(node, "image", None) is not None or node.bl_idname in {"ShaderNodeTexImage", "ShaderNodeTexEnvironment"}:
        props["image"] = _image_entry(node.image, ctx)
        if node.bl_idname == "ShaderNodeTexImage":
            props["image_user"] = {"frame_offset": node.image_user.frame_offset}
    if node.bl_idname == "ShaderNodeGroup" and node.node_tree is not None:
        props["group"] = serialize_tree(node.node_tree, ctx)
    return props


def _socket(sock):
    s = {"identifier": sock.identifier, "name": sock.name, "type": sock.type}
    if hasattr(sock, "default_value"):
        s["default"] = _value(sock.default_value)
    return s


def serialize_tree(tree, ctx):
    nodes = []
    for node in tree.nodes:
        if node.bl_idname in {"NodeFrame"}:
            continue
        nodes.append({
            "name": node.name,
            "type": node.bl_idname,
            "label": node.label,
            "mute": node.mute,
            "settings": _node_settings(node, ctx),
            "inputs": [_socket(s) for s in node.inputs if s.enabled],
            "outputs": [_socket(s) for s in node.outputs if s.enabled],   # RGB/Value nodes keep their value here
        })
    links = []
    for link in tree.links:
        if not link.is_valid or link.is_muted:
            continue
        links.append({
            "from_node": link.from_node.name, "from_socket": link.from_socket.identifier,
            "to_node": link.to_node.name, "to_socket": link.to_socket.identifier,
        })
    out = {"nodes": nodes, "links": links}
    if tree.bl_idname == "ShaderNodeTree" and getattr(tree, "interface", None) is not None:
        out["interface"] = [
            {"identifier": i.identifier, "name": i.name, "in_out": i.in_out, "socket_type": getattr(i, "socket_type", "")}
            for i in tree.interface.items_tree if i.item_type == "SOCKET"
        ]
    return out


def active_output_name(tree):
    best = None
    for node in tree.nodes:
        if node.bl_idname == "ShaderNodeOutputMaterial":
            if node.is_active_output:
                return node.name
            if best is None or node.target in {"ALL", "EEVEE"}:
                best = node.name
    return best


def serialize_material(mat, ctx, tree=None):
    """tree: an already-inlined node tree (groups flattened) to use instead of mat.node_tree."""
    data = {
        "version": FORMAT_VERSION,
        "blender": bpy.app.version_string,
        "material": mat.name,
        "use_nodes": bool(getattr(mat, "use_nodes", True) and mat.node_tree),
        "settings": {
            "backface_culling": mat.use_backface_culling,
            "render_method": getattr(mat, "surface_render_method", "DITHERED"),
            "blend_method": getattr(mat, "blend_method", "OPAQUE"),
            "diffuse_color": list(mat.diffuse_color),
            "roughness": mat.roughness,
            "metallic": mat.metallic,
        },
    }
    if data["use_nodes"]:
        tree = tree or mat.node_tree
        data["tree"] = serialize_tree(tree, ctx)
        data["output"] = active_output_name(tree)
        data["inlined"] = tree is not mat.node_tree
    return data
