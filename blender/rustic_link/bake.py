# SPDX-License-Identifier: GPL-3.0-or-later
"""Bake fallback: materials RusticEngine can't rebuild from nodes are baked into images at export.

RusticEngine decides what it can rebuild: after each import it writes a report
(<project>/.godot/rustic/blender/<path>.json). Materials it kept as plain glTF (result != "translated")
are baked on the next export, as are materials marked "Always bake". Each object gets its own bake
(on its evaluated mesh, so it matches what is exported), cached on disk until the material, mesh or
size changes. The exported .glb then carries a simple Principled material with the baked images.
"""
import hashlib
import json
import os

import bpy

from . import graph

CHANNELS = ("base", "roughness", "metallic", "emission", "alpha", "normal")


def report_file(glb):
    from . import find_project
    project = find_project(glb)
    if not project:
        return ""
    rel = os.path.splitext(os.path.relpath(os.path.abspath(glb), project))[0].replace(os.sep, "/")
    return os.path.join(project, ".godot", "rustic", "blender", rel.replace("/", "_") + ".json")


def plain_materials(glb):
    """{material name: why} for materials the last import kept as plain glTF."""
    try:
        with open(report_file(glb), encoding="utf-8") as f:
            rep = json.load(f)
    except (OSError, ValueError):
        return {}
    out = {}
    for m in rep.get("materials", []):
        if m.get("result") != "translated":
            name = m.get("material", "")
            if name.endswith(" (baked)"):
                continue
            out[name] = (m.get("problems") or ["kept the standard material"])[0]
    return out


def wanted(scene, glb):
    """Materials to bake: marked Always Bake, plus (with Auto-Bake) what RusticEngine couldn't rebuild last
    time. Those are remembered on the material, because once baked the next report shows them as fine."""
    names = {m.name for m in bpy.data.materials if getattr(m, "rustic_bake", False)}
    if scene.rustic.auto_bake:
        for name in plain_materials(glb):
            mat = bpy.data.materials.get(name)
            if mat is not None:
                mat["rustic_auto_baked"] = True
        names |= {m.name for m in bpy.data.materials if m.get("rustic_auto_baked")}
    return names


def _bsdf(nt):
    out = nt.get_output_node("CYCLES") or nt.get_output_node("ALL")
    if not out or not out.inputs["Surface"].is_linked:
        return out, None
    node = out.inputs["Surface"].links[0].from_node
    return out, node if node.bl_idname == "ShaderNodeBsdfPrincipled" else None


def _channels(mat):
    """Which images this material needs."""
    _out, bsdf = _bsdf(mat.node_tree)
    if bsdf is None:
        return ["base"]   # mixes of shaders etc.: bake the overall color
    chans = ["base"]
    for ch, sock in (("roughness", "Roughness"), ("metallic", "Metallic"), ("emission", "Emission Color"), ("alpha", "Alpha"), ("normal", "Normal")):
        if bsdf.inputs[sock].is_linked:
            chans.append(ch)
    return chans


def _safe(s):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s)


def _cache_key(mat, mesh, size):
    h = hashlib.sha1()
    h.update(json.dumps(graph.serialize_material(mat, {}), sort_keys=True, default=str).encode())
    h.update(f"{size}|{len(mesh.vertices)}|{len(mesh.polygons)}".encode())
    if mesh.uv_layers.active:
        import numpy as np
        uv = np.empty(len(mesh.loops) * 2, dtype=np.float32)
        mesh.uv_layers.active.data.foreach_get("uv", uv)
        h.update(uv.tobytes())
        co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", co)
        h.update(co.tobytes())
    return h.hexdigest()


def _temp_object(ob, slot_index, depsgraph):
    """A temporary object with the evaluated mesh, only the faces using this slot, one material slot."""
    import bmesh
    mesh = bpy.data.meshes.new_from_object(ob.evaluated_get(depsgraph), preserve_all_data_layers=True, depsgraph=depsgraph)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != slot_index], context="FACES")
    for f in bm.faces:
        f.material_index = 0
    bm.to_mesh(mesh)
    bm.free()
    while len(mesh.materials) > 1:
        mesh.materials.pop()
    tmp = bpy.data.objects.new("rustic_bake_tmp", mesh)
    tmp.matrix_world = ob.matrix_world
    bpy.context.scene.collection.objects.link(tmp)
    return tmp


def _bake_into(tmp, mat, chans, size, out_dir, stem):
    """Bakes each channel of `mat` on `tmp` into PNGs. Returns {channel: path}."""
    work = mat.copy()
    tmp.data.materials.clear()
    tmp.data.materials.append(work)
    nt = work.node_tree
    out, bsdf = _bsdf(nt)
    surface_src = out.inputs["Surface"].links[0].from_socket if out and out.inputs["Surface"].is_linked else None
    paths = {}
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(False)
    tmp.select_set(True)
    vl.objects.active = tmp
    try:
        for ch in chans:
            img = bpy.data.images.new(f"{stem}_{ch}", size, size, alpha=(ch == "base"), float_buffer=False)
            img.colorspace_settings.name = "sRGB" if ch in ("base", "emission") else "Non-Color"
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = img
            nt.nodes.active = tex
            emit = None
            kwargs = {}
            if ch == "normal":
                kind = "NORMAL"
                kwargs = {"normal_space": "TANGENT"}
            elif bsdf is None:
                kind = "DIFFUSE"
                kwargs = {"pass_filter": {"COLOR"}}
            else:
                kind = "EMIT"
                sock = bsdf.inputs[{"base": "Base Color", "roughness": "Roughness", "metallic": "Metallic",
                                    "emission": "Emission Color", "alpha": "Alpha"}[ch]]
                emit = nt.nodes.new("ShaderNodeEmission")
                if sock.is_linked:
                    nt.links.new(sock.links[0].from_socket, emit.inputs["Color"])
                else:
                    v = sock.default_value
                    emit.inputs["Color"].default_value = tuple(v) if hasattr(v, "__len__") else (v, v, v, 1.0)
                nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
            bpy.ops.object.bake(type=kind, margin=16, use_clear=True, **kwargs)
            if emit is not None:
                nt.nodes.remove(emit)
                if surface_src is not None:
                    nt.links.new(surface_src, out.inputs["Surface"])
            path = os.path.join(out_dir, f"{stem}_{ch}.png")
            img.filepath_raw = path
            img.file_format = "PNG"
            img.save()
            bpy.data.images.remove(img)
            nt.nodes.remove(tex)
            paths[ch] = path
    finally:
        bpy.data.materials.remove(work)
    return paths


def _baked_material(mat, paths):
    """A plain Principled material with the baked images (what the .glb gets)."""
    new = bpy.data.materials.new(mat.name + " (baked)")
    new.use_nodes = True
    for attr in ("blend_method", "use_backface_culling", "alpha_threshold"):
        if hasattr(mat, attr):
            try:
                setattr(new, attr, getattr(mat, attr))
            except (AttributeError, TypeError):
                pass
    nt = new.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    _o, src = _bsdf(mat.node_tree)
    if src is not None:   # keep the values that weren't baked
        for sock in ("Roughness", "Metallic", "Emission Strength", "IOR", "Alpha"):
            if not src.inputs[sock].is_linked:
                bsdf.inputs[sock].default_value = src.inputs[sock].default_value
    for ch, path in paths.items():
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(path, check_existing=True)
        if ch not in ("base", "emission"):
            tex.image.colorspace_settings.name = "Non-Color"
        if ch == "base":
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        elif ch == "normal":
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nt.links.new(tex.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
        else:
            sock = {"roughness": "Roughness", "metallic": "Metallic", "emission": "Emission Color", "alpha": "Alpha"}[ch]
            nt.links.new(tex.outputs["Color"], bsdf.inputs[sock])
            if ch == "emission" and src is not None and src.inputs["Emission Strength"].default_value == 0:
                bsdf.inputs["Emission Strength"].default_value = 1.0
    new["rustic_baked_from"] = mat.name
    return new


class BakeSwap:
    """Used around the glTF export: bakes what's wanted and swaps the baked materials in, then restores."""

    def __init__(self, scene, glb, use_selection=False):
        self.scene, self.glb, self.use_selection = scene, glb, use_selection
        self.restore, self.temp_mats, self.notes, self.baked = [], [], [], []

    def __enter__(self):
        names = wanted(self.scene, self.glb)
        if not names:
            return self
        stem = os.path.splitext(os.path.basename(self.glb))[0]
        out_dir = os.path.join(os.path.dirname(os.path.abspath(self.glb)), stem + "_textures", "baked")
        os.makedirs(out_dir, exist_ok=True)
        render = self.scene.render
        saved = (render.engine, self.scene.cycles.samples, self.scene.render.bake.margin)
        vl = bpy.context.view_layer
        sel = [o for o in vl.objects if o.select_get()]
        active = vl.objects.active
        mode = active.mode if active else "OBJECT"
        if mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        render.engine = "CYCLES"
        self.scene.cycles.samples = 4
        depsgraph = bpy.context.evaluated_depsgraph_get()
        try:
            objs = [o for o in self.scene.objects if o.type == "MESH" and (not self.use_selection or o in sel)]
            for ob in objs:
                for i, slot in enumerate(ob.material_slots):
                    mat = slot.material
                    if mat is None or mat.name not in names or not mat.use_nodes:
                        continue
                    ev = ob.evaluated_get(depsgraph).data
                    if not ev.uv_layers:
                        self.notes.append(f"{ob.name}: {mat.name} needs a UV map to bake (U > Smart UV Project)")
                        continue
                    if not any(p.material_index == i for p in ev.polygons):
                        continue
                    tag = f"{_safe(mat.name)}__{_safe(ob.name)}"
                    size = int(self.scene.rustic.bake_size)
                    key = _cache_key(mat, ev, size)
                    chans = _channels(mat)
                    side = os.path.join(out_dir, tag + ".json")
                    paths = {ch: os.path.join(out_dir, f"{tag}_{ch}.png") for ch in chans}
                    try:
                        cached = json.load(open(side)).get("key") == key and all(os.path.isfile(p) for p in paths.values())
                    except (OSError, ValueError):
                        cached = False
                    if not cached:
                        tmp = _temp_object(ob, i, depsgraph)
                        try:
                            paths = _bake_into(tmp, mat, chans, size, out_dir, tag)
                        finally:
                            m = tmp.data
                            bpy.data.objects.remove(tmp)
                            bpy.data.meshes.remove(m)
                        with open(side, "w") as f:
                            json.dump({"key": key, "material": mat.name, "object": ob.name}, f)
                    baked = _baked_material(mat, paths)
                    self.temp_mats.append(baked)
                    self.restore.append((ob, i, slot.link, mat))
                    slot.link = "OBJECT"
                    slot.material = baked
                    self.baked.append(f"{mat.name} on {ob.name}" + (" (cached)" if cached else ""))
        finally:
            render.engine, self.scene.cycles.samples, self.scene.render.bake.margin = saved
            for o in vl.objects:
                o.select_set(o in sel)
            vl.objects.active = active
            if mode != "OBJECT" and active:
                bpy.ops.object.mode_set(mode=mode)
        return self

    def __exit__(self, *exc):
        for ob, i, link, mat in reversed(self.restore):
            slot = ob.material_slots[i]
            slot.material = None
            slot.link = link
            if link == "OBJECT":
                slot.material = mat
        for m in self.temp_mats:
            imgs = [n.image for n in m.node_tree.nodes if n.bl_idname == "ShaderNodeTexImage" and n.image]
            bpy.data.materials.remove(m)
            for img in imgs:
                if img.users == 0:
                    bpy.data.images.remove(img)
        return False
