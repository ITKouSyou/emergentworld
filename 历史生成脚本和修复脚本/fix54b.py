# 前端：行动结果显示属性成长
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# _on_action_done 里加属性成长展示
old = '''	var exp_gain: int = int(data.get("exp_gain", 0))
	if exp_gain > 0:
		lines.append("[color=yellow]经验 +%d[/color]" % exp_gain)

	# 世界事件'''

new = '''	var exp_gain: int = int(data.get("exp_gain", 0))
	if exp_gain > 0:
		lines.append("[color=yellow]经验 +%d[/color]" % exp_gain)

	# 属性成长
	var growth = data.get("attribute_growth")
	if growth is Dictionary:
		var attr_label: String = str(growth.get("attribute_label", ""))
		var new_val: int = int(growth.get("new_value", 0))
		if attr_label != "":
			lines.append("[color=gold]★ %s 提升到 %d[/color]" % [attr_label, new_val])

	# 世界事件'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] _on_action_done 显示属性成长")
else:
    print("[skip] 已改过或锚点未匹配")

# 顺便：升级面板里加"自然成长上限 15"提示
old_hint = '''	var attr_title := Label.new()
	attr_title.text = "属性（可分配点会亮起 [+]）"'''

new_hint = '''	var attr_title := Label.new()
	attr_title.text = "属性（可分配点 [+] 可加到 20，行动自然成长上限 15）"'''

if old_hint in t:
    t = t.replace(old_hint, new_hint, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 属性标题加说明")

print()
print("重启后端：Ctrl+C → uvicorn server.main:app")
print("Godot 完全关闭重开，按 F5")