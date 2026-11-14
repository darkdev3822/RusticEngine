# SPDX-License-Identifier: GPL-3.0-or-later
"""Reference images that line up by themselves.

Pick front/side/back/top pictures, type how tall the thing really is, and each picture becomes an image
empty that: faces its own orthographic view (and only shows there), finds the subject inside the picture
(ignores the empty background), scales it so the subject is exactly that tall, stands it on the ground
(z = 0) and centres it on the origin. Front and side therefore match exactly, which is the part people
fight with by hand.
"""
import math
import os

import bpy
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, FloatProperty, StringProperty

COLLECTION = "References"
VIEWS = [("FRONT", "Front", "Seen from the front (Numpad 1)"), ("RIGHT", "Right Side", "Seen from the right (Numpad 3)"),
         ("LEFT", "Left Side", "Seen from the left (Ctrl Numpad 3)"), ("BACK", "Back", "Seen from the back (Ctrl Numpad 1)"),
         ("TOP", "Top", "Seen from above (Numpad 7)")]
# Euler rotation that makes the image face the viewer of each ortho view, the world axis of its
# horizontal image axis (sign, axis), and where to push it back along the viewing axis.
ROT = {"FRONT": (90, 0, 0), "BACK": (90, 0, 180), "RIGHT": (90, 0, 90), "LEFT": (90, 0, -90), "TOP": (0, 0, 0)}
H_AXIS = {"FRONT": (1, 0), "BACK": (-1, 0), "RIGHT": (1, 1), "LEFT": (-1, 1), "TOP": (1, 0)}
BEHIND = {"FRONT": (1, 1), "BACK": (-1, 1), "RIGHT": (-1, 0), "LEFT": (1, 0), "TOP": (-1, 2)}


def guess_view(name):
    n = os.path.basename(name).lower()
    for key, view in (("front", "FRONT"), ("back", "BACK"), ("rear", "BACK"), ("left", "LEFT"), ("right", "RIGHT"),
                      ("side", "RIGHT"), ("profile", "RIGHT"), ("top", "TOP"), ("plan", "TOP")):
        if key in n:
            return view
    return ""


def subject_box(img):
    """Pixel box (x0, y0, x1, y1), y up from the bottom, of whatever isn't background.
    Background = transparent pixels if the picture has transparency, else the colour of its corners."""
    import numpy as np
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    alpha = px[..., 3]
    if alpha.min() < 0.5 and (alpha < 0.5).mean() > 0.02:
        mask = alpha > 0.5
    else:
        corners = np.array([px[0, 0, :3], px[0, -1, :3], px[-1, 0, :3], px[-1, -1, :3]])
        bg = np.median(corners, axis=0)
        mask = np.abs(px[..., :3] - bg).max(axis=2) > 0.12
    rows = np.where(mask.mean(axis=1) > 0.002)[0]
    cols = np.where(mask.mean(axis=0) > 0.002)[0]
    if len(rows) < 2 or len(cols) < 2:
        return (0, 0, w, h), False
    return (int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1), True


def place(img, view, meters_per_px, box, opacity, depth_offset, coll):
    w, h = img.size
    x0, y0, x1, y1 = box
    m = meters_per_px
    name = f"Ref {view.title()}"
    old = bpy.data.objects.get(name)
    if old is not None:
        bpy.data.objects.remove(old)
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_type = "IMAGE"
    ob.data = img
    ob.empty_display_size = max(w, h) * m
    ob.empty_image_offset = (-0.5, -0.5)
    ob.rotation_euler = tuple(math.radians(a) for a in ROT[view])
    # Image-local offset of the subject's anchor from the picture centre, in metres:
    # horizontally its centre, vertically its bottom (top view: its centre both ways).
    du = ((x0 + x1) / 2 - w / 2) * m
    dv = (((y0 + y1) / 2 if view == "TOP" else y0) - h / 2) * m
    loc = [0.0, 0.0, 0.0]
    sign, axis = H_AXIS[view]
    loc[axis] = -sign * du
    if view == "TOP":
        loc[1] = -dv
    else:
        loc[2] = -dv
    bsign, baxis = BEHIND[view]
    loc[baxis] += bsign * depth_offset
    ob.location = loc
    ob.color[3] = opacity
    ob.use_empty_image_alpha = True
    ob.empty_image_depth = "BACK"
    ob.empty_image_side = "FRONT"
    ob.show_empty_image_only_axis_aligned = True
    ob.show_empty_image_perspective = False
    ob.show_empty_image_orthographic = True
    coll.objects.link(ob)
    ob.hide_select = True
    ob["rustic_reference"] = view
    return ob


def add_references(files, height, opacity=0.5, real_width=0.0):
    """files: [(path, view)]. Returns (objects, notes)."""
    coll = bpy.data.collections.get(COLLECTION)
    if coll is None:
        coll = bpy.data.collections.new(COLLECTION)
        bpy.context.scene.collection.children.link(coll)
    order = {"FRONT": 0, "BACK": 1, "RIGHT": 2, "LEFT": 3, "TOP": 4}
    files = sorted(files, key=lambda f: order[f[1]])
    obs, notes, width_m = [], [], real_width
    for path, view in files:
        img = bpy.data.images.load(path, check_existing=True)
        box, found = subject_box(img)
        if not found:
            notes.append(f"{os.path.basename(path)}: couldn't tell the subject from the background, used the whole picture")
        bw, bh = box[2] - box[0], box[3] - box[1]
        if view == "TOP":
            # The top view shows width x depth: match its width to the front view's width.
            m = (width_m / bw) if width_m > 0 else (height / max(bw, bh))
        else:
            m = height / bh
            if view in ("FRONT", "BACK") and not width_m:
                width_m = bw * m
        obs.append(place(img, view, m, box, opacity, height * 0.5, coll))
    return obs, notes


class RUSTIC_OT_add_references(bpy.types.Operator):
    """Add reference pictures that line up by themselves: each faces its view, is scaled to the real size and stands on the ground"""
    bl_idname = "rustic.add_references"
    bl_label = "Add Reference Images"
    bl_options = {"REGISTER", "UNDO"}

    directory: StringProperty(subtype="DIR_PATH")
    files: CollectionProperty(type=bpy.types.OperatorFileListElement)
    filter_image: BoolProperty(default=True, options={"HIDDEN"})
    filter_folder: BoolProperty(default=True, options={"HIDDEN"})
    height: FloatProperty(name="Real Height", default=1.8, min=0.001, unit="LENGTH",
                          description="How tall the subject really is (a person ~1.8 m, a longsword ~1.1 m, a mug ~0.1 m)")
    opacity: FloatProperty(name="Opacity", default=0.5, min=0.05, max=1.0)
    first_view: EnumProperty(name="If the name doesn't say", items=VIEWS, default="FRONT",
                             description="Pictures named front/side/back/top are placed automatically; others get this view, then the next ones")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        paths = [os.path.join(self.directory, f.name) for f in self.files if f.name]
        if not paths:
            self.report({"ERROR"}, "Pick one or more pictures")
            return {"CANCELLED"}
        fallback = [v[0] for v in VIEWS]
        fallback = fallback[fallback.index(self.first_view):] + fallback[:fallback.index(self.first_view)]
        chosen, used = [], set()
        for p in paths:
            v = guess_view(p)
            if v and v not in used:
                chosen.append((p, v)); used.add(v)
        for p in paths:
            if p not in [c[0] for c in chosen]:
                v = next((f for f in fallback if f not in used), None)
                if v:
                    chosen.append((p, v)); used.add(v)
        obs, notes = add_references(chosen, self.height, self.opacity)
        for n in notes:
            self.report({"WARNING"}, n)
        views = ", ".join(o["rustic_reference"].title() for o in obs)
        self.report({"INFO"}, f"References placed ({views}). Press Numpad 1 / 3 / 7 to see each one; they hide in perspective view.")
        return {"FINISHED"}


def draw_panel(layout, context):
    box = layout.box()
    box.label(text="Reference Images", icon="IMAGE_REFERENCE")
    box.operator(RUSTIC_OT_add_references.bl_idname, icon="ADD")
    refs = [o for o in bpy.data.objects if "rustic_reference" in o]
    for o in refs:
        row = box.row(align=True)
        row.label(text=o["rustic_reference"].title())
        row.prop(o, "color", index=3, text="Opacity", slider=True)
        row.prop(o, "hide_viewport", text="", emboss=False)
    if refs:
        box.label(text="Numpad 1 front, 3 side, 7 top, 5 ortho", icon="INFO")


classes = (RUSTIC_OT_add_references,)
