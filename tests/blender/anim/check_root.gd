extends SceneTree
# Plays Walk for 1 s and sums the root motion; the skeleton itself must stay where it is.
var walker: Node
var ap: AnimationPlayer
var total := Vector3()
var frames := 0
func _init() -> void:
	walker = (load("res://walker.glb") as PackedScene).instantiate()
	root.add_child(walker)
	ap = walker.find_children("*", "AnimationPlayer", true, false)[0]
	print("ROOT_ENGINE track=", ap.root_motion_track, " loop=", ap.get_animation("Walk").loop_mode)
	ap.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_PHYSICS
	ap.play("Walk")
func _physics_process(_d: float) -> bool:
	frames += 1
	if frames > 1:
		total += ap.get_root_motion_position()
	if frames == 31:   # 30 physics frames of motion = 0.5 s at 60 fps
		var sk := walker.find_children("*", "Skeleton3D", true, false)[0] as Skeleton3D
		var r := sk.find_bone("root")
		print("ROOT_ENGINE half_second_motion=(%.2f, %.2f, %.2f) root_bone_pose=(%.2f, %.2f, %.2f)" % [total.x, total.y, total.z,
			sk.get_bone_pose_position(r).x, sk.get_bone_pose_position(r).y, sk.get_bone_pose_position(r).z])
		return true
	return false
