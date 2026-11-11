@tool
extends EditorPlugin
# Runs the scenario named by $E2E_SCENARIO (a script with `func run(h) -> void`),
# writes screenshots + result.txt into $E2E_OUT, then quits the editor.

func _enter_tree() -> void:
	OS.low_processor_usage_mode = false  # otherwise frame_post_draw may never fire
	_go.call_deferred()

func _go() -> void:
	var h := preload("helpers.gd").new(self)
	var path := OS.get_environment("E2E_SCENARIO")
	var scenario = load(path).new() if path != "" else null
	if scenario == null:
		h.fail("couldn't load scenario %s" % path)
	else:
		await h.frames(30)
		await scenario.run(h)
	h.finish()
