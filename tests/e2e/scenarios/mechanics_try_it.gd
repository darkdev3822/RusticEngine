@tool
extends RefCounted
# Add the First-Person starter, try its sandbox, live-tune it, stop.

func _gdext_ready() -> bool:
	for f in DirAccess.get_files_at("res://"):
		if f.ends_with(".gdextension"):
			return true
	return false

func run(h) -> void:
	h.check(await h.until(_gdext_ready, 300), "first Rust build finished (.gdextension in place)")
	await h.main_screen("Mechanics")
	var mp = h.plugin_of("MechanicsPlugin")
	if not h.check(mp != null, "Mechanics plugin found"):
		return
	var menu: MenuButton = h.find_one("MenuButton", h.base())
	for m in h.find_all("MenuButton", h.base()):
		if m.text == "Add Mechanic":
			menu = m
	menu.about_to_popup.emit()
	var pm := menu.get_popup()
	var idx := -1
	for i in pm.item_count:
		if pm.get_item_text(i).begins_with("First"):
			idx = pm.get_item_id(i)
	if not h.check(idx >= 0, "First-Person starter listed in Add Mechanic"):
		return
	mp.add_starter(idx)
	await h.frames(30)
	h.check(FileAccess.file_exists("res://mechanics/first_person/mechanic.toml"), "first_person installed")
	await h.shot("01_installed")
	h.press("Try It")
	h.check(await h.until(func(): return EditorInterface.is_playing_scene(), 30), "sandbox is running")
	await h.seconds(8.0)
	# Live tuning: edit walk_speed the way the inspector does while the sandbox runs.
	var insp: EditorInspector = h.find_one("EditorInspector", mp.get_parent())
	for i in h.find_all("EditorInspector", h.base()):
		if i.get_edited_object() is Resource and str(i.get_edited_object().resource_path).ends_with("tuning.tres"):
			insp = i
	var tuning = insp.get_edited_object() if insp else null
	if h.check(tuning != null and "walk_speed" in tuning, "tuning shown in the Mechanics inspector"):
		tuning.walk_speed = 6.25
		insp.property_edited.emit("walk_speed")
		await h.seconds(2.0)
		h.check("6.25" in h.project_file("res://mechanics/first_person/tuning.tres"), "tuning edit saved to tuning.tres")
	await h.shot("02_running")
	EditorInterface.stop_playing_scene()
	await h.seconds(2.0)
	await h.shot("03_stopped")
