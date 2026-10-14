# 1. 任务面板 Label → RichTextLabel
# 2. Tab 栏字体缩小
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# ---- 1. 替换 _render_npc_quests_panel 里的 Label ----

# 待提交标题
t = t.replace(
    '''		var t1 := Label.new()
		t1.text = "[待提交]"
		t1.add_theme_color_override("font_color", Color(1.0, 0.6, 0.3))
		npc_quests_panel.add_child(t1)''',
    '''		var t1 := RichTextLabel.new()
		t1.bbcode_enabled = true
		t1.fit_content = true
		t1.custom_minimum_size = Vector2(0, 20)
		t1.text = "[color=orange][b][待提交][/b][/color]"
		npc_quests_panel.add_child(t1)''',
)

# 可接受标题
t = t.replace(
    '''		var t2 := Label.new()
		t2.text = "[可接受]"
		t2.add_theme_color_override("font_color", Color(1.0, 0.85, 0.3))
		npc_quests_panel.add_child(t2)''',
    '''		var t2 := RichTextLabel.new()
		t2.bbcode_enabled = true
		t2.fit_content = true
		t2.custom_minimum_size = Vector2(0, 20)
		t2.text = "[color=gold][b][可接受][/b][/color]"
		npc_quests_panel.add_child(t2)''',
)

# 待提交 info label
t = t.replace(
    '''			var info := Label.new()
			var title_s: String = str(q.get("title", "?"))
			var exp_r: int = int(q.get("reward_exp", 0))
			var money_r: int = int(q.get("reward_money", 0))
			var ready: bool = bool(q.get("ready", false))
			var rk: String = str(q.get("require_item_kind", ""))
			var rc: int = int(q.get("require_item_count", 0))

			var status := ""
			if rc > 0:
				if ready:
					status = "[color=green]（已集齐%s）[/color]" % rk
				else:
					status = "[color=gray]（还需%s×%d）[/color]" % [rk, rc]

			info.text = "%s  (%d经验,%d钱) %s" % [title_s, exp_r, money_r, status]
			info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			row.add_child(info)''',
    '''			var info := RichTextLabel.new()
			info.bbcode_enabled = true
			info.fit_content = true
			info.custom_minimum_size = Vector2(0, 20)
			var title_s: String = str(q.get("title", "?"))
			var exp_r: int = int(q.get("reward_exp", 0))
			var money_r: int = int(q.get("reward_money", 0))
			var ready: bool = bool(q.get("ready", false))
			var rk: String = str(q.get("require_item_kind", ""))
			var rc: int = int(q.get("require_item_count", 0))

			var status := ""
			if rc > 0:
				if ready:
					status = "[color=green]（已集齐%s）[/color]" % rk
				else:
					status = "[color=gray]（还需%s×%d）[/color]" % [rk, rc]

			info.text = "%s  (%d经验,%d钱) %s" % [title_s, exp_r, money_r, status]
			info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			row.add_child(info)''',
)

# 可接受 info label
t = t.replace(
    '''			var info2 := Label.new()
			var title_s2: String = str(q.get("title", "?"))
			var exp_r2: int = int(q.get("reward_exp", 0))
			var money_r2: int = int(q.get("reward_money", 0))
			var loc_label: String = str(q.get("require_location_label", ""))
			info2.text = "%s -> %s (%d经验,%d钱)" % [title_s2, loc_label, exp_r2, money_r2]
			info2.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			row2.add_child(info2)''',
    '''			var info2 := RichTextLabel.new()
			info2.bbcode_enabled = true
			info2.fit_content = true
			info2.custom_minimum_size = Vector2(0, 20)
			var title_s2: String = str(q.get("title", "?"))
			var exp_r2: int = int(q.get("reward_exp", 0))
			var money_r2: int = int(q.get("reward_money", 0))
			var loc_label: String = str(q.get("require_location_label", ""))
			info2.text = "%s -> %s (%d经验,%d钱)" % [title_s2, loc_label, exp_r2, money_r2]
			info2.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			row2.add_child(info2)''',
)

p.write_text(t, encoding="utf-8")
print("[fix] 任务面板 Label → RichTextLabel")

# ---- 2. Tab 字体缩小 ----

# 给所有 TabContainer 加小字体主题
old_tab = '''func _build_ui() -> void:'''
new_tab = '''func _make_small_tab_theme() -> Theme:
	var theme := Theme.new()
	theme.set_font_size("font_size", "TabBar", 12)
	return theme


func _build_ui() -> void:'''

if old_tab in t and "_make_small_tab_theme" not in t:
    t = t.replace(old_tab, new_tab, 1)
    print("[fix] 加小字体主题函数")

# 给三个 TabContainer 应用
# mid_tabs
t = t.replace(
    '''	var mid_tabs := TabContainer.new()
	mid_tabs.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	mid_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	split.add_child(mid_tabs)''',
    '''	var mid_tabs := TabContainer.new()
	mid_tabs.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	mid_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	mid_tabs.add_theme_font_size_override("font_size", 12)
	mid_tabs.add_theme_stylebox_override("tab_selected", StyleBoxEmpty.new())
	split.add_child(mid_tabs)''',
)

# right_tabs
t = t.replace(
    '''	var right_tabs := TabContainer.new()
	right_tabs.custom_minimum_size = Vector2(420, 0)
	right_tabs.size_flags_horizontal = Control.SIZE_SHRINK_END
	right_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	split.add_child(right_tabs)''',
    '''	var right_tabs := TabContainer.new()
	right_tabs.custom_minimum_size = Vector2(440, 0)
	right_tabs.size_flags_horizontal = Control.SIZE_SHRINK_END
	right_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	right_tabs.add_theme_font_size_override("font_size", 11)
	split.add_child(right_tabs)''',
)

p.write_text(t, encoding="utf-8")
print("[fix] Tab 字号缩小到 11-12")

# 检查是否应用
t = p.read_text(encoding="utf-8")
print()
print("mid_tabs 字号：%s" % ("mid_tabs.add_theme_font_size_override" in t))
print("right_tabs 字号：%s" % ("right_tabs.add_theme_font_size_override" in t))

print()
print("Godot 完全关闭重开，按 F5")