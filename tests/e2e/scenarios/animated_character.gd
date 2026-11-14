@tool
extends RefCounted
# Add the Animated Character starter from the Mechanics tab: it brings the Third-Person Controller with it,
# the mannequin imports with its looping animations and root motion, and the sandbox runs.

func _gdext_ready() -> bool:
	for f in DirAccess.get_files_at("res://"):
		if f.ends_with(".gdextension"):
			return true
	return false

func run(h) -> void:
	h.check(await h.until(_gdext_ready, 300), "first Rust build finished")
	await h.main_screen("Mechanics")
	var mp = h.plugin_of("MechanicsPlugin")
	if not h.check(mp != null, "Mechanics plugin found"):
		return
	var menu: MenuButton = null
	for m in h.find_all("MenuButton", h.base()):
		if m.text == "Add Mechanic":
			menu = m
	menu.about_to_popup.emit()
	var pm := menu.get_popup()
	var idx := -1
	for i in pm.item_count:
		if pm.get_item_text(i).begins_with("Animated Character"):
			idx = pm.get_item_id(i)
	if not h.check(idx >= 0, "Animated Character listed in Add Mechanic"):
		return
	mp.add_starter(idx)
	await h.frames(30)
	h.check(FileAccess.file_exists("res://mechanics/character_animation/mechanic.toml"), "character_animation installed")
	h.check(FileAccess.file_exists("res://mechanics/third_person/mechanic.toml"), "third_person installed with it (uses)")
	h.check(await h.until(func(): return ResourceLoader.exists("res://mechanics/character_animation/mannequin.glb"), 120), "mannequin imported")
	var scene := (load("res://mechanics/character_animation/mannequin.glb") as PackedScene).instantiate()
	var ap: AnimationPlayer = scene.find_children("*", "AnimationPlayer", true, false)[0]
	var names := Array(ap.get_animation_list())
	names.sort()
	h.check(names == ["Fall", "Idle", "Run", "Walk"], "mannequin animations: %s" % [names])
	h.check(ap.get_animation("Walk").loop_mode == Animation.LOOP_LINEAR, "Walk loops")
	h.check(str(ap.root_motion_track).ends_with(":root"), "root motion track set: %s" % ap.root_motion_track)
	scene.free()
	await h.shot("01_installed")
	h.press("Try It")
	h.check(await h.until(func(): return EditorInterface.is_playing_scene(), 120), "sandbox is running")
	await h.seconds(6.0)
	await h.shot("02_sandbox")
	EditorInterface.stop_playing_scene()
	await h.seconds(1.0)
