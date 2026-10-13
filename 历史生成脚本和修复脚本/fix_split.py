# 布局重构：三栏同时可见
from pathlib import Path

# 备份
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")
Path("client/main.gd.bak").write_text(t, encoding="utf-8")
print("[backup] client/main.gd.bak")

# ============================================================
# 1. 重写 _build_ui
# ============================================================
old_build = '''func _build_ui() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var margin := MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 12)
	margin.add_theme_constant_override("margin_top", 12)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_bottom", 12)
	add_child(margin)

	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 8)
	margin.add_child(root)

	_build_top_bar(root)

	tabs_root = TabContainer.new()
	tabs_root.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(tabs_root)

	_build_player_tab(tabs_root)
	_build_world_tab(tabs_root)'''

new_build = '''func _build_ui() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var margin := MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 12)
	margin.add_theme_constant_override("margin_top", 12)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_bottom", 12)
	add_child(margin)

	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 8)
	margin.add_child(root)

	_build_top_bar(root)

	# 三栏分屏
	var split := HSplitContainer.new()
	split.size_flags_vertical = Control.SIZE_EXPAND_FILL
	split.add_theme_constant_override("separation", 8)
	root.add_child(split)

	# --- 左栏：我 ---
	var left_panel := VBoxContainer.new()
	left_panel.custom_minimum_size = Vector2(340, 0)
	left_panel.add_theme_constant_override("separation", 6)
	split.add_child(left_panel)
	_build_player_tab(left_panel)

	# --- 中栏：地图 / 人物 ---
	var mid_tabs := TabContainer.new()
	mid_tabs.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	mid_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	split.add_child(mid_tabs)
	_build_map_tab(mid_tabs)
	_build_npc_tab(mid_tabs)

	# --- 右栏：事件 / 史册 / 奖励 / 物品 ---
	var right_tabs := TabContainer.new()
	right_tabs.custom_minimum_size = Vector2(420, 0)
	right_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	split.add_child(right_tabs)
	_build_event_tab(right_tabs)
	_build_chronicle_tab(right_tabs)
	_build_reward_tab(right_tabs)
	_build_item_tab(right_tabs)'''

if old_build in t:
    t = t.replace(old_build, new_build, 1)
    print("[fix] _build_ui 改成三栏")
else:
    print("[fail] _build_ui 锚点未找到")

# ============================================================
# 2. _build_player_tab 参数类型改 Container，去掉 tab name
# ============================================================
old_pt = '''func _build_player_tab(parent: TabContainer) -> void:
	player_tab_panel = VBoxContainer.new()
	player_tab_panel.name = "我"
	player_tab_panel.add_theme_constant_override("separation", 8)
	parent.add_child(player_tab_panel)'''

new_pt = '''func _build_player_tab(parent: Container) -> void:
	player_tab_panel = VBoxContainer.new()
	player_tab_panel.add_theme_constant_override("separation", 8)
	parent.add_child(player_tab_panel)

	var title := Label.new()
	title.text = "[我]"
	title.add_theme_font_size_override("font_size", 18)
	player_tab_panel.add_child(title)'''

if old_pt in t:
    t = t.replace(old_pt, new_pt, 1)
    print("[fix] _build_player_tab 参数改 Container")
else:
    print("[fail] _build_player_tab 锚点未找到")

# ============================================================
# 3. 删除 _build_world_tab，改成 _build_map_tab
# ============================================================
old_wt = '''func _build_world_tab(parent: TabContainer) -> void:
	# 主 Tab：地图
	map_view = MapView.new()
	map_view.name = "地图"
	map_view.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	map_view.size_flags_vertical = Control.SIZE_EXPAND_FILL
	map_view.npc_clicked.connect(_on_map_npc_clicked)
	parent.add_child(map_view)

	# NPC 面板
	_build_npc_tab(parent)

	# 编年史
	_build_event_tab(parent)

	# 史册
	_build_chronicle_tab(parent)

	# 奖励
	_build_reward_tab(parent)

	# 物品
	_build_item_tab(parent)'''

new_wt = '''func _build_map_tab(parent: TabContainer) -> void:
	map_view = MapView.new()
	map_view.name = "地图"
	map_view.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	map_view.size_flags_vertical = Control.SIZE_EXPAND_FILL
	map_view.npc_clicked.connect(_on_map_npc_clicked)
	parent.add_child(map_view)'''

if old_wt in t:
    t = t.replace(old_wt, new_wt, 1)
    print("[fix] _build_world_tab → _build_map_tab")
else:
    print("[fail] _build_world_tab 锚点未找到")

# ============================================================
# 4. 删除 tabs_root 变量声明
# ============================================================
old_var = "var tabs_root: TabContainer\n"
if old_var in t:
    t = t.replace(old_var, "", 1)
    print("[fix] 删除 tabs_root 变量")

p.write_text(t, encoding="utf-8")
print()
print("Godot 完全关闭重开，按 F5")