extends SceneTree
# Renders each imported case through its own Blender camera and prints the linear centre colour.
var cases := ["sun", "point", "spot", "area", "point_orange", "sky_px", "sky_py"]
var i := -1
var frame := 0
var current: Node

func _init() -> void:
	root.size = Vector2i(64, 64)

func _process(_d: float) -> bool:
	frame += 1
	if i >= 0 and frame == 12:
		var img := root.get_texture().get_image()
		var acc := Vector3()
		for y in range(24, 40):
			for x in range(24, 40):
				var c := img.get_pixel(x, y).srgb_to_linear()
				acc += Vector3(c.r, c.g, c.b)
		acc /= 256.0
		var lights := []
		for l in current.find_children("*", "Light3D", true, false):
			lights.append("%s energy=%.3f range=%.1f" % [l.get_class(), l.light_energy, l.get("omni_range") if l is OmniLight3D else (l.get("spot_range") if l is SpotLight3D else 0.0)])
		print("ENGINE %s [%.4f, %.4f, %.4f] %s world=%s" % [cases[i], acc.x, acc.y, acc.z, lights, current.find_children("*", "WorldEnvironment", true, false).size()])
	if i < 0 or frame == 12:
		if current:
			current.queue_free()
		i += 1
		frame = 0
		if i >= cases.size():
			return true
		current = (load("res://%s.glb" % cases[i]) as PackedScene).instantiate()
		root.add_child(current)
		var cams := current.find_children("*", "Camera3D", true, false)
		if cams.size() > 0:
			(cams[0] as Camera3D).current = true
	return false
