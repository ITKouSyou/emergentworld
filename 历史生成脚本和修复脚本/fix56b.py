# 前端：整段替换 _on_npc_detail 加日程显示
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

start = t.find("func _on_npc_detail(data: Dictionary) -> void:")
if start < 0:
    print("[fail] 找不到 _on_npc_detail")
    raise SystemExit(1)

end = t.find("\nfunc ", start + 1)
if end < 0:
    end = len(t)

new_func = '''func _on_npc_detail(data: Dictionary) -> void:
	var lines: Array[String] = []
	var gender_zh: String = str(data.get("gender_label", "未知"))
	lines.append("[b][color=yellow]%s[/color][/b]   %s   %d 岁" % [
		str(data.get("name", "?")), gender_zh, int(data.get("age", 0)),
	])
	lines.append("所在地：%s" % str(data.get("location_label", "")))
	lines.append("")
	lines.append("[b]性格[/b]")
	for t2 in data.get("traits", []):
		if t2 is Dictionary:
			lines.append("   %s：%.2f" % [str(t2.get("label", "?")), float(t2.get("value", 0))])
	lines.append("")
	lines.append("[b]需求[/b]")
	for n in data.get("needs", []):
		if n is Dictionary:
			lines.append("   %s：%.2f" % [str(n.get("label", "?")), float(n.get("value", 0))])
	lines.append("")
	lines.append("[b]目标[/b]")
	for g in data.get("goals", []):
		lines.append("   · %s" % str(g))

	# 日程
	var sched: Array = data.get("schedule", [])
	if not sched.is_empty():
		lines.append("")
		lines.append("[b]日常作息[/b]")
		for s in sched:
			lines.append("   %s" % str(s))

	# 家庭
	var fam: Dictionary = data.get("family", {})
	if fam is Dictionary:
		var fam_lines: Array[String] = []
		if str(fam.get("spouse_name", "")) != "":
			fam_lines.append("   配偶：%s" % str(fam["spouse_name"]))
		var ch_arr = fam.get("children_names", [])
		if ch_arr != null and ch_arr.size() > 0:
			var ch_names: Array[String] = []
			for c in ch_arr:
				ch_names.append(str(c))
			fam_lines.append("   子女：%s" % "、".join(ch_names))
		var pa_arr = fam.get("parents_names", [])
		if pa_arr != null and pa_arr.size() > 0:
			var pa_names: Array[String] = []
			for c in pa_arr:
				pa_names.append(str(c))
			fam_lines.append("   父母：%s" % "、".join(pa_names))
		var si_arr = fam.get("siblings_names", [])
		if si_arr != null and si_arr.size() > 0:
			var si_names: Array[String] = []
			for c in si_arr:
				si_names.append(str(c))
			fam_lines.append("   兄弟姐妹：%s" % "、".join(si_names))
		if not fam_lines.is_empty():
			lines.append("")
			lines.append("[b]家庭[/b]")
			for fl in fam_lines:
				lines.append(fl)

	npc_detail.text = "\\n".join(lines)'''

t = t[:start] + new_func + t[end:]
p.write_text(t, encoding="utf-8")
print("[fix] _on_npc_detail 整段重写（含日程）")

# 确认
t2 = p.read_text(encoding="utf-8")
print("'日常作息' 出现：%s" % ("日常作息" in t2))
print("'data.get(\"schedule\"' 出现：%s" % ('data.get("schedule"' in t2))