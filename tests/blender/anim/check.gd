extends SceneTree
# Loads the imported arm, lists what came through, and samples the tip bone (Lower's tail) per animation.
func _init() -> void:
	var scene := (load("res://arm.glb") as PackedScene).instantiate()
	root.add_child(scene)
	var ap := scene.find_children("*", "AnimationPlayer", true, false)
	var sk := scene.find_children("*", "Skeleton3D", true, false)
	print("ANIM_ENGINE players=%d skeletons=%d" % [ap.size(), sk.size()])
	if sk.size() > 0:
		var s := sk[0] as Skeleton3D
		var names := []
		for i in s.get_bone_count(): names.append(s.get_bone_name(i))
		print("ANIM_ENGINE bones=", names)
	for m in scene.find_children("*", "MeshInstance3D", true, false):
		var mesh := (m as MeshInstance3D).mesh as ArrayMesh
		var shapes := []
		for i in mesh.get_blend_shape_count(): shapes.append(mesh.get_blend_shape_name(i))
		print("ANIM_ENGINE mesh=%s shapes=%s" % [m.name, shapes])
	if ap.size() == 0: quit(); return
	var player := ap[0] as AnimationPlayer
	for a in player.get_animation_list():
		var anim := player.get_animation(a)
		print("ANIM_ENGINE anim=%s length=%.4f loop=%d tracks=%d" % [a, anim.length, anim.loop_mode, anim.get_track_count()])
	var s := sk[0] as Skeleton3D
	var lower := s.find_bone("Lower")
	for a in ["Walk", "Wave"]:
		if not player.has_animation(a): continue
		for t in ([0.0, 0.25, 0.5] if a == "Walk" else [0.0, 0.375]):
			player.play(a); player.seek(t, true); player.advance(0)
			# tail of Lower = its head + bone length along its local Y
			# Local poses are set by the animation right away; chain them up by hand (global poses update lazily).
			var g := Transform3D()
			var b := lower
			while b >= 0:
				g = s.get_bone_pose(b) * g
				b = s.get_bone_parent(b)
			g = s.global_transform * g * Transform3D(Basis(), Vector3(0, 1.0, 0))
			print("ANIM_ENGINE %s t=%.4f tip=(%.3f, %.3f, %.3f)" % [a, t, g.origin.x, g.origin.y, g.origin.z])
	if player.has_animation("Smile"):
		var mi := scene.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D
		player.play("Smile"); player.seek(player.get_animation("Smile").length, true); player.advance(0)
		print("ANIM_ENGINE smile_end=%.3f" % mi.get_blend_shape_value(0))
	quit()
