"""给主界面加 loading 状态：按钮禁用 + 计时提示 + 事件日志顶部占位。

改动：
    - 顶部状态栏旁加 loading_label，显示"⏳ 正在生成事件... (Ns)"
    - 触发/推进按钮在请求期间 disabled
    - "推进 24 tick" 显示进度 (n/24)
    - 请求失败时清除 loading
"""
from pathlib import Path

p = Path("client/main.gd")
text = p.read_text(encoding="utf-8")

# ---------- 1. 加成员变量 ----------
OLD_VARS = '''var map_poll_timer: Timer
var event_action_panel: VBoxContainer
var pending_events_by_id: Dictionary = {}
'''
NEW_VARS = '''var map_poll_timer: Timer
var event_action_panel: VBoxContainer
var pending_events_by_id: Dictionary = {}

# loading 状态
var loading_label: Label
var trigger_btn: Button
var step_btn: Button
var step24_btn: Button
var refresh_btn: Button
var loading_timer: Timer
var loading_started_ms: int = 0
var loading_message: String = ""
var is_step_24_running: bool = false
var step_24_done: int = 0
'''
if OLD_VARS not in text:
    print("未找到成员变量块，可能已改过")
    raise SystemExit(1)
text = text.replace(OLD_VARS, NEW_VARS)

# ---------- 2. 构建顶部栏 ----------
OLD_TOPBAR = '''func _build_top_bar(root: VBoxContainer) -> void:
	var top := HBoxContainer.new()
	top.add_theme_constant_override("separation", 12)
	root.add_child(top)

	status_label = Label.new()
	status_label.text = "加载中..."
	status_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(status_label)

	var step_btn := Button.new()
	step_btn.text = "推进一 tick"
	step_btn.pressed.connect(func(): api.step_world())
	top.add_child(step_btn)

	var step24_btn := Button.new()
	step24_btn.text = "推进 24 tick"
	step24_btn.pressed.connect(_on_step_24)
	top.add_child(step24_btn)

	var event_btn := Button.new()
	event_btn.text = "触发事件"
	event_btn.pressed.connect(func(): api.trigger_event())
	top.add_child(event_btn)

	var refresh_btn := Button.new()
	refresh_btn.text = "刷新"
	refresh_btn.pressed.connect(_refresh_all)
	top.add_child(refresh_btn)'''

NEW_TOPBAR = '''func _build_top_bar(root: VBoxContainer) -> void:
	var top := HBoxContainer.new()
	top.add_theme_constant_override("separation", 12)
	root.add_child(top)

	status_label = Label.new()
	status_label.text = "加载中..."
	status_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(status_label)

	loading_label = Label.new()
	loading_label.text = ""
	loading_label.add_theme_color_override("font_color", Color(1.0, 0.85, 0.3))
	top.add_child(loading_label)

	step_btn = Button.new()
	step_btn.text = "推进一 tick"
	step_btn.pressed.connect(_on_step_once)
	top.add_child(step_btn)

	step24_btn = Button.new()
	step24_btn.text = "推进 24 tick"
	step24_btn.pressed.connect(_on_step_24)
	top.add_child(step24_btn)

	trigger_btn = Button.new()
	trigger_btn.text = "触发事件"
	trigger_btn.pressed.connect(_on_trigger_event)
	top.add_child(trigger_btn)

	refresh_btn = Button.new()
	refresh_btn.text = "刷新"
	refresh_btn.pressed.connect(_refresh_all)
	top.add_child(refresh_btn)

	# loading 计时器
	loading_timer = Timer.new()
	loading_timer.wait_time = 0.5
	loading_timer.autostart = false
	loading_timer.timeout.connect(_on_loading_tick)
	add_child(loading_timer)'''

if OLD_TOPBAR not in text:
    print("未找到 _build_top_bar，可能已改过")
    raise SystemExit(1)
text = text.replace(OLD_TOPBAR, NEW_TOPBAR)

# ---------- 3. 加 loading 相关函数 ----------
NEW_LOADING_FUNCS = '''

# ================================================================ loading 状态

func _set_loading(msg: String) -> void:
	loading_message = msg
	if msg == "":
		loading_label.text = ""
		loading_timer.stop()
		trigger_btn.disabled = false
		step_btn.disabled = false
		step24_btn.disabled = false
		refresh_btn.disabled = false
	else:
		loading_started_ms = Time.get_ticks_msec()
		loading_label.text = "⏳ " + msg + " (0.0s)"
		loading_timer.start()
		trigger_btn.disabled = true
		step_btn.disabled = true
		if not is_step_24_running:
			step24_btn.disabled = true
		refresh_btn.disabled = true


func _on_loading_tick() -> void:
	if loading_message == "":
		loading_timer.stop()
		return
	var elapsed := (Time.get_ticks_msec() - loading_started_ms) / 1000.0
	loading_label.text = "⏳ %s (%.1fs)" % [loading_message, elapsed]


func _on_step_once() -> void:
	_set_loading("正在推进...")
	api.step_world()


func _on_trigger_event() -> void:
	_set_loading("正在生成事件（调用 LLM，请稍候）...")
	api.trigger_event()
'''

# 插到 _build_top_bar 后面的空行处，比较靠前的位置
marker = "\n\nfunc _build_left_panel(split: HSplitContainer) -> void:"
if marker not in text:
    print("未找到插入位置")
    raise SystemExit(1)
text = text.replace(marker, NEW_LOADING_FUNCS + marker, 1)

# ---------- 4. 改 _on_step_24 ----------
OLD_STEP24 = '''func _on_step_24() -> void:
	_step_24_recursive(24)


func _step_24_recursive(remaining: int) -> void:
	if remaining <= 0:
		return
	api.step_world()
	await get_tree().create_timer(0.6).timeout
	_step_24_recursive(remaining - 1)'''

NEW_STEP24 = '''func _on_step_24() -> void:
	is_step_24_running = true
	step_24_done = 0
	step24_btn.disabled = true
	_set_loading("推进 24 tick (0/24)")
	_step_24_recursive(24)


func _step_24_recursive(remaining: int) -> void:
	if remaining <= 0:
		is_step_24_running = false
		step_24_done = 0
		_set_loading("")
		_refresh_all()
		return
	api.step_world()
	await get_tree().create_timer(0.3).timeout
	_step_24_recursive(remaining - 1)'''

if OLD_STEP24 not in text:
    print("未找到 _on_step_24，可能已改过")
    raise SystemExit(1)
text = text.replace(OLD_STEP24, NEW_STEP24)

# ---------- 5. 事件触发回调里清 loading ----------
OLD_EVENT_TRIGGERED = '''func _on_event_triggered(data: Dictionary) -> void:
	if data.has("event_summary") and data.get("event_summary") != null:
		var summary: String = str(data.get("event_summary", ""))
		var tpl_label: String = str(data.get("template_label", ""))
		if summary != "":
			event_log.append_text("\\n[color=orange]→[/color] [b]%s[/b] %s" % [tpl_label, summary])
	_refresh_all()'''

NEW_EVENT_TRIGGERED = '''func _on_event_triggered(data: Dictionary) -> void:
	# 24 tick 循环中不清 loading
	if is_step_24_running:
		step_24_done += 1
		_set_loading("推进 24 tick (%d/24)" % step_24_done)
	else:
		_set_loading("")

	if data.has("event_summary") and data.get("event_summary") != null:
		var summary: String = str(data.get("event_summary", ""))
		var tpl_label: String = str(data.get("template_label", ""))
		if summary != "":
			event_log.append_text("\\n[color=orange]→[/color] [b]%s[/b] %s" % [tpl_label, summary])

	# 立刻拉取最新事件列表（异步）
	api.fetch_events(20)
	api.fetch_rewards(20)
	api.fetch_items(100)
	api.fetch_map()
	api.fetch_world_state()
	api.fetch_npcs()
	if current_npc_id != "":
		api.fetch_npc_items(current_npc_id)'''

if OLD_EVENT_TRIGGERED not in text:
    print("未找到 _on_event_triggered，可能已改过")
    raise SystemExit(1)
text = text.replace(OLD_EVENT_TRIGGERED, NEW_EVENT_TRIGGERED)

# ---------- 6. 事件选择按钮点击时显示 loading ----------
OLD_CHOICE = '''func _on_event_choice_pressed(event_id: String, choice_id: String) -> void:
	api.resolve_event(event_id, choice_id)'''

NEW_CHOICE = '''func _on_event_choice_pressed(event_id: String, choice_id: String) -> void:
	_set_loading("正在结算（调用 LLM）...")
	# 禁用选项按钮，防止重复点
	for child in event_action_panel.get_children():
		_disable_recursive(child)
	api.resolve_event(event_id, choice_id)


func _disable_recursive(node: Node) -> void:
	if node is Button:
		(node as Button).disabled = true
	for child in node.get_children():
		_disable_recursive(child)'''

if OLD_CHOICE not in text:
    print("未找到 _on_event_choice_pressed，可能已改过")
    raise SystemExit(1)
text = text.replace(OLD_CHOICE, NEW_CHOICE)

# ---------- 7. 事件结算完成时清 loading ----------
OLD_RESOLVED = '''func _on_event_resolved(data: Dictionary) -> void:
	# 清空当前选中，刷新
	current_event_id = ""
	_refresh_all()'''

NEW_RESOLVED = '''func _on_event_resolved(data: Dictionary) -> void:
	_set_loading("")
	current_event_id = ""
	_refresh_all()'''

if OLD_RESOLVED not in text:
    print("未找到 _on_event_resolved，可能已改过")
    raise SystemExit(1)
text = text.replace(OLD_RESOLVED, NEW_RESOLVED)

# ---------- 8. 请求失败时清 loading ----------
OLD_FAILED = '''func _on_request_failed(endpoint: String, error: String) -> void:
	push_warning("Request failed: %s -> %s" % [endpoint, error])
	status_label.text = "[color=red]错误：%s[/color]" % error'''

NEW_FAILED = '''func _on_request_failed(endpoint: String, error: String) -> void:
	push_warning("Request failed: %s -> %s" % [endpoint, error])
	status_label.text = "[color=red]错误：%s[/color]" % error
	# 请求失败也要清除 loading，避免按钮永远禁用
	if is_step_24_running:
		is_step_24_running = false
		step_24_done = 0
	_set_loading("")'''

if OLD_FAILED not in text:
    print("未找到 _on_request_failed，可能已改过")
    raise SystemExit(1)
text = text.replace(OLD_FAILED, NEW_FAILED)

# ---------- 9. 写回 ----------
p.write_text(text, encoding="utf-8", newline="\n")
print("[fix] client/main.gd 已更新")
print()
print("改动摘要：")
print("  - 顶部加 loading 提示，显示已等待秒数")
print("  - 请求进行时禁用 触发/推进/刷新 按钮")
print("  - 24 tick 显示进度 (n/24)")
print("  - 事件选项按钮点击后立即禁用，防重复")
print("  - 请求失败自动清 loading")
print()
print("回到 Godot 按 F5 重启")