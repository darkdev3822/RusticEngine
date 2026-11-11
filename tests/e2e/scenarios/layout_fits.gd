@tool
extends RefCounted
# The editor must fit common screens: its minimum size has to stay under 1366x768,
# on both the 2D screen (fresh project, no scene open) and the RusticEngine tabs.

const SCREEN := Vector2(1366, 768)

func _check(h, where: String) -> void:
	await h.frames(10)
	var m: Vector2 = h.tree().root.get_contents_minimum_size()
	h.check(m.x <= SCREEN.x and m.y <= SCREEN.y, "%s: editor minimum size %dx%d fits %dx%d" % [where, m.x, m.y, SCREEN.x, SCREEN.y])

func run(h) -> void:
	for screen in ["2D", "3D", "Script", "Studio", "Mechanics"]:
		await h.main_screen(screen)
		await _check(h, screen)
	await h.main_screen("2D")
	await h.shot("01_2d")
