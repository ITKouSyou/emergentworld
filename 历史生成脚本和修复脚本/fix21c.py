# 直接追加两个辅助函数
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

if "func _highlight_names" in t:
    print("[skip] 已有 _highlight_names")
else:
    tail = '''

func _replace_template_ids(text: String) -> String:
	var re := RegEx.new()
	re.compile("\\\\[([a-z_]+)\\\\]")
	var result := text
	for m in re.search_all(text):
		var tid: String = m.get_string(1)
		var zh: String = tid
		if i18n_templates.has(tid):
			zh = str(i18n_templates[tid])
		result = result.replace("[%s]" % tid, "[%s]" % zh)
	return result


func _highlight_names(text: String) -> String:
	var result := text
	for npc_id in npc_order:
		var npc: Dictionary = npc_data[npc_id]
		var npc_name: String = str(npc.get("name", ""))
		if npc_name == "":
			continue
		var gender: String = str(npc.get("gender", "unknown"))
		var color := "#7ac4e8"
		if gender == "female":
			color = "#f0a0c0"
		elif gender == "male":
			color = "#88b8f0"
		result = result.replace(npc_name, "[color=%s]%s[/color]" % [color, npc_name])
	return result


func _color_name(npc_name: String) -> String:
	for npc_id in npc_order:
		var npc: Dictionary = npc_data[npc_id]
		if str(npc.get("name", "")) == npc_name:
			var gender: String = str(npc.get("gender", "unknown"))
			var color := "#7ac4e8"
			if gender == "female":
				color = "#f0a0c0"
			elif gender == "male":
				color = "#88b8f0"
			return "[color=%s]%s[/color]" % [color, npc_name]
	return npc_name
'''
    t = t.rstrip() + "\n" + tail
    p.write_text(t, encoding="utf-8")
    print("[fix] 追加 _highlight_names / _color_name / _replace_template_ids")

# 确保史册替换中文 ID 也生效（如果之前没改）
if "_replace_template_ids(body)" not in t:
    print("[warn] 史册里没调用 _replace_template_ids，可能 _on_chronicle_list 没改过")

print()
print("Godot 完全关闭重开，按 F5")