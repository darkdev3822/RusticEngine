extends SceneTree
# Drives the Animated Character sandbox: stand, walk forward, then walk off the tower, and reports what the
# AnimationTree does.
var sandbox: Node
var player: CharacterBody3D
var frames := 0
var walk_blend := 0.0
var saw_air := false
var air_after_landing := false

func _init() -> void:
	sandbox = (load("res://mechanics/character_animation/sandbox.tscn") as PackedScene).instantiate()
	root.add_child(sandbox)
	player = sandbox.get_node("Player")

func _tree() -> AnimationTree:
	var t := player.find_children("AnimationTree", "AnimationTree", true, false)
	return t[0] if t.size() > 0 else null

func _physics_process(_d: float) -> bool:
	frames += 1
	var tree := _tree()
	if frames == 60:
		print("ANIMATE idle tree=%s active=%s blend=%.2f state=%s" % [tree != null, tree.active if tree else false,
			tree.get("parameters/locomotion/blend_position") if tree else -1.0, tree.get("parameters/state/current_state") if tree else ""])
		Input.action_press("move_forward")
	if frames == 180:
		walk_blend = tree.get("parameters/locomotion/blend_position")
		var lower := player.find_children("*", "Skeleton3D", true, false)[0] as Skeleton3D
		print("ANIMATE walking speed=%.2f blend=%.2f scale=%.2f root_bone=%s" % [Vector2(player.velocity.x, player.velocity.z).length(), walk_blend,
			tree.get("parameters/speed/scale"), lower.get_bone_pose_position(lower.find_bone("root")).snapped(Vector3.ONE * 0.01)])
		Input.action_release("move_forward")
		player.global_position = Vector3(-7, 4.2, -8)   # on top of the tower
		player.velocity = Vector3.ZERO
	if frames == 200:
		Input.action_press("move_forward")
	if frames > 200 and tree and tree.get("parameters/state/current_state") == "air":
		saw_air = true
	if frames == 420:
		Input.action_release("move_forward")
	if frames == 480:
		print("ANIMATE fall saw_air=%s now=%s on_floor=%s blend=%.2f" % [saw_air, tree.get("parameters/state/current_state"), player.is_on_floor(),
			tree.get("parameters/locomotion/blend_position")])
		return true
	return false
