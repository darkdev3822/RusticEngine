@tool
extends RefCounted
# Project > Tools > Connect an Outside AI Agent... writes .mcp.json and shows setup help.

func run(h) -> void:
	var found := false
	for pm in h.find_all("PopupMenu", h.base().get_parent()):
		for i in pm.item_count:
			if pm.get_item_text(i).begins_with("Connect an Outside AI Agent"):
				pm.index_pressed.emit(i)
				found = true
				break
		if found:
			break
	if not h.check(found, "Tools menu has Connect an Outside AI Agent"):
		return
	await h.frames(20)
	var dlg: Window = null
	for w in h.find_all("AcceptDialog", h.base().get_parent()):
		if w.visible and "Outside AI" in w.title:
			dlg = w
	h.check(dlg != null, "connect dialog is open")
	h.check(FileAccess.file_exists("res://.mcp.json"), ".mcp.json written")
	h.check(FileAccess.file_exists("res://.cursor/mcp.json"), ".cursor/mcp.json written")
	var j = JSON.parse_string(h.project_file("res://.mcp.json"))
	h.check(j is Dictionary and j.has("mcpServers"), ".mcp.json has mcpServers")
	if j is Dictionary and j.has("mcpServers"):
		for k in j.mcpServers:
			var cmd: String = j.mcpServers[k].get("command", "")
			h.check(FileAccess.file_exists(cmd), "MCP command exists: " + cmd)
			h.say("args: " + str(j.mcpServers[k].get("args", [])))
	await h.shot("01_dialog")
