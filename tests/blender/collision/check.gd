extends SceneTree
# Lists the bodies and shapes the import made, then runs physics for 3 seconds and reports where things landed.
var level: Node
var frames := 0

func _init() -> void:
	level = (load("res://level.glb") as PackedScene).instantiate()
	root.add_child(level)
	var named := level.find_child("Wall*", true, false)
	print("COLLISION_NAMED %s %s" % [named.name if named else "missing", named.find_children("*", "StaticBody3D", true, false).size() if named else -1])
	for n in ["Floor", "Crate", "Ball", "Pillar", "InvisibleWall", "Checkpoint", "Platform", "Decoration"]:
		var node := level.find_child(n, true, false)
		var info := "missing"
		if node:
			var shapes := []
			for c in node.get_children():
				if c is CollisionShape3D:
					var s: Shape3D = c.shape
					var d := s.get_class()
					if s is BoxShape3D: d += " size=%s" % [(s as BoxShape3D).size.snapped(Vector3.ONE * 0.01)]
					elif s is SphereShape3D: d += " r=%.2f" % (s as SphereShape3D).radius
					elif s is CylinderShape3D: d += " r=%.2f h=%.2f" % [(s as CylinderShape3D).radius, (s as CylinderShape3D).height]
					shapes.append(d)
			var mesh := node.find_children("*", "MeshInstance3D", true, false).size() + (1 if node is MeshInstance3D else 0)
			info = "%s shapes=%s meshes=%d" % [node.get_class(), shapes, mesh]
			if node is RigidBody3D: info += " mass=%.1f friction=%.2f bounce=%.2f" % [node.mass, node.physics_material_override.friction, node.physics_material_override.bounce]
			if node is Node3D: info += " scale=%s" % [(node as Node3D).scale.snapped(Vector3.ONE * 0.01)]
		print("COLLISION_NODE %s %s" % [n, info])

func _physics_process(_d: float) -> bool:
	frames += 1
	if frames == 180:
		for n in ["Crate", "Ball"]:
			var b := level.find_child(n, true, false) as Node3D
			print("COLLISION_REST %s y=%.2f" % [n, b.global_position.y])
		return true
	return false
