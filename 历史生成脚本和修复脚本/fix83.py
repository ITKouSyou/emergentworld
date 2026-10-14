# 修 fix82b 的 split 用法
from pathlib import Path
import re

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 1. 在 _build_item_tab(right_tabs) 后插入 _build_craft_tab
pattern = re.compile(r"(\n([ \t]+)_build_item_tab\(right_tabs\)\n)")
m = pattern.search(t)

if not m:
    print("[fail] 找不到 _build_item_tab(right_tabs)")
    raise SystemExit(1)

# 检查是否已有 _build_craft_tab 调用（紧跟其后）
after_text = t[m.end():m.end() + 500]
if "_build_craft_tab(right_tabs)" in after_text:
    print("[skip] _build_ui 已有 craft Tab 调用")
else:
    indent = m.group(2)
    insert_line = indent + "_build_craft_tab(right_tabs)\n"
    t = t[:m.end()] + insert_line + t[m.end():]
    p.write_text(t, encoding="utf-8")
    print("[fix] _build_ui 加合成 Tab 调用")

# 2. 追加 _build_craft_tab 等函数
t = p.read_text(encoding="utf-8")

if "func _build_craft_tab" in t:
    print("[skip] 已有 _build_craft_tab 函数")
else:
    tail = '''

func _build_craft_tab(parent: TabContainer) -> void:
	var tab := VBoxContainer.new()
	tab.name = "合成"
	tab.add_theme_constant_override("separation", 6)
	parent.add_child(tab)

	var ctrl := HBoxContainer.new()
	ctrl.add_theme_constant_override("separation", 6)
	tab.add_child(ctrl)

	var refresh := Button.new()
	refresh.text = "刷新配方"
	refresh.pressed.connect(func(): api.fetch_recipes())
	ctrl.add_child(refresh)

	var hint := Label.new()
	hint.text = "（合成会消耗材料）"
	hint.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
	ctrl.add_child(hint)

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	tab.add_child(scroll)

	craft_log = RichTextLabel.new()
	craft_log.bbcode_enabled = true
	craft_log.fit_content = true
	craft_log.meta_clicked.connect(_on_craft_meta_clicked)
	craft_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(craft_log)


func _on_recipes_received(data: Array) -> void:
	all_recipes = data
	if craft_log == null:
		return
	craft_log.clear()

	if data.is_empty():
		craft_log.text = "[i]没有可用配方[/i]"
		return

	for r in data:
		if not r is Dictionary:
			continue
		var rid: String = str(r.get("id", ""))
		var name: String = str(r.get("name", "?"))
		var kind: String = str(r.get("kind", ""))
		var desc: String = str(r.get("desc", ""))
		var can_craft: bool = bool(r.get("can_craft", false))

		var color := "white"
		var prefix := "○"
		if can_craft:
			color = "gold"
			prefix = "★"

		craft_log.append_text("[color=%s]%s [b]%s[/b][/color]  [i](%s)[/i]\\n" % [
			color, prefix, name, kind,
		])
		craft_log.append_text("    %s\\n" % desc)

		var mats: Array = r.get("materials", [])
		var mat_lines: Array[String] = []
		for m in mats:
			if not m is Dictionary:
				continue
			var mk: String = str(m.get("kind", ""))
			var need: int = int(m.get("count", 0))
			var have: int = int(m.get("have", 0))
			var ok2 := have >= need
			var mc := "lightgreen" if ok2 else "red"
			mat_lines.append("[color=%s]%s %d/%d[/color]" % [mc, mk, have, need])
		craft_log.append_text("    材料：%s\\n" % "、".join(mat_lines))

		if can_craft:
			craft_log.append_text("    [url=craft:%s][color=green][合成][/color][/url]\\n" % rid)
		else:
			craft_log.append_text("    [color=gray]（材料不足）[/color]\\n")

		craft_log.append_text("\\n")


func _on_craft_meta_clicked(meta) -> void:
	var s := str(meta)
	if s.begins_with("craft:"):
		var rid := s.substr(6)
		api.craft_item(rid)


func _on_craft_done(data: Dictionary) -> void:
	api.fetch_items(200)
	api.fetch_recipes()
'''
    t = t.rstrip() + "\n" + tail
    p.write_text(t, encoding="utf-8")
    print("[fix] main.gd 加合成 Tab 函数")

# 3. _refresh_all 拉配方
t = p.read_text(encoding="utf-8")
i = t.find("func _refresh_all() -> void:")
if i >= 0:
    e = t.find("\nfunc ", i + 1)
    body = t[i:e]
    if "api.fetch_recipes" not in body:
        body_new = body.rstrip() + "\n\tapi.fetch_recipes()\n"
        t = t[:i] + body_new + t[e:]
        p.write_text(t, encoding="utf-8")
        print("[fix] _refresh_all 拉配方")
    else:
        print("[skip] _refresh_all 已有 fetch_recipes")

# 4. 物品详情显示耐久
t = p.read_text(encoding="utf-8")
old_dur = '''		lines.append("价值：%.2f" % value)
		item_detail.text = "\\n".join(lines)'''
new_dur = '''		lines.append("价值：%.2f" % value)

		# 耐久
		var dur: int = int(it.get("durability", 100))
		var max_dur: int = int(it.get("max_durability", 100))
		if max_dur > 0:
			var dcolor := "lightgreen"
			if dur <= max_dur * 0.3:
				dcolor = "red"
			elif dur <= max_dur * 0.6:
				dcolor = "yellow"
			lines.append("耐久：[color=%s]%d / %d[/color]" % [dcolor, dur, max_dur])

		item_detail.text = "\\n".join(lines)'''
if old_dur in t and "耐久：" not in t:
    t = t.replace(old_dur, new_dur, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 物品详情显示耐久")
else:
    print("[skip] 已改过或锚点未匹配")

# 5. 打印 _build_ui 里的 Tab 调用
t = p.read_text(encoding="utf-8")
i = t.find("func _build_ui")
e = t.find("\nfunc ", i + 1)
body = t[i:e]
print()
print("=== _build_ui Tab 调用 ===")
for line in body.split("\n"):
    if "right_tabs" in line:
        print("  " + line.strip())

print()
print("Godot 完全关闭重开，按 F5")