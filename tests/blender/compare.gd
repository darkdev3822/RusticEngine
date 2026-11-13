# Renders every material of a RusticEngine Link .glb in UV space (bake preview mode) and diffs it
# against the Cycles bakes from make_scene.py. Run through tests/blender/run.sh.
extends SceneTree

const SIZE := 128

func _init() -> void:
	var args := OS.get_cmdline_user_args()
	if args[0] == "lit":
		await _lit(args[1], args[2])
		return
	var glb: String = args[0]
	var bake_dir: String = args[1]
	var out_dir: String = args[2]
	DirAccess.make_dir_recursive_absolute(out_dir)
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	var err := doc.append_from_file(glb, state)
	if err != OK:
		print("COMPARE FAIL could not load ", glb, " err ", err)
		quit(1)
		return
	var report: Dictionary = state.get_additional_data("RUSTIC_blender_nodes")
	var scene := doc.generate_scene(state)
	var meshes: Array = scene.find_children("*", "MeshInstance3D", true, false)
	var lines: PackedStringArray = []
	var failed := 0
	for mi: MeshInstance3D in meshes:
		var mat: Material = mi.mesh.surface_get_material(0)
		var name := String(mi.name)
		var info := _report_for(report, mat.resource_name if mat else name)
		if not (mat is ShaderMaterial):
			lines.append("%-20s KEPT STANDARD  %s" % [name, ", ".join(info.get("problems", []))])
			continue
		var img := await _render(mi)
		img.save_png(out_dir.path_join(name + ".godot.png"))
		if not FileAccess.file_exists(bake_dir.path_join(name + ".png")):
			lines.append("%-20s translated (lit-only case, see lit.png)  %s" % [name, "; ".join(info.get("notes", []))])
			continue
		var bake := Image.load_from_file(bake_dir.path_join(name + ".png"))
		bake.convert(Image.FORMAT_RGB8)
		img.convert(Image.FORMAT_RGB8)
		var stats := _diff(img, bake, out_dir.path_join(name + ".diff.png"))
		var ok: bool = stats.mean < 3.0 and stats.over16 < 1.0
		if not ok:
			failed += 1
		lines.append("%-20s %s  mean %.2f  p99 %d  >16: %.2f%%  %s" % [name, "OK  " if ok else "DIFF", stats.mean, stats.p99, stats.over16, "; ".join(info.get("notes", []))])
	scene.free()
	await process_frame
	for l in lines:
		print("COMPARE ", l)
	print("COMPARE DONE failed=%d" % failed)
	quit(1 if failed else 0)

func _report_for(report: Dictionary, mat_name: String) -> Dictionary:
	for m in report.get("materials", []):
		if m.get("material", "") == mat_name:
			return m
	return {}

func _render(mi: MeshInstance3D) -> Image:
	var vp := SubViewport.new()
	vp.size = Vector2i(SIZE, SIZE)
	vp.own_world_3d = true
	vp.transparent_bg = false
	vp.msaa_3d = Viewport.MSAA_DISABLED
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(vp)
	var copy: MeshInstance3D = mi.duplicate()
	copy.transform = Transform3D()
	copy.extra_cull_margin = 16384.0
	vp.add_child(copy)
	var cam := Camera3D.new()
	cam.position = Vector3(0, 0, 5)
	vp.add_child(cam)
	for i in 3:
		await RenderingServer.frame_post_draw
	var img := vp.get_texture().get_image()
	vp.queue_free()
	# (bake previews write sRGB themselves, like the bakes)
	return img

func _diff(a: Image, b: Image, path: String) -> Dictionary:
	var w := mini(a.get_width(), b.get_width())
	var h := mini(a.get_height(), b.get_height())
	var diff := Image.create(w * 3, h, false, Image.FORMAT_RGB8)
	var errs: Array = []
	var total := 0.0
	var over := 0
	for y in h:
		for x in w:
			var ca := a.get_pixel(x, y)
			var cb := b.get_pixel(x, y)
			var e := maxf(maxf(absf(ca.r - cb.r), absf(ca.g - cb.g)), absf(ca.b - cb.b)) * 255.0
			errs.append(e)
			total += e
			if e > 16.0:
				over += 1
			diff.set_pixel(x, y, ca)
			diff.set_pixel(x + w, y, cb)
			diff.set_pixel(x + 2 * w, y, Color(e / 64.0, e / 64.0, e / 64.0))
	diff.save_png(path)
	errs.sort()
	return {"mean": total / (w * h), "p99": int(errs[int(errs.size() * 0.99)]), "over16": 100.0 * over / (w * h)}


# Lit render of the whole scene with the real (non-preview) materials: catches shader compile
# errors in the lit code paths (normals, alpha, emission, coat) and gives a picture to look at.
func _lit(glb: String, out_png: String) -> void:
	await process_frame
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	if doc.append_from_file(glb, state) != OK:
		print("COMPARE FAIL could not load ", glb)
		quit(1)
		return
	var scene := doc.generate_scene(state)
	var vp := SubViewport.new()
	vp.size = Vector2i(1280, 360)
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(vp)
	vp.add_child(scene)
	var meshes: Array = scene.find_children("*", "MeshInstance3D", true, false)
	var span := 0.0
	for mi: MeshInstance3D in meshes:
		span = maxf(span, mi.position.x)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 30, 0)
	vp.add_child(sun)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.25, 0.27, 0.3)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.5, 0.5, 0.55)
	vp.add_child(env)
	var cam := Camera3D.new()
	cam.position = Vector3(span * 0.5, 6.0, 4.0)
	vp.add_child(cam)
	await process_frame
	cam.look_at(Vector3(span * 0.5, 0, 0))
	cam.fov = 70.0
	for i in 5:
		await RenderingServer.frame_post_draw
	vp.get_texture().get_image().save_png(out_png)
	print("COMPARE LIT saved ", out_png, " (", meshes.size(), " meshes)")
	vp.queue_free()
	await process_frame
	quit(0)
