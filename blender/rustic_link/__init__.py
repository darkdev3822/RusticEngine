# SPDX-License-Identifier: GPL-3.0-or-later
"""RusticEngine Link: exports a standard .glb that also carries the real shader node graphs
(glTF extension RUSTIC_blender_nodes), so RusticEngine can rebuild procedural materials."""

bl_info = {
    "name": "RusticEngine Link",
    "author": "RusticEngine",
    "version": (0, 5, 0),
    "blender": (4, 2, 0),
    "location": "File > Export > RusticEngine (.glb) | 3D View > Sidebar > RusticEngine",
    "description": "Send scenes to RusticEngine with procedural materials intact",
    "category": "Import-Export",
}

import json
import os
import time

import bpy
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, EnumProperty, PointerProperty, StringProperty
from bpy_extras.io_utils import ExportHelper

from . import graph, refs, ember, bake, scene_data

EXTENSION_NAME = "RUSTIC_blender_nodes"
_final_path = ""   # real destination while exporting through a temp file


class glTF2ExportUserExtension:
    """Picked up by Blender's glTF exporter for every enabled add-on that defines it."""

    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
        self.Extension = Extension

    @staticmethod
    def _ctx(export_settings):
        path = _final_path or export_settings.get("gltf_filepath", "")
        glb_dir = os.path.dirname(os.path.abspath(path)) if path else ""
        stem = os.path.splitext(os.path.basename(path))[0] if path else "export"
        return {"glb_dir": glb_dir, "texture_dir": os.path.join(glb_dir, stem + "_textures") if glb_dir else ""}

    def _add(self, gltf_obj, name, data):
        if gltf_obj.extensions is None:
            gltf_obj.extensions = {}
        gltf_obj.extensions[name] = self.Extension(name=name, extension=data, required=False)

    def gather_node_hook(self, gltf2_node, blender_object, export_settings):
        if blender_object is not None and getattr(blender_object, "type", "") == "LIGHT":
            self._add(gltf2_node, scene_data.LIGHT_EXT, scene_data.light_data(blender_object.data))

    def gather_scene_hook(self, gltf2_scene, blender_scene, export_settings):
        if blender_scene is not None:
            self._add(gltf2_scene, scene_data.WORLD_EXT, scene_data.world_data(blender_scene, self._ctx(export_settings)))

    def gather_material_hook(self, gltf2_material, blender_material, export_settings):
        if blender_material is None:
            return
        ctx = self._ctx(export_settings)
        # Blender 5.x passes an InlineShaderNodes (node groups already flattened); 4.x the Material.
        if isinstance(blender_material, bpy.types.Material):
            mat, tree = blender_material, None
        else:
            mat = bpy.data.materials.get(gltf2_material.name or "")
            tree = getattr(blender_material, "node_tree", None)
            if mat is None:
                return
        if gltf2_material.extensions is None:
            gltf2_material.extensions = {}
        gltf2_material.extensions[EXTENSION_NAME] = self.Extension(
            name=EXTENSION_NAME, extension=graph.serialize_material(mat, ctx, tree), required=False)


def _prefs(context):
    addon = context.preferences.addons.get(__package__)
    return addon.preferences if addon else None


def find_project(path):
    """The folder holding project.godot above `path`, or ""."""
    d = os.path.dirname(os.path.abspath(path))
    while True:
        if os.path.isfile(os.path.join(d, "project.godot")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return ""
        d = parent


def export_glb(filepath, use_selection=False):
    """Exports the scene the way RusticEngine wants it, then tells an open editor. Returns the written path.

    Writes through a hidden temp folder and renames, so the editor never imports a half-written file."""
    global _final_path
    filepath = os.path.abspath(filepath)
    tmp_dir = os.path.join(os.path.dirname(filepath), ".rustic_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp = os.path.join(tmp_dir, os.path.basename(filepath))
    _final_path = filepath
    wm = bpy.context.window_manager
    try:
        # Materials RusticEngine can't rebuild from nodes get baked into images and swapped in for the export.
        with bake.BakeSwap(bpy.context.scene, filepath, use_selection) as baked:
            wm.rustic_bake_note = "; ".join(baked.notes + (["Baked: " + ", ".join(baked.baked)] if baked.baked else []))
            bpy.ops.export_scene.gltf(
                filepath=tmp,
                export_format="GLB",
                use_selection=use_selection,
                export_apply=True,          # modifiers (incl. Geometry Nodes) as evaluated meshes
                export_yup=True,
                export_extras=True,
                export_cameras=True,
                export_lights=True,
                export_materials="EXPORT",
            )
        os.replace(tmp, filepath)
    finally:
        _final_path = ""
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass
    notify_editor(filepath)
    return filepath


def notify_editor(filepath):
    """Writes res://.godot/rustic/blender_link.json; the RusticEngine editor watches it and reimports."""
    project = find_project(filepath)
    if not project:
        return False
    rel = os.path.relpath(filepath, project).replace(os.sep, "/")
    note_dir = os.path.join(project, ".godot", "rustic")
    os.makedirs(note_dir, exist_ok=True)
    note = os.path.join(note_dir, "blender_link.json")
    tmp = note + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"files": ["res://" + rel], "blend": bpy.data.filepath, "time": time.time()}, f)
    os.replace(tmp, note)
    return True


def editor_connected(filepath):
    """True when a RusticEngine editor has this project open (it touches editor_alive every 2 s)."""
    project = find_project(filepath) if filepath else ""
    if not project:
        return False
    try:
        return time.time() - os.path.getmtime(os.path.join(project, ".godot", "rustic", "editor_alive")) < 6
    except OSError:
        return False


def default_target(context):
    target = context.scene.rustic.target if context.scene else ""
    if target:
        return bpy.path.abspath(target)
    prefs = _prefs(context)
    blend = bpy.data.filepath
    name = os.path.splitext(os.path.basename(blend))[0] if blend else "untitled"
    if prefs and prefs.project_dir:
        return os.path.join(bpy.path.abspath(prefs.project_dir), prefs.subfolder, name + ".glb")
    return os.path.join(os.path.dirname(blend), name + ".glb") if blend else ""


class RUSTIC_OT_export(bpy.types.Operator, ExportHelper):
    """Export this scene as a .glb for RusticEngine (procedural materials included)"""
    bl_idname = "rustic.export_glb"
    bl_label = "Export to RusticEngine"
    filename_ext = ".glb"
    filter_glob: StringProperty(default="*.glb", options={"HIDDEN"})
    use_selection: BoolProperty(name="Selected Only", default=False)

    def invoke(self, context, event):
        target = default_target(context)
        prefs = _prefs(context)
        if prefs and prefs.project_dir and target:
            self.filepath = target
            return self.execute(context)        # project set: export straight there
        if target:
            self.filepath = target
        return ExportHelper.invoke(self, context, event)

    def execute(self, context):
        try:
            export_glb(self.filepath, self.use_selection)
        except Exception as e:
            self.report({"ERROR"}, f"Export failed: {e}")
            return {"CANCELLED"}
        context.window_manager.rustic_last_export = self.filepath
        context.scene.rustic.target = self.filepath   # later saves (Live Link) go to the same place
        self.report({"INFO"}, f"Sent to RusticEngine: {self.filepath}")
        return {"FINISHED"}


class RUSTIC_SceneSettings(bpy.types.PropertyGroup):
    live: BoolProperty(name="Live Link", default=False,
                       description="Every time you save the .blend, re-export it to RusticEngine; an open editor updates by itself")
    export_world: BoolProperty(name="Send World", default=True,
                               description="Bring the world (sky or HDRI, background color) and the color management (AgX/Filmic, exposure) into RusticEngine as a WorldEnvironment")
    auto_bake: BoolProperty(name="Auto-Bake", default=True,
                            description="Materials RusticEngine couldn't rebuild from nodes last time are baked into images on export")
    bake_size: EnumProperty(name="Bake Size", default="1024", items=[("512", "512", ""), ("1024", "1024", ""), ("2048", "2048", ""), ("4096", "4096", "")],
                            description="Size of baked images")
    target: StringProperty(name="Export Path", subtype="FILE_PATH",
                           description="Where this .blend is exported (set by the first export)")


@persistent
def _on_save(*_args):
    scene = bpy.context.scene
    if scene is None or not scene.rustic.live:
        return
    target = default_target(bpy.context)
    if not target:
        print("RusticEngine Live Link: set a project in the RusticEngine panel first")
        return
    try:
        export_glb(target)
        bpy.context.window_manager.rustic_last_export = target
        scene.rustic.target = target
        print("RusticEngine Live Link: sent", target)
    except Exception as e:
        print("RusticEngine Live Link: export failed:", e)


class RUSTIC_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    project_dir: StringProperty(name="RusticEngine Project", subtype="DIR_PATH",
                                description="Folder of your RusticEngine project (the one with project.godot)")
    subfolder: StringProperty(name="Folder in Project", default="art/blender",
                              description="Where exported scenes go inside the project")

    def draw(self, context):
        self.layout.prop(self, "project_dir")
        self.layout.prop(self, "subfolder")


class RUSTIC_PT_panel(bpy.types.Panel):
    bl_label = "RusticEngine"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "RusticEngine"

    def draw(self, context):
        prefs = _prefs(context)
        col = self.layout.column()
        if prefs:
            col.prop(prefs, "project_dir", text="Project")
        col.operator(RUSTIC_OT_export.bl_idname, icon="EXPORT")
        col.prop(context.scene.rustic, "live", icon="LINKED")
        col.prop(context.scene.rustic, "export_world", icon="WORLD")
        if context.scene.rustic.live and not bpy.data.filepath:
            col.label(text="Save the .blend to start", icon="INFO")
        target = default_target(context)
        if target:
            ok = editor_connected(target)
            col.label(text="Editor open" if ok else "Editor not open", icon="CHECKMARK" if ok else "RADIOBUT_OFF")
        last = context.window_manager.rustic_last_export
        if last:
            col.label(text="Last: " + os.path.basename(last), icon="FILE_3D")
        self._draw_bake(context)
        refs.draw_panel(self.layout, context)

    def _draw_bake(self, context):
        box = self.layout.box()
        row = box.row()
        row.prop(context.scene.rustic, "auto_bake")
        row.prop(context.scene.rustic, "bake_size", text="")
        target = default_target(context)
        plain = bake.plain_materials(target) if target else {}
        if plain:
            box.label(text="Came in plain last time:", icon="ERROR")
            for name, why in plain.items():
                r = box.row()
                r.label(text=name, icon="MATERIAL")
                r.label(text=why[:48])
            if not context.scene.rustic.auto_bake:
                box.label(text="Turn on Auto-Bake (or Always Bake) and export again")
        mat = context.object.active_material if context.object else None
        if mat:
            box.prop(mat, "rustic_bake", text=f"Always bake '{mat.name}'")
        note = context.window_manager.rustic_bake_note
        if note:
            for line in note.split("; ")[:4]:
                box.label(text=line[:70], icon="IMAGE_DATA")


def _menu(self, context):
    self.layout.operator(RUSTIC_OT_export.bl_idname, text="RusticEngine (.glb)")


_classes = refs.classes + (RUSTIC_SceneSettings, RUSTIC_Preferences, RUSTIC_OT_export, RUSTIC_PT_panel) + ember.classes


def register():
    for c in _classes:
        bpy.utils.register_class(c)
    bpy.types.WindowManager.rustic_last_export = StringProperty()
    bpy.types.WindowManager.rustic_bake_note = StringProperty()
    bpy.types.Material.rustic_bake = BoolProperty(
        name="Always Bake", default=False,
        description="Bake this material into images on every export to RusticEngine (heavy node setups run faster as images)")
    ember.register()
    bpy.types.Scene.rustic = PointerProperty(type=RUSTIC_SceneSettings)
    bpy.types.TOPBAR_MT_file_export.append(_menu)
    if _on_save not in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.append(_on_save)


def unregister():
    if _on_save in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(_on_save)
    bpy.types.TOPBAR_MT_file_export.remove(_menu)
    del bpy.types.Scene.rustic
    del bpy.types.WindowManager.rustic_last_export
    del bpy.types.WindowManager.rustic_bake_note
    del bpy.types.Material.rustic_bake
    ember.unregister()
    for c in reversed(_classes):
        bpy.utils.unregister_class(c)
