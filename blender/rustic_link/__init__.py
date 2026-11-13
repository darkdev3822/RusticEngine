# SPDX-License-Identifier: GPL-3.0-or-later
"""RusticEngine Link: exports a standard .glb that also carries the real shader node graphs
(glTF extension RUSTIC_blender_nodes), so RusticEngine can rebuild procedural materials."""

bl_info = {
    "name": "RusticEngine Link",
    "author": "RusticEngine",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "File > Export > RusticEngine (.glb) | 3D View > Sidebar > RusticEngine",
    "description": "Send scenes to RusticEngine with procedural materials intact",
    "category": "Import-Export",
}

import os

import bpy
from bpy.props import BoolProperty, StringProperty
from bpy_extras.io_utils import ExportHelper

from . import graph

EXTENSION_NAME = "RUSTIC_blender_nodes"


class glTF2ExportUserExtension:
    """Picked up by Blender's glTF exporter for every enabled add-on that defines it."""

    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
        self.Extension = Extension

    def gather_material_hook(self, gltf2_material, blender_material, export_settings):
        if blender_material is None:
            return
        path = export_settings.get("gltf_filepath", "")
        glb_dir = os.path.dirname(os.path.abspath(path)) if path else ""
        stem = os.path.splitext(os.path.basename(path))[0] if path else "export"
        ctx = {"glb_dir": glb_dir, "texture_dir": os.path.join(glb_dir, stem + "_textures") if glb_dir else ""}
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


def export_glb(filepath, use_selection=False):
    """Exports the scene the way RusticEngine wants it. Returns the written path."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format="GLB",
        use_selection=use_selection,
        export_apply=True,          # modifiers (incl. Geometry Nodes) as evaluated meshes
        export_yup=True,
        export_extras=True,
        export_cameras=True,
        export_lights=True,
        export_materials="EXPORT",
    )
    return filepath


def default_target(context):
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
        self.report({"INFO"}, f"Sent to RusticEngine: {self.filepath}")
        return {"FINISHED"}


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
        last = context.window_manager.rustic_last_export
        if last:
            col.label(text="Last: " + os.path.basename(last), icon="CHECKMARK")


def _menu(self, context):
    self.layout.operator(RUSTIC_OT_export.bl_idname, text="RusticEngine (.glb)")


_classes = (RUSTIC_Preferences, RUSTIC_OT_export, RUSTIC_PT_panel)


def register():
    for c in _classes:
        bpy.utils.register_class(c)
    bpy.types.WindowManager.rustic_last_export = StringProperty()
    bpy.types.TOPBAR_MT_file_export.append(_menu)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(_menu)
    del bpy.types.WindowManager.rustic_last_export
    for c in reversed(_classes):
        bpy.utils.unregister_class(c)
