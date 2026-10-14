# 修左侧栏横向滚动条
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

old = '''	# --- 左栏：我（加滚动）---
	var left_scroll := ScrollContainer.new()
	left_scroll.custom_minimum_size = Vector2(340, 0)
	left_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	split.add_child(left_scroll)

	var left_panel := VBoxContainer.new()
	left_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left_panel.add_theme_constant_override("separation", 6)
	left_scroll.add_child(left_panel)
	_build_player_tab(left_panel)'''

new = '''	# --- 左栏：我（只允许纵向滚动）---
	var left_scroll := ScrollContainer.new()
	left_scroll.custom_minimum_size = Vector2(340, 0)
	left_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	left_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	split.add_child(left_scroll)

	var left_panel := VBoxContainer.new()
	left_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left_panel.add_theme_constant_override("separation", 6)
	left_scroll.add_child(left_panel)
	_build_player_tab(left_panel)'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 左栏禁止横向滚动")
else:
    print("[fail] _build_ui 左栏锚点未找到")

# 再让属性说明的 Label 允许收缩（避免撑宽父容器）
t = p.read_text(encoding="utf-8")

# 找属性行构建代码，加 clip_text
old2 = '''		var desc_lbl := Label.new()
		desc_lbl.text = attr_desc[i]
		desc_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		desc_lbl.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
		row.add_child(desc_lbl)'''

new2 = '''		var desc_lbl := Label.new()
		desc_lbl.text = attr_desc[i]
		desc_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		desc_lbl.clip_text = true
		desc_lbl.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		desc_lbl.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
		row.add_child(desc_lbl)'''

if old2 in t:
    t = t.replace(old2, new2, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 属性说明 Label 允许裁剪")
else:
    print("[skip] 属性说明 Label 已改过或锚点未匹配")

# 探索结果 / 行动结果 RichTextLabel 加 autowrap
t = p.read_text(encoding="utf-8")
for old3, name in [
    ('\taction_result_label = RichTextLabel.new()\n\taction_result_label.bbcode_enabled = true',
     'action_result_label'),
]:
    if old3 in t and "autowrap_mode" not in t.split("action_result_label")[1][:300]:
        pass  # 复杂，跳过

print()
print("Godot 完全关闭重开，按 F5")