@tool
extends RefCounted
# Every Studio tool: open it, make something, save, check the exported game files,
# reload it and check it comes back the same (describe() before == after).

const TOOLS := [
	# [list name, editor class, save method, load method, extra files (from base path)]
	["3D Model", "StudioModelEditor", "save_model", "load_model", [".rmodel", ".glb"]],
	["Sound Effects", "StudioSfxEditor", "save_sound", "load_sound", [".rsfx", ".wav"]],
	["Music", "StudioMusicEditor", "save_music", "load_music", [".rmusic", ".wav"]],
	["Pixel Art", "StudioPixelEditor", "save_sprite", "load_sprite", [".rpix", ".png"]],
	["Sky", "StudioSkyEditor", "save_sky", "load_sky", [".rsky", ".tscn"]],
	["UI Kit", "StudioUiEditor", "save_ui", "load_ui", [".rui", "_theme.tres"]],
]

func run(h) -> void:
	await h.main_screen("Studio")
	var sp = h.plugin_of("StudioPlugin")
	var list: ItemList = null
	for l in h.find_all("ItemList", h.base()):
		if l.is_visible_in_tree() and l.item_count >= 6 and l.get_item_text(0) == "3D Model":
			list = l
	if not h.check(list != null, "Studio tool list found"):
		return
	h.check(list.item_count == TOOLS.size(), "Studio lists %d tools" % TOOLS.size())
	var only := OS.get_environment("E2E_ONLY")  # e.g. E2E_ONLY="Sky" to test one tool
	for t in TOOLS:
		if only != "" and t[0] != only:
			continue
		var idx := -1
		for i in list.item_count:
			if list.get_item_text(i) == t[0]:
				idx = i
		if not h.check(idx >= 0, "tool '%s' listed" % t[0]):
			continue
		list.select(idx)
		list.item_selected.emit(idx)
		await h.frames(15)
		var ed = h.find_one(t[1], h.base())
		if not h.check(ed != null and ed.is_visible_in_tree(), "%s open" % t[0]):
			continue
		if t[1] == "StudioPixelEditor":
			ed.new_sprite(16, 16)
			for x in range(4, 12):
				ed.paint(x, 8, 1)
		elif ed.has_method("preset"):
			ed.preset(1)
		await h.frames(5)
		var base: String = "res://studio_test/" + t[0].to_snake_case().replace(" ", "_")
		ed.call(t[2], base + t[4][0])
		await h.frames(10)
		var before: String = ed.describe()
		for ext in t[4]:
			h.check(FileAccess.file_exists(base + ext), "%s saved %s" % [t[0], (base + ext).get_file()])
		await h.shot("tool_%d_%s" % [idx, t[0].to_snake_case().replace(" ", "_")])
		ed.call(t[3], base + t[4][0])
		await h.frames(10)
		var after: String = ed.describe()
		if not h.check(after == before, "%s reload matches what was saved" % t[0]):
			h.say("  before: " + before.substr(0, 300).replace("\n", " | "))
			h.say("  after:  " + after.substr(0, 300).replace("\n", " | "))
