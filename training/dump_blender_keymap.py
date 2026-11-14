# Run: flatpak run org.blender.Blender -b --factory-startup --python ABS/dump_blender_keymap.py -- OUT.json
# Dumps Blender's default keymap (what each shortcut does, per editor/mode) for Ember's shortcut drills.
import json, sys
import bpy

out_path = sys.argv[sys.argv.index("--") + 1]
kc = bpy.context.window_manager.keyconfigs.default
if True:  # background mode only has a few keymaps, so always build the full default from the shipped preset
    # Background mode has no window keymap yet: build it from the shipped preset data.
    from bl_keymap_utils.io import keyconfig_init_from_data
    import importlib.util, os
    path = os.path.join(bpy.utils.resource_path("LOCAL"), "scripts", "presets", "keyconfig", "keymap_data", "blender_default.py")
    spec = importlib.util.spec_from_file_location("blender_default", path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    kc = bpy.context.window_manager.keyconfigs.new("dump")
    keyconfig_init_from_data(kc, mod.generate_keymaps(mod.Params(select_mouse='LEFT', spacebar_action='PLAY', use_fallback_tool=True, use_fallback_tool_select_handled=False, use_gizmo_drag=True)))  # factory defaults


def op_label(idname, props):
    if idname in ("wm.call_menu", "wm.call_menu_pie", "wm.call_panel"):
        name = getattr(props, "name", "")
        cls = getattr(bpy.types, name, None)
        label = getattr(cls, "bl_label", name) if cls else name
        return ("Pie menu: " if idname.endswith("pie") else "Menu: ") + label
    if idname == "wm.context_toggle":
        return "Toggle " + getattr(props, "data_path", "")
    try:
        mod, fn = idname.split(".", 1)
        return getattr(getattr(bpy.ops, mod), fn).get_rna_type().name
    except Exception:
        return idname


def combo(i):
    keys = []
    if i.ctrl == 1: keys.append("Ctrl")
    if i.shift == 1: keys.append("Shift")
    if i.alt == 1: keys.append("Alt")
    if i.oskey == 1: keys.append("Cmd/Super")
    if i.key_modifier and i.key_modifier != "NONE": keys.append(i.key_modifier.title())
    t = i.type.replace("EVT_", "")
    pretty = {"LEFTMOUSE": "Left Click", "RIGHTMOUSE": "Right Click", "MIDDLEMOUSE": "Middle Mouse", "WHEELUPMOUSE": "Wheel Up",
              "WHEELDOWNMOUSE": "Wheel Down", "ZERO": "0", "ONE": "1", "TWO": "2", "THREE": "3", "FOUR": "4", "FIVE": "5", "SIX": "6",
              "SEVEN": "7", "EIGHT": "8", "NINE": "9", "ACCENT_GRAVE": "`", "SLASH": "/", "PERIOD": ".", "COMMA": ",", "MINUS": "-",
              "PLUS": "+", "NUMPAD_PERIOD": "Numpad .", "DEL": "Delete", "RET": "Enter", "ESC": "Esc", "BACK_SPACE": "Backspace"}
    keys.append(pretty.get(t, t.replace("NUMPAD_", "Numpad ").title()))
    s = " + ".join(keys)
    if i.value == "DOUBLE_CLICK": s += " (double)"
    elif i.value == "CLICK_DRAG": s += " (drag)"
    return s


def props(i):
    """The settings this shortcut passes (e.g. type=VERT), so 1/2/3 read as vertex/edge/face mode."""
    out = {}
    p = i.properties
    if p is None:
        return out
    for k in p.bl_rna.properties.keys():
        if k == "rna_type" or not p.is_property_set(k):
            continue
        v = getattr(p, k, None)
        if isinstance(v, (str, bool, int, float)) and k not in ("name",):
            out[k] = v
        elif isinstance(v, set):
            out[k] = ",".join(sorted(v))
    return out


rows = []
for km in kc.keymaps:
    for i in km.keymap_items:
        if not i.active or i.map_type in ("TIMER", "NDOF", "TEXTINPUT") or i.type in ("MOUSEMOVE", "INBETWEEN_MOUSEMOVE"):
            continue
        rows.append({"keymap": km.name, "space": km.space_type, "keys": combo(i), "operator": i.idname,
                     "label": op_label(i.idname, i.properties), "props": props(i)})
json.dump({"blender": bpy.app.version_string, "items": rows}, open(out_path, "w"), indent=0)
print("KEYMAP_DONE", len(rows))
