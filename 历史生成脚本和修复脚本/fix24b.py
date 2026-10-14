# 前端：目标面板 + 领取奖励
from pathlib import Path

# 1. api.gd
p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")
if "func fetch_goals" not in t:
    anchor = "func fetch_world_state() -> void:"
    addition = '''signal goals_received(data: Dictionary)
signal goal_claimed(data: Dictionary)

func fetch_goals() -> void:
	_request("GET", "/goal", {}, "goals_received")

func claim_goal(goal_id: String) -> void:
	_request("POST", "/goal/claim", {"goal_id": goal_id}, "goal_claimed")

'''
    if anchor in t:
        t = t.replace(anchor, addition + anchor, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] api.gd 加 goal 方法")

# 2. main.gd 加目标面板到"我"栏
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 2.1 变量
if "var goal_log:" not in t:
    anchor = "var market_log: RichTextLabel\n"
    if anchor in t:
        t = t.replace(anchor, anchor + "var goal_log: RichTextLabel\n", 1)
        print("[fix] 加 goal_log 变量")

# 2.2 信号
start = t.find("func _connect_signals() -> void:")
if start >= 0:
    after = t.find("\nfunc ", start + 1)
    if after < 0:
        after = len(t)
    body = t[start:after]
    if "api.goals_received.connect" not in body:
        anchor = "api.request_failed.connect(_on_request_failed)"
        if anchor not in body:
            anchor = "\tapi.request_failed.connect(_on_request_failed)"
        if anchor in body:
            indent = anchor[:len(anchor) - len(anchor.lstrip())]
            new_lines = (
                indent + "api.goals_received.connect(_on_goals_received)\n"
                + indent + "api.goal_claimed.connect(_on_goal_claimed)\n"
            )
            body = body.replace(anchor, new_lines + anchor, 1)
            t = t[:start] + body + t[after:]
            print("[fix] 连接目标信号")

p.write_text(t, encoding="utf-8")

# 2.3 在 _build_player_tab 里加目标区
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

if "_build_goal_section" not in t:
    tail = '''

func _build_goal_section() -> void:
	# 在"我"面板里追加目标区（在属性标题之前）
	if player_tab_panel == null:
		return
	if goal_log != null and is_instance_valid(goal_log):
		return

	var insert_index := player_tab_panel.get_child_count()
	for i in range(player_tab_panel.get_child_count()):
		var c := player_tab_panel.get_child(i)
		if c is Label:
			var lbl := c as Label
			if lbl.text.begins_with("属性"):
				insert_index = i
				break

	var title := Label.new()
	title.text = "[目标]"
	title.add_theme_font_size_override("font_size", 16)

	goal_log = RichTextLabel.new()
	goal_log.bbcode_enabled = true
	goal_log.fit_content = true
	goal_log.meta_clicked.connect(_on_goal_meta_clicked)
	goal_log.custom_minimum_size = Vector2(0, 120)

	player_tab_panel.add_child(title)
	player_tab_panel.move_child(title, insert_index)
	player_tab_panel.add_child(goal_log)
	player_tab_panel.move_child(goal_log, insert_index + 1)


func _on_goals_received(data: Dictionary) -> void:
	if goal_log == null:
		return
	goal_log.clear()

	var daily: Array = data.get("daily", [])
	var milestones: Array = data.get("milestones", [])

	goal_log.append_text("[color=gold]◆ 今日[/color]\\n")
	if daily.is_empty():
		goal_log.append_text("  （无）\\n")
	for g in daily:
		if not g is Dictionary:
			continue
		_render_goal(g)
	goal_log.append_text("\\n[color=cyan]◆ 长期[/color]\\n")
	for g in milestones:
		if not g is Dictionary:
			continue
		_render_goal(g)


func _render_goal(g: Dictionary) -> void:
	var label: String = str(g.get("label", "?"))
	var progress: int = int(g.get("progress", 0))
	var target: int = int(g.get("target", 1))
	var done: bool = bool(g.get("done", false))
	var claimed: bool = bool(g.get("claimed", false))
	var gid: String = str(g.get("id", ""))
	var exp_r: int = int(g.get("exp_reward", 0))
	var money_r: int = int(g.get("money_reward", 0))

	if claimed:
		goal_log.append_text("  [color=dimgray]✓ %s  (已领取)[/color]\\n" % label)
		return
	if done:
		var reward := []
		if exp_r > 0:
			reward.append("经验 +%d" % exp_r)
		if money_r > 0:
			reward.append("铜钱 +%d" % money_r)
		goal_log.append_text("  [color=gold][url=claim:%s][b]★ %s[/b]  [领取：%s][/url][/color]\\n" % [
			gid, label, "、".join(reward),
		])
		return

	goal_log.append_text("  · %s  (%d/%d)\\n" % [label, progress, target])


func _on_goal_meta_clicked(meta) -> void:
	var s := str(meta)
	if s.begins_with("claim:"):
		api.claim_goal(s.substr(6))


func _on_goal_claimed(data: Dictionary) -> void:
	# 刷新玩家 + 目标
	api.fetch_player()
	api.fetch_goals()
'''
    t = t.rstrip() + "\n" + tail
    p.write_text(t, encoding="utf-8")
    print("[fix] 加 _build_goal_section")

# 2.4 在 _ready 里调用 _build_goal_section
t = p.read_text(encoding="utf-8")
if "_build_goal_section()" not in t.replace("func _build_goal_section", ""):
    anchor = "\t_ensure_action_ui()\n"
    if anchor in t:
        t = t.replace(anchor, anchor + "\t_build_goal_section()\n", 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] 调用 _build_goal_section")

# 2.5 _refresh_all 里拉目标
t = p.read_text(encoding="utf-8")
if "api.fetch_goals()" not in t:
    i = t.find("func _refresh_all")
    if i >= 0:
        e = t.find("\nfunc ", i + 1)
        body = t[i:e]
        body_new = body.rstrip() + "\n\tapi.fetch_goals()\n"
        t = t[:i] + body_new + t[e:]
        p.write_text(t, encoding="utf-8")
        print("[fix] _refresh_all 拉目标")

# 2.6 _on_i18n_received 后也拉一次目标
t = p.read_text(encoding="utf-8")
if "_refresh_all()" in t and "api.fetch_goals()" not in t.split("_refresh_all")[0][-500:]:
    pass

print()
print("前端完成。重启 uvicorn + Godot 完全关闭重开")