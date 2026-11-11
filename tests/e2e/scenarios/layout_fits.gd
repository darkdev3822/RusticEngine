@tool
extends RefCounted
# Nothing may push the editor wider than the screen: on every main screen and every Studio tool,
# the Ember dock (rightmost) must end inside the window. Run at 1600x900 by run.sh.

func _ember_fits(h, where: String) -> void:
	await h.frames(12)
	var win: Vector2 = h.tree().root.size
	var dock: Control = h.find_one("AIGuideDock", h.base())
	if dock == null:
		h.fail("Ember dock not found")
		return
	var r: Rect2 = dock.get_global_rect()
	h.check(r.end.x <= win.x + 1 and r.size.x >= 200, "%s: Ember dock inside the window (x %d-%d of %d)" % [where, r.position.x, r.end.x, win.x])

func run(h) -> void:
	for screen in ["2D", "3D", "Script", "Mechanics"]:
		await h.main_screen(screen)
		await _ember_fits(h, screen)
	await h.main_screen("Studio")
	var list: ItemList = null
	for l in h.find_all("ItemList", h.base()):
		if l.is_visible_in_tree() and l.item_count >= 6 and l.get_item_text(0) == "3D Model":
			list = l
	if h.check(list != null, "Studio tool list found"):
		for i in list.item_count:
			list.select(i)
			list.item_selected.emit(i)
			await _ember_fits(h, "Studio " + list.get_item_text(i))
	await h.shot("01_last")
