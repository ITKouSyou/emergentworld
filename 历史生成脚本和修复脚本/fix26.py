# 1. daily 目标加钱奖励
# 2. 左侧面板加滚动
from pathlib import Path

# ============================================================
# 1. goal.py：daily 目标加小钱
# ============================================================
p = Path("server/systems/goal.py")
t = p.read_text(encoding="utf-8")

old_pool = '''DAILY_POOL = [
    ("earn_money_today", "今天赚到 {n} 钱", 5, 15, 0),
    ("hunt_today", "猎得 {n} 只猎物", 1, 20, 0),
    ("gather_today", "采集 {n} 次", 1, 10, 0),
    ("train_today", "修炼 {n} 次", 1, 15, 0),
    ("socialize_today", "社交 {n} 次", 1, 12, 0),
    ("explore_today", "探索 {n} 次", 1, 15, 0),
    ("event_today", "参与 {n} 个事件", 1, 20, 0),
]'''

new_pool = '''DAILY_POOL = [
    ("earn_money_today", "今天赚到 {n} 钱", 5, 15, 3),
    ("hunt_today", "猎得 {n} 只猎物", 1, 20, 5),
    ("gather_today", "采集 {n} 次", 1, 10, 2),
    ("train_today", "修炼 {n} 次", 1, 15, 2),
    ("socialize_today", "社交 {n} 次", 1, 12, 3),
    ("explore_today", "探索 {n} 次", 1, 15, 4),
    ("event_today", "参与 {n} 个事件", 1, 20, 5),
]'''

if old_pool in t:
    t = t.replace(old_pool, new_pool, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] daily 目标加钱奖励")
else:
    print("[skip] goal.py 已改过或未匹配")

# ============================================================
# 2. main.gd：左侧加滚动
# ============================================================
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

old_left = '''	# --- 左栏：我 ---
	var left_panel := VBoxContainer.new()
	left_panel.custom_minimum_size = Vector2(340, 0)
	left_panel.add_theme_constant_override("separation", 6)
	split.add_child(left_panel)
	_build_player_tab(left_panel)'''

new_left = '''	# --- 左栏：我（加滚动）---
	var left_scroll := ScrollContainer.new()
	left_scroll.custom_minimum_size = Vector2(340, 0)
	left_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	split.add_child(left_scroll)

	var left_panel := VBoxContainer.new()
	left_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left_panel.add_theme_constant_override("separation", 6)
	left_scroll.add_child(left_panel)
	_build_player_tab(left_panel)'''

if old_left in t:
    t = t.replace(old_left, new_left, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 左侧加滚动")
else:
    print("[fail] _build_ui 左侧锚点未找到")

print()
print("重启后端 + Godot 完全关闭重开")
print()
print("注意：daily 目标加钱需要重建 goal 表 → 调一次 /goal/reset")