# SPDX-License-Identifier: GPL-3.0-or-later
"""Ask Ember from inside Blender.

The question goes to the RusticEngine editor that has this project open (through two small files in
<project>/.godot/rustic/, like the live link): the editor's Ember answers with what it can see of the
Blender scene (mode, selection, mesh counts, modifiers...) and the Blender library, and the reply is
shown here while it is written. Ember teaches here: it never changes the Blender scene.
"""
import json
import os
import re
import textwrap
import time
import uuid

import bpy
from bpy.props import StringProperty

_state = {"id": "", "question": "", "text": "", "done": True, "asked_at": 0.0, "project": "", "history": []}


def _project(context):
    from . import default_target, find_project, _prefs
    prefs = _prefs(context)
    for path in (default_target(context), bpy.path.abspath(prefs.project_dir) if prefs and prefs.project_dir else ""):
        if path:
            p = find_project(path if os.path.isdir(path) else os.path.dirname(path)) or find_project(path)
            if p:
                return p
    return ""


def _connected(project):
    try:
        return time.time() - os.path.getmtime(os.path.join(project, ".godot", "rustic", "editor_alive")) < 6
    except OSError:
        return False


def describe(context):
    """One line about what the creator is looking at, for Ember."""
    parts = [f"in Blender {bpy.app.version_string}: " + (os.path.basename(bpy.data.filepath) or "unsaved file")]
    mode = context.mode
    if mode == "EDIT_MESH":
        sel = context.tool_settings.mesh_select_mode
        kind = "/".join(n for n, on in zip(("vertex", "edge", "face"), sel) if on)
        parts.append(f"Edit Mode ({kind} select)")
    else:
        parts.append(mode.replace("_", " ").title() + " Mode")
    try:
        tool = context.workspace.tools.from_space_view3d_mode(mode, create=False)
        if tool:
            parts.append("active tool " + tool.idname.replace("builtin.", "").replace("_", " "))
    except Exception:
        pass
    ob = context.active_object
    if ob:
        desc = f"active object {ob.name} ({ob.type}"
        if ob.type == "MESH":
            me = ob.data
            if ob.mode == "EDIT":
                import bmesh
                bm = bmesh.from_edit_mesh(me)
                sv = sum(v.select for v in bm.verts)
                se = sum(e.select for e in bm.edges)
                sf = sum(f.select for f in bm.faces)
                desc += f", {len(bm.verts)} vertices, {len(bm.edges)} edges, {len(bm.faces)} faces; selected {sv} vertices, {se} edges, {sf} faces"
            else:
                tris = sum(len(p.vertices) - 2 for p in me.polygons)
                desc += f", {len(me.vertices)} vertices, {len(me.polygons)} faces, {tris} triangles, {len(me.uv_layers)} UV maps"
        d = ob.dimensions
        desc += f", size {d.x:.2f} x {d.y:.2f} x {d.z:.2f} m"
        s = ob.scale
        if max(abs(s.x - 1), abs(s.y - 1), abs(s.z - 1)) > 1e-4:
            desc += f", scale not applied ({s.x:.2f}, {s.y:.2f}, {s.z:.2f})"
        if ob.modifiers:
            desc += ", modifiers: " + ", ".join(f"{m.name} ({m.type.title()})" for m in ob.modifiers)
        mats = [s.material.name for s in getattr(ob, "material_slots", []) if s.material]
        if mats:
            desc += ", materials: " + ", ".join(mats[:6])
        parts.append(desc + ")")
    others = [o.name for o in context.selected_objects if o != ob]
    if others:
        parts.append(f"also selected {len(others)} objects: " + ", ".join(others[:8]))
    parts.append(f"render engine {context.scene.render.engine.replace('BLENDER_', '').title()}")
    return "; ".join(parts)


def _redraw():
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type in {"VIEW_3D", "NODE_EDITOR"}:
                area.tag_redraw()


def _poll():
    st = _state
    if st["done"] or not st["id"]:
        return None
    try:
        with open(os.path.join(st["project"], ".godot", "rustic", "blender_reply.json"), encoding="utf-8") as f:
            reply = json.load(f)
    except (OSError, ValueError):
        reply = {}
    if reply.get("id") == st["id"] or reply.get("busy"):
        st["text"] = reply.get("text", "")
        st["started"] = True
        if reply.get("done"):
            st["done"] = True
            st["history"] = (st["history"] + [(st["question"], st["text"])])[-5:]
    elif time.time() - st["asked_at"] > 8 and not st.get("started"):
        st["done"] = True
        st["text"] = "RusticEngine didn't pick up the question. Is this project open in the editor?"
    _redraw()
    return None if st["done"] else 0.3


class RUSTIC_OT_ember_ask(bpy.types.Operator):
    """Ask Ember (in the RusticEngine editor) about what you're doing in Blender"""
    bl_idname = "rustic.ember_ask"
    bl_label = "Ask Ember"

    question: StringProperty(default="", options={"SKIP_SAVE"})

    def execute(self, context):
        wm = context.window_manager
        q = (self.question or wm.rustic_ember_question).strip()
        if not q:
            self.report({"WARNING"}, "Type a question for Ember first")
            return {"CANCELLED"}
        project = _project(context)
        if not project:
            self.report({"ERROR"}, "No RusticEngine project: export once (or set the project folder in the add-on preferences)")
            return {"CANCELLED"}
        if not _connected(project):
            self.report({"ERROR"}, "Open this project in RusticEngine: Ember lives in the editor")
            return {"CANCELLED"}
        if not _state["done"]:
            self.report({"WARNING"}, "Ember is still answering")
            return {"CANCELLED"}
        qid = uuid.uuid4().hex
        msg = {"id": qid, "text": q, "context": describe(context), "time": time.time()}
        d = os.path.join(project, ".godot", "rustic")
        os.makedirs(d, exist_ok=True)
        tmp = os.path.join(d, "blender_ask.json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(msg, f)
        os.replace(tmp, os.path.join(d, "blender_ask.json"))
        _state.update(id=qid, question=q, text="", done=False, asked_at=time.time(), project=project, started=False)
        wm.rustic_ember_question = ""
        if not bpy.app.timers.is_registered(_poll):
            bpy.app.timers.register(_poll, first_interval=0.3)
        return {"FINISHED"}


class RUSTIC_OT_ember_text(bpy.types.Operator):
    """Open Ember's answers in the Text Editor (easier to read long ones)"""
    bl_idname = "rustic.ember_text"
    bl_label = "Open in Text Editor"

    def execute(self, context):
        txt = bpy.data.texts.get("Ember") or bpy.data.texts.new("Ember")
        txt.clear()
        for q, a in _state["history"] or [(_state["question"], _state["text"])]:
            txt.write(f"You: {q}\n\nEmber:\n{a}\n\n" + "-" * 60 + "\n\n")
        for area in context.screen.areas:
            if area.type == "TEXT_EDITOR":
                area.spaces.active.text = txt
                return {"FINISHED"}
        self.report({"INFO"}, "Saved to the text \"Ember\": open it in a Text Editor")
        return {"FINISHED"}


def _plain(md):
    md = re.sub(r"\*\*(.+?)\*\*", r"\1", md)
    md = re.sub(r"`([^`]+)`", r"\1", md)
    return re.sub(r"^#+\s*", "", md, flags=re.M)


def _wrapped(layout, text, width):
    chars = max(20, int(width / 7))
    col = layout.column(align=True)
    col.scale_y = 0.8
    for para in _plain(text).split("\n"):
        if not para.strip():
            col.separator(factor=0.5)
            continue
        indent = re.match(r"\s*(?:[-*]|\d+[.)])\s+", para)
        sub = " " * len(indent.group(0)) if indent else ""
        for i, line in enumerate(textwrap.wrap(para.strip(), chars - len(sub)) or [""]):
            col.label(text=(line if i == 0 else sub + line))


class RUSTIC_PT_ember(bpy.types.Panel):
    bl_label = "Ember"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "RusticEngine"

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        project = _project(context)
        if not project:
            layout.label(text="Export once to link a project", icon="INFO")
        elif not _connected(project):
            layout.label(text="Open the project in RusticEngine", icon="INFO")
        row = layout.row(align=True)
        row.prop(wm, "rustic_ember_question", text="", placeholder="Ask Ember...")
        row.operator(RUSTIC_OT_ember_ask.bl_idname, text="", icon="PLAY")
        st = _state
        if st["question"]:
            box = layout.box()
            box.label(text=st["question"][:60], icon="USER")
            if not st["done"] and not st["text"]:
                box.label(text="Ember is thinking...", icon="SORTTIME")
            _wrapped(box, st["text"], context.region.width - 30)
            if st["done"] and st["text"]:
                box.operator(RUSTIC_OT_ember_text.bl_idname, icon="TEXT")


classes = (RUSTIC_OT_ember_ask, RUSTIC_OT_ember_text, RUSTIC_PT_ember)


def register():
    bpy.types.WindowManager.rustic_ember_question = StringProperty(
        name="Question", description="Ask Ember about what you're doing (press Enter, then the arrow)")


def unregister():
    if bpy.app.timers.is_registered(_poll):
        bpy.app.timers.unregister(_poll)
    del bpy.types.WindowManager.rustic_ember_question
