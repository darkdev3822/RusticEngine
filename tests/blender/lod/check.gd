extends SceneTree
# Lists each LOD's visibility range, parent and position (relative to LOD0), then drops the barrel.
var props: Node
var frames := 0

func _init() -> void:
	props = (load("res://props.glb") as PackedScene).instantiate()
	root.add_child(props)

func _report(tag: String) -> void:
	for g in ["Rock", "Barrel"]:
		var holder := props.find_child(g, true, false) as Node3D
		if holder == null:
			print("LOD_ENGINE %s %s missing" % [tag, g]); continue
		var lod0 := holder.get_node_or_null(g + "_LOD0") as Node3D
		for i in 3:
			var m := holder.get_node_or_null("%s_LOD%d" % [g, i]) as GeometryInstance3D
			if m == null:
				print("LOD_ENGINE %s %s_LOD%d missing" % [tag, g, i]); continue
			var tris := 0
			var mesh := (m as MeshInstance3D).mesh
			for s in mesh.get_surface_count():
				tris += (mesh.surface_get_arrays(s)[Mesh.ARRAY_INDEX] as PackedInt32Array).size() / 3
			print("LOD_ENGINE %s %s_LOD%d holder=%s tris=%d begin=%.1f end=%.1f margin=%.2f fade=%d offset=%.3f y=%.2f" % [
				tag, g, i, holder.get_class(), tris, m.visibility_range_begin, m.visibility_range_end,
				m.visibility_range_begin_margin + m.visibility_range_end_margin, m.visibility_range_fade_mode,
				m.global_position.distance_to(lod0.global_position), m.global_position.y])

func _physics_process(_d: float) -> bool:
	frames += 1
	if frames == 1:
		_report("start")
	if frames == 150:
		_report("after_fall")
		return true
	return false
