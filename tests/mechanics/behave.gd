extends SceneTree
# Behavior checks for the new-mechanic starting code. Run headless with the sandbox project:
#   godot --headless --path P -s res://behave.gd -- <variant>
# Prints "BEHAVE PASS <variant>" or "BEHAVE FAIL <variant>: why".

var kind := ""
var room: Node
var player: CharacterBody3D

func _initialize() -> void:
	kind = OS.get_cmdline_user_args()[0]
	room = load("res://mechanics/t_%s/sandbox.tscn" % kind).instantiate()
	root.add_child(room)
	player = room.get_node_or_null("Player")
	_run.call_deferred()

func frames(n: int) -> void:
	for i in n:
		await physics_frame

func node() -> Node:
	return room.find_children("*", "T" + kind.to_pascal_case(), true, false)[0]

func done(ok: bool, why := "") -> void:
	print("BEHAVE %s %s%s" % ["PASS" if ok else "FAIL", kind, "" if ok else ": " + why])
	quit()

func tap(action: String) -> void:
	Input.action_press(action)
	await frames(2)
	Input.action_release(action)

func _run() -> void:
	await frames(10)
	var n := node()
	match kind:
		"dash":
			await frames(30)
			var before := player.velocity
			await tap("t_dash")
			done(player.velocity.length() > before.length() + 5.0, "no burst (v=%s)" % player.velocity)
		"double_jump":
			await frames(30)
			player.velocity.y = 4.0; player.global_position.y += 1.0
			await frames(15)
			await tap("jump")
			done(n.jumps_left() == 0 and player.velocity.y > 2.0, "no air jump (left=%d vy=%.1f)" % [n.jumps_left(), player.velocity.y])
		"wall_jump":
			await frames(30)
			player.global_position = Vector3(-1.05, 2.0, -2.0)  # against Wall1, in the air
			player.velocity = Vector3(-3, 0, 0)
			await frames(3)
			await tap("jump")
			done(player.velocity.x > 2.0 and player.velocity.y > 2.0, "no kick off the wall (v=%s)" % player.velocity)
		"glide":
			await frames(30)
			player.global_position.y = 20.0
			Input.action_press("jump")
			await frames(90)
			var vy := player.velocity.y
			Input.action_release("jump")
			done(vy > -2.0, "fell fast while gliding (vy=%.1f)" % vy)
		"pickup_counter":
			player.global_position = n.global_position
			await frames(10)
			done(player.get_meta("t_pickup_counter_count", 0) == 1 and not is_instance_valid(n), "not collected")
		"door":
			var door: Node3D = n.get_node("Door")
			var y0 := door.position.y
			player.global_position = n.global_position + Vector3(0, 0, 1.5)
			await frames(60)
			done(door.position.y > y0 + 1.0, "door didn't open (%.2f -> %.2f)" % [y0, door.position.y])
		"checkpoint":
			player.global_position = n.global_position
			await frames(10)
			player.global_position = Vector3(30, -20, 30)
			await frames(5)
			done(player.global_position.distance_to(n.global_position) < 2.0, "no respawn (at %s)" % player.global_position)
		"trigger":
			var got := [false]
			n.triggered.connect(func(): got[0] = true)
			player.global_position = n.global_position
			await frames(10)
			done(got[0], "triggered not emitted")
		"patrol":
			var x0: float = n.global_position.x
			await frames(120)
			done(absf(n.global_position.x - x0) > 1.0, "didn't move")
		"chase":
			var d0: float = n.global_position.distance_to(player.global_position)
			await frames(90)
			done(n.global_position.distance_to(player.global_position) < d0 - 1.0, "didn't approach")
		"countdown":
			var t0: float = n.time_left()
			await frames(60)
			done(n.time_left() < t0 - 0.5, "not counting")
		"regen":
			var stats := player.get_node("CharacterStats")
			stats.damage(50.0)
			var h0: float = stats.get_health()
			await frames(60 * 6)
			done(stats.get_health() > h0 + 5.0, "no healing (%.1f -> %.1f)" % [h0, stats.get_health()])
		"score":
			var total = n.add_points(5)
			done(total == 5 and n.get_total() == 5, "total %s" % total)
		_:
			done(false, "no check for this kind")
