extends SceneTree
func _init() -> void:
	var dir: String = OS.get_cmdline_user_args()[0]
	DirAccess.make_dir_recursive_absolute(dir)
	var f := FileAccess.open(dir.path_join("project.godot"), FileAccess.WRITE)
	f.store_string('config_version=5\n\n[application]\nconfig/name="Agent Test"\nconfig/icon="res://icon.svg"\n')
	f.close()
	RustTools.create_crate(dir, "Agent Test", true)
	quit()
