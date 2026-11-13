@tool
extends EditorPlugin
# Opens main.tscn (a Blender .glb instance with gameplay nodes added), signals the test script, then waits
# for Blender's save to reimport the .glb and checks the open scene updated without losing those nodes.

var out_dir := OS.get_environment("LIVE_OUT")

func _enter_tree() -> void:
	await get_tree().create_timer(3.0).timeout
	EditorInterface.open_scene_from_path("res://main.tscn")
	await get_tree().create_timer(1.0).timeout
	EditorInterface.get_resource_filesystem().resources_reimported.connect(_on_reimported)
	FileAccess.open(out_dir.path_join("READY"), FileAccess.WRITE).store_string("ok")

func _on_reimported(files: PackedStringArray) -> void:
	if not files.has("res://art/blender/level.glb"):
		return
	await get_tree().create_timer(1.5).timeout
	var root := EditorInterface.get_edited_scene_root()
	var level := root.get_node_or_null("Level") as Node3D
	var r := []
	r.append("level=%s" % (level != null))
	if level:
		r.append("gameplay=%s" % (level.get_node_or_null("Gameplay") != null))
		r.append("gameplay_script=%s" % (level.get_node_or_null("Gameplay") != null and level.get_node("Gameplay").get_script() != null))
		r.append("marker=%s" % (level.get_node_or_null("Cube/Marker") != null))
		r.append("level_pos=%s" % [level.position])
		var cube := level.get_node_or_null("Cube") as MeshInstance3D
		r.append("cube_x=%.2f" % (cube.position.x if cube else -999.0))
		r.append("ball=%s" % (level.get_node_or_null("Ball") != null))
		var mat: Material = cube.get_active_material(0) if cube else null
		r.append("cube_shader=%s" % (mat is ShaderMaterial))
		if mat is ShaderMaterial:
			r.append("red=%s" % ((mat as ShaderMaterial).shader.code.contains("vec3(1.0, 0.0, 0.0)") or (mat as ShaderMaterial).shader.code.contains("1.0, 0.0, 0.0")))
	var line := "LIVE_RESULT " + " ".join(r)
	print(line)
	FileAccess.open(out_dir.path_join("RESULT"), FileAccess.WRITE).store_string(line)
	get_tree().quit()
