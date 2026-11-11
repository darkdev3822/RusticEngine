@tool
extends RefCounted
# Helpers a scenario gets as `h`.

var plugin: EditorPlugin
var out := OS.get_environment("E2E_OUT")
var failures: PackedStringArray = []
var notes: PackedStringArray = []

func _init(p: EditorPlugin) -> void:
	plugin = p

func tree() -> SceneTree:
	return plugin.get_tree()

func say(msg: String) -> void:
	notes.append(msg)
	print("[e2e] ", msg)

func fail(msg: String) -> void:
	failures.append(msg)
	printerr("[e2e] FAIL: ", msg)

func check(ok: bool, msg: String) -> bool:
	if ok:
		say("ok: " + msg)
	else:
		fail(msg)
	return ok

func frames(n: int = 1) -> void:
	for i in n:
		await tree().process_frame

func seconds(s: float) -> void:
	await tree().create_timer(s, true, false, true).timeout

# Wait until cond.call() is true (polls each frame). Returns false on timeout.
func until(cond: Callable, timeout_s: float = 30.0) -> bool:
	var end := Time.get_ticks_msec() + int(timeout_s * 1000)
	while Time.get_ticks_msec() < end:
		if cond.call():
			return true
		await frames(1)
	return false

func shot(name: String) -> void:
	await frames(3)
	await RenderingServer.frame_post_draw
	var img := plugin.get_viewport().get_texture().get_image()
	img.save_png(out.path_join(name + ".png"))
	say("screenshot " + name + ".png")
	# Dialogs open as their own OS windows; save each visible one too.
	var n := 0
	for w in find_all("Window", EditorInterface.get_base_control().get_parent()):
		if w.visible and not w.is_embedded() and w != plugin.get_tree().root and w.size.x > 0:
			var wi = w.get_texture().get_image()
			if wi:
				n += 1
				wi.save_png(out.path_join("%s_window%d.png" % [name, n]))
				say("  + window '%s' -> %s_window%d.png" % [w.title, name, n])

func base() -> Node:
	return EditorInterface.get_base_control()

func find_all(cls: String, under: Node = null) -> Array[Node]:
	return (under if under else tree().root).find_children("*", cls, true, false)

func find_one(cls: String, under: Node = null) -> Node:
	var a := find_all(cls, under)
	return a[0] if a.size() > 0 else null

# The editor plugin instance of a C++ plugin class (e.g. "MechanicsPlugin").
func plugin_of(cls: String) -> Node:
	return find_one(cls, EditorInterface.get_base_control().get_parent())

# First visible Button whose text contains `text`.
func button(text: String, under: Node = null) -> Button:
	for b in find_all("Button", under):
		if b.is_visible_in_tree() and text in b.text:
			return b
	return null

func press(text: String, under: Node = null) -> bool:
	var b := button(text, under)
	if not check(b != null, "button '%s' exists" % text):
		return false
	b.pressed.emit()
	return true

func main_screen(name: String) -> void:
	EditorInterface.set_main_screen_editor(name)
	await frames(10)

func project_file(p: String) -> String:
	return FileAccess.get_file_as_string(p)

func finish() -> void:
	var f := FileAccess.open(out.path_join("result.txt"), FileAccess.WRITE)
	f.store_string(("PASS" if failures.is_empty() else "FAIL") + "\n" + "\n".join(notes) + "\n" + "\n".join(failures) + "\n")
	f.close()
	if EditorInterface.is_playing_scene():
		EditorInterface.stop_playing_scene()
		await seconds(1.0)
	tree().quit(0 if failures.is_empty() else 1)
