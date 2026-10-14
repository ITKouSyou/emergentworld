# Part 69C：前端 + 一键 seed
from pathlib import Path

# 1. api.gd
p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")
if "func fetch_factions" not in t:
    anchor = "func fetch_world_state() -> void:"
    addition = '''signal factions_received(data: Dictionary)

func fetch_factions() -> void:
	_request("GET", "/faction", {}, "factions_received")

'''
    if anchor in t:
        t = t.replace(anchor, addition + anchor, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] api.gd 加 fetch_factions")

# 2. main.gd
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 2.1 变量
if "var faction_log:" not in t:
    anchor = "var quest_log: RichTextLabel\n"
    if anchor in t:
        t = t.replace(anchor, anchor + "var faction_log: RichTextLabel\n", 1)
        print("[fix] 加 faction_log 变量")

# 2.2 信号连接（强制插到 request_failed 前）
start = t.find("func _connect_signals() -> void:")
if start >= 0:
    after = t.find("\nfunc ", start + 1)
    if after < 0:
        after = len(t)
    body = t[start:after]
    if "api.factions_received.connect" not in body:
        anchor = "api.request_failed.connect(_on_request_failed)"
        if anchor not in body:
            anchor = "\tapi.request_failed.connect(_on_request_failed)"
        if anchor in body:
            indent = anchor[:len(anchor) - len(anchor.lstrip())]
            new_line = indent + "api.factions_received.connect(_on_factions_received)"
            body = body.replace(anchor, new_line + "\n" + anchor, 1)
            t = t[:start] + body + t[after:]
            print("[fix] 连接 factions_received")
    p.write_text(t, encoding="utf-8")
t = p.read_text(encoding="utf-8")

# 2.3 在 _build_ui 加"派系"Tab
old_right = '''	_build_event_tab(right_tabs)
	_build_quest_tab(right_tabs)
	_build_chronicle_tab(right_tabs)
	_build_market_tab(right_tabs)
	_build_reward_tab(right_tabs)
	_build_item_tab(right_tabs)'''
new_right = '''	_build_event_tab(right_tabs)
	_build_quest_tab(right_tabs)
	_build_faction_tab(right_tabs)
	_build_chronicle_tab(right_tabs)
	_build_market_tab(right_tabs)
	_build_reward_tab(right_tabs)
	_build_item_tab(right_tabs)'''
if old_right in t:
    t = t.replace(old_right, new_right, 1)
    print("[fix] _build_ui 加派系 Tab")

# 2.4 追加函数
t = p.read_text(encoding="utf-8")
if "_build_faction_tab" not in t:
    tail = '''

func _build_faction_tab(parent: TabContainer) -> void:
	var tab := VBoxContainer.new()
	tab.name = "派系"
	tab.add_theme_constant_override("separation", 6)
	parent.add_child(tab)

	var ctrl := HBoxContainer.new()
	ctrl.add_theme_constant_override("separation", 6)
	tab.add_child(ctrl)

	var refresh := Button.new()
	refresh.text = "刷新"
	refresh.pressed.connect(func(): api.fetch_factions())
	ctrl.add_child(refresh)

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	tab.add_child(scroll)

	faction_log = RichTextLabel.new()
	faction_log.bbcode_enabled = true
	faction_log.fit_content = true
	faction_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(faction_log)


func _on_factions_received(data: Dictionary) -> void:
	if faction_log == null:
		return
	faction_log.clear()

	var factions: Array = data.get("factions", [])
	var discount: float = float(data.get("market_discount", 1.0))

	faction_log.append_text("[b][color=gold]◆ 派系声望[/color][/b]\\n\\n")
	for f in factions:
		if not f is Dictionary:
			continue
		var label: String = str(f.get("label", "?"))
		var desc: String = str(f.get("desc", ""))
		var value: int = int(f.get("value", 0))
		var attitude: String = str(f.get("attitude", ""))

		var color := "gray"
		if value >= 20:
			color = "lightgreen"
		elif value >= 5:
			color = "white"
		elif value <= -20:
			color = "red"
		elif value <= -5:
			color = "orange"

		faction_log.append_text("[b]%s[/b]  [color=%s]%+d[/color]  [i]%s[/i]\\n" % [
			label, color, value, attitude,
		])
		faction_log.append_text("    [color=lightgray]%s[/color]\\n\\n" % desc)

	faction_log.append_text("\\n[b][color=cyan]◆ 市场折扣[/color][/b]\\n")
	if discount < 1.0:
		faction_log.append_text("    商帮声望让你享受 [color=green]%.0f%%[/color] 优惠\\n" % ((1.0 - discount) * 100))
	elif discount > 1.0:
		faction_log.append_text("    商帮态度冷淡，价格上浮 [color=red]%.0f%%[/color]\\n" % ((discount - 1.0) * 100))
	else:
		faction_log.append_text("    无折扣\\n")
'''
    t = t.rstrip() + "\n" + tail
    p.write_text(t, encoding="utf-8")
    print("[fix] 加派系 Tab")

# 2.5 _refresh_all 拉派系
t = p.read_text(encoding="utf-8")
i = t.find("func _refresh_all() -> void:")
if i >= 0:
    e = t.find("\nfunc ", i + 1)
    body = t[i:e]
    if "api.fetch_factions" not in body:
        body_new = body.rstrip() + "\n\tapi.fetch_factions()\n"
        t = t[:i] + body_new + t[e:]
        p.write_text(t, encoding="utf-8")
        print("[fix] _refresh_all 拉派系")

# 2.6 NPC 详情显示派系
t = p.read_text(encoding="utf-8")
old_npc = '''	lines.append("所在地：%s" % str(data.get("location_label", "")))'''
new_npc = '''	lines.append("所在地：%s" % str(data.get("location_label", "")))
	var fl: String = str(data.get("faction_label", ""))
	if fl != "" and fl != "中立":
		lines.append("所属派系：[color=gold]%s[/color]" % fl)'''
if old_npc in t and "所属派系" not in t:
    t = t.replace(old_npc, new_npc, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] NPC 详情显示派系")

# ============================================================
# 3. seed_world.py：seed 后分配派系
# ============================================================
p = Path("tools/seed_world.py")
t = p.read_text(encoding="utf-8")

if "assign_all_factions" not in t:
    t = t.replace(
        "from server.systems.schedule import generate_schedule",
        "from server.systems.schedule import generate_schedule\nfrom server.systems.faction import assign_all_factions",
        1,
    )
    old_seed = '''        build_families(session, npcs, rng)
        print("built families")'''
    new_seed = '''        # 分配派系
        stats = assign_all_factions(session)
        print("assigned factions: %r" % stats)

        build_families(session, npcs, rng)
        print("built families")'''
    if old_seed in t:
        t = t.replace(old_seed, new_seed, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] seed_world 分配派系")

print()
print("========== 全部完成 ==========")
print("运行：")
print("  python fix69a.py")
print("  python fix69b.py")
print("  python fix69c.py")
print("  Remove-Item data\\world.db")
print("  python tools\\seed_world.py --npc 14")
print("  uvicorn server.main:app")
print("Godot 完全关闭重开")