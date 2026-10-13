# 强制修 _on_chronicle_list 里的替换
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 找 _on_chronicle_list 函数
i = t.find("func _on_chronicle_list")
if i < 0:
    print("[fail] 找不到 _on_chronicle_list")
    raise SystemExit(1)

e = t.find("\n\nfunc ", i + 1)
if e < 0:
    e = len(t)

old_body = t[i:e]

# 强制整体替换
new_body = '''func _on_chronicle_list(data: Array) -> void:
	chronicle_log.clear()
	if data.is_empty():
		chronicle_log.text = "[i]还没有史册。点击下方按钮生成一份。[/i]"
		return
	for c in data:
		if not c is Dictionary:
			continue
		var title: String = str(c.get("title", "?"))
		title = _replace_template_ids(title)
		chronicle_log.append_text("[b][color=gold]%s[/color][/b]\\n" % title)

		var body: String = str(c.get("body", ""))
		body = _replace_template_ids(body)
		body = _highlight_names(body)
		chronicle_log.append_text("[color=lightgray]%s[/color]\\n\\n" % body)

		chronicle_log.append_text("[i]——  记录于第 %d 回合[/i]\\n\\n" % int(c.get("created_at", 0)))
'''

t = t[:i] + new_body + t[e:]
p.write_text(t, encoding="utf-8")
print("[fix] _on_chronicle_list 强制替换")

# 确认替换函数存在
t2 = p.read_text(encoding="utf-8")
print("_replace_template_ids 存在：%s" % ("func _replace_template_ids" in t2))
print("_highlight_names 存在：%s" % ("func _highlight_names" in t2))

print()
print("Godot 完全关闭重开，按 F5")