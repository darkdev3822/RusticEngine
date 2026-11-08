# Headless test: RusticEngine's Rust project template + every node template compiles.
# Run: rustic-engine --headless --script ~/rustic-engine/tests/test_rust_tools.gd -- <empty dir>
extends SceneTree

func _init() -> void:
	var dir: String = OS.get_cmdline_user_args()[0]
	DirAccess.make_dir_recursive_absolute(dir)
	var f := FileAccess.open(dir.path_join("project.godot"), FileAccess.WRITE)
	f.store_string('config_version=5\n\n[application]\nconfig/name="Template Test"\nrun/main_scene="res://main.tscn"\n')
	f.close()
	print("crate name for 'My Cool Game!': ", RustTools.crate_name_from("My Cool Game!"))
	print("create_crate: ", error_string(RustTools.create_crate(dir, "Template Test", true)))
	for base in RustTools.node_base_classes():
		var path := RustTools.create_node_class(dir, "Test" + base, base)
		print("node ", base, " -> ", path.get_file() if path else "FAILED")
	var r := RustTools.build(dir, false)
	print("build ok: ", r.ok)
	if not r.ok:
		print(r.output)
	quit(0 if r.ok else 1)
