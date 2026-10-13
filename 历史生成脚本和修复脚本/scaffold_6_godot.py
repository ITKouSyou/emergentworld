r"""EmergentWorld scaffold - Part 6: Godot 4 客户端。

运行：
    python scaffold_6_godot.py --force
"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

# ================================================================ project.godot

FILES["client/project.godot"] = '''config_version=5

[application]

config/name="EmergentWorld Client"
run/main_scene="res://Main.tscn"
config/features=PackedStringArray("4.3", "GL Compatibility")
config/icon="res://icon.svg"

[display]

window/size/viewport_width=1360
window/size/viewport_height=820
window/stretch/mode="canvas_items"

[rendering]

renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
'''

# ================================================================ icon.svg

FILES["client/icon.svg"] = '''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">
  <rect width="64" height="64" fill="#2b2b3c"/>
  <circle cx="32" cy="32" r="18" fill="none" stroke="#e0c060" stroke-width="3"/>
  <circle cx="32" cy="32" r="6" fill="#e0c060"/>
</svg>
'''

# ================================================================ api.gd

FILES["client/api.gd"] = '''class_name GameApi
extends Node

const BASE_URL := "http://127.0.0.1:8000"

signal world_state_received(data: Dictionary)
signal npc_list_received(data: Array)
signal npc_detail_received(data: Dictionary)
signal dialogue_received(data: Dictionary)
signal event_triggered(data: Dictionary)
signal event_list_received(data: Array)
signal relationships_received(data: Array)
signal reward_list_received(data: Array)
signal request_failed(endpoint: String, error: String)


func fetch_world_state() -> void:
	_request("GET", "/world/state", {}, "world_state_received")


func step_world() -> void:
	_request("POST", "/world/step", {}, "event_triggered")


func trigger_event() -> void:
	_request("POST", "/event/trigger", {}, "event_triggered")


func fetch_npcs() -> void:
	_request("GET", "/npc", {}, "npc_list_received")


func fetch_npc_detail(npc_id: String) -> void:
	_request("GET", "/npc/%s" % npc_id, {}, "npc_detail_received")


func fetch_relationships(npc_id: String) -> void:
	_request("GET", "/npc/%s/relationships" % npc_id, {}, "relationships_received")


func send_dialogue(npc_id: String, player_input: String) -> void:
	_request("POST", "/npc/%s/dialogue" % npc_id, {"player_input": player_input}, "dialogue_received")


func fetch_events(limit: int = 20) -> void:
	_request("GET", "/event?limit=%d" % limit, {}, "event_list_received")


func fetch_rewards(limit: int = 20) -> void:
	_request("GET", "/reward?limit=%d" % limit, {}, "reward_list_received")


func _request(method: String, path: String, body: Dictionary, signal_name: String) -> void:
	var http := HTTPRequest.new()
	http.timeout = 60.0
	add_child(http)
	http.request_completed.connect(_on_response.bind(http, signal_name))

	var url := BASE_URL + path
	var headers := PackedStringArray([
		"Content-Type: application/json",
		"Accept: application/json",
	])

	var err: int
	if method == "GET":
		err = http.request(url, headers, HTTPClient.METHOD_GET)
	else:
		var body_str := JSON.stringify(body)
		err = http.request(url, headers, HTTPClient.METHOD_POST, body_str)

	if err != OK:
		http.queue_free()
		request_failed.emit(signal_name, "request failed: %d" % err)


func _on_response(
	result: int,
	response_code: int,
	_headers: PackedStringArray,
	body: PackedByteArray,
	http: HTTPRequest,
	signal_name: String
) -> void:
	http.queue_free()

	if result != HTTPRequest.RESULT_SUCCESS:
		request_failed.emit(signal_name, "transport error: %d" % result)
		return

	var text := body.get_string_from_utf8()
	var data = JSON.parse_string(text)

	if response_code < 200 or response_code >= 300:
		var msg := "HTTP %d" % response_code
		if data is Dictionary and data.has("detail"):
			msg += ": " + str(data["detail"])
		request_failed.emit(signal_name, msg)
		return

	if data == null:
		request_failed.emit(signal_name, "JSON parse failed")
		return

	emit_signal(signal_name, data)
'''

# ================================================================ main.gd

FILES["client/main.gd"] = '''extends Control

var api: GameApi

var status_label: Label
var npc_list: ItemList
var npc_detail: RichTextLabel
var relationship_label: RichTextLabel
var dialogue_log: RichTextLabel
var dialogue_input: LineEdit
var event_log: RichTextLabel
var reward_log: RichTextLabel

var current_npc_id: String = ""
var npc_data: Dictionary = {}
var npc_order: Array[String] = []


func _ready() -> void:
	api = GameApi.new()
	add_child(api)
	_connect_signals()
	_build_ui()
	_refresh_all()


func _connect_signals() -> void:
	api.world_state_received.connect(_on_world_state)
	api.npc_list_received.connect(_on_npc_list)
	api.npc_detail_received.connect(_on_npc_detail)
	api.dialogue_received.connect(_on_dialogue)
	api.event_triggered.connect(_on_event_triggered)
	api.event_list_received.connect(_on_event_list)
	api.relationships_received.connect(_on_relationships)
	api.reward_list_received.connect(_on_reward_list)
	api.request_failed.connect(_on_request_failed)


func _build_ui() -> void:
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

	var split := HSplitContainer.new()
	split.size_flags_vertical = Control.SIZE_EXPAND_FILL
	split.add_theme_constant_override("separation", 8)
	root.add_child(split)

	_build_left_panel(split)
	_build_middle_panel(split)
	_build_right_panel(split)


func _build_top_bar(root: VBoxContainer) -> void:
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

	var event_btn := Button.new()
	event_btn.text = "触发事件"
	event_btn.pressed.connect(func(): api.trigger_event())
	top.add_child(event_btn)

	var refresh_btn := Button.new()
	refresh_btn.text = "刷新"
	refresh_btn.pressed.connect(_refresh_all)
	top.add_child(refresh_btn)


func _build_left_panel(split: HSplitContainer) -> void:
	var panel := VBoxContainer.new()
	panel.custom_minimum_size = Vector2(240, 0)
	panel.add_theme_constant_override("separation", 6)
	split.add_child(panel)

	var title := Label.new()
	title.text = "NPC 列表"
	panel.add_child(title)

	npc_list = ItemList.new()
	npc_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	npc_list.item_selected.connect(_on_npc_selected)
	panel.add_child(npc_list)


func _build_middle_panel(split: HSplitContainer) -> void:
	var panel := VBoxContainer.new()
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	panel.add_theme_constant_override("separation", 6)
	split.add_child(panel)

	var detail_title := Label.new()
	detail_title.text = "NPC 详情"
	panel.add_child(detail_title)

	var detail_scroll := ScrollContainer.new()
	detail_scroll.custom_minimum_size = Vector2(0, 200)
	detail_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	panel.add_child(detail_scroll)

	npc_detail = RichTextLabel.new()
	npc_detail.bbcode_enabled = true
	npc_detail.fit_content = true
	npc_detail.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	npc_detail.text = "选择一个 NPC 查看详情"
	detail_scroll.add_child(npc_detail)

	relationship_label = RichTextLabel.new()
	relationship_label.bbcode_enabled = true
	relationship_label.fit_content = true
	relationship_label.custom_minimum_size = Vector2(0, 80)
	panel.add_child(relationship_label)

	var dlg_title := Label.new()
	dlg_title.text = "对话"
	panel.add_child(dlg_title)

	var dlg_scroll := ScrollContainer.new()
	dlg_scroll.custom_minimum_size = Vector2(0, 120)
	dlg_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	panel.add_child(dlg_scroll)

	dialogue_log = RichTextLabel.new()
	dialogue_log.bbcode_enabled = true
	dialogue_log.fit_content = true
	dialogue_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	dialogue_log.text = ""
	dlg_scroll.add_child(dialogue_log)

	var dlg_input_row := HBoxContainer.new()
	dlg_input_row.add_theme_constant_override("separation", 6)
	panel.add_child(dlg_input_row)

	dialogue_input = LineEdit.new()
	dialogue_input.placeholder_text = "对 NPC 说..."
	dialogue_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	dialogue_input.text_submitted.connect(_on_dialogue_submit)
	dlg_input_row.add_child(dialogue_input)

	var send_btn := Button.new()
	send_btn.text = "发送"
	send_btn.pressed.connect(func(): _on_dialogue_submit(dialogue_input.text))
	dlg_input_row.add_child(send_btn)


func _build_right_panel(split: HSplitContainer) -> void:
	var panel := VBoxContainer.new()
	panel.custom_minimum_size = Vector2(360, 0)
	panel.add_theme_constant_override("separation", 6)
	split.add_child(panel)

	var title := Label.new()
	title.text = "事件日志"
	panel.add_child(title)

	var ev_scroll := ScrollContainer.new()
	ev_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	panel.add_child(ev_scroll)

	event_log = RichTextLabel.new()
	event_log.bbcode_enabled = true
	event_log.fit_content = true
	event_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ev_scroll.add_child(event_log)

	var rwd_title := Label.new()
	rwd_title.text = "最近奖励"
	panel.add_child(rwd_title)

	var rwd_scroll := ScrollContainer.new()
	rwd_scroll.custom_minimum_size = Vector2(0, 100)
	panel.add_child(rwd_scroll)

	reward_log = RichTextLabel.new()
	reward_log.bbcode_enabled = true
	reward_log.fit_content = true
	reward_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rwd_scroll.add_child(reward_log)


func _refresh_all() -> void:
	api.fetch_world_state()
	api.fetch_npcs()
	api.fetch_events(20)
	api.fetch_rewards(10)


func _on_world_state(data: Dictionary) -> void:
	var director = data.get("director", {})
	var tension: float = 0.0
	if director is Dictionary:
		tension = float(director.get("tension", 0.0))
	status_label.text = "Day %d, %02d:00   Tick %d   Tension %.2f" % [
		int(data.get("day", 0)),
		int(data.get("hour", 0)),
		int(data.get("tick", 0)),
		tension,
	]


func _on_npc_list(data: Array) -> void:
	npc_data.clear()
	npc_order.clear()
	npc_list.clear()
	for npc in data:
		if not npc is Dictionary:
			continue
		var id: String = str(npc.get("id", ""))
		var name: String = str(npc.get("name", "?"))
		npc_data[id] = npc
		npc_order.append(id)
		npc_list.add_item("%s   (%s)" % [name, id.substr(4, 6)])


func _on_npc_selected(index: int) -> void:
	if index < 0 or index >= npc_order.size():
		return
	current_npc_id = npc_order[index]
	api.fetch_npc_detail(current_npc_id)
	api.fetch_relationships(current_npc_id)
	dialogue_log.text = "[i]开始与 %s 对话[/i]\\n" % str(npc_data[current_npc_id].get("name", "?"))


func _on_npc_detail(data: Dictionary) -> void:
	var lines: Array[String] = []
	lines.append("[b][color=yellow]%s[/color][/b]  age %d" % [
		str(data.get("name", "?")),
		int(data.get("age", 0)),
	])
	lines.append("位置: %s" % str(data.get("location_id", "?")))
	lines.append("")

	lines.append("[b]性格[/b]")
	var traits: Dictionary = data.get("traits", {})
	for k in traits:
		lines.append("   %s: %.2f" % [str(k), float(traits[k])])

	lines.append("")
	lines.append("[b]需求[/b]")
	var needs: Dictionary = data.get("needs", {})
	for k in needs:
		lines.append("   %s: %.2f" % [str(k), float(needs[k])])

	lines.append("")
	lines.append("[b]目标[/b]")
	var goals: Array = data.get("goals", [])
	for g in goals:
		lines.append("   - %s" % str(g))

	npc_detail.text = "\\n".join(lines)


func _on_relationships(data: Array) -> void:
	if data.is_empty():
		relationship_label.text = "[i]（暂无关系记录）[/i]"
		return
	var lines: Array[String] = ["[b]关系[/b]"]
	for r in data:
		if not r is Dictionary:
			continue
		var other: String = ""
		if str(r.get("from_npc", "")) == current_npc_id:
			other = str(r.get("to_npc", ""))
		else:
			other = str(r.get("from_npc", ""))
		lines.append("   %s   trust=%.2f   aff=%.2f   fear=%.2f   debt=%.2f" % [
			other.substr(0, 10),
			float(r.get("trust", 0)),
			float(r.get("affection", 0)),
			float(r.get("fear", 0)),
			float(r.get("debt", 0)),
		])
	relationship_label.text = "\\n".join(lines)


func _on_dialogue_submit(text: String) -> void:
	text = text.strip_edges()
	if text == "" or current_npc_id == "":
		return
	dialogue_log.append_text("\\n[b]你:[/b] %s" % text)
	dialogue_input.text = ""
	api.send_dialogue(current_npc_id, text)


func _on_dialogue(data: Dictionary) -> void:
	var name: String = str(data.get("npc_name", "NPC"))
	var reply: String = str(data.get("reply", ""))
	dialogue_log.append_text("\\n[b][color=cyan]%s:[/color][/b] %s\\n" % [name, reply])


func _on_event_triggered(data: Dictionary) -> void:
	if data.has("event_summary") and data.get("event_summary") != null:
		var summary: String = str(data.get("event_summary", ""))
		if summary != "":
			event_log.append_text("\\n[color=orange]→[/color] %s" % summary)
	api.fetch_world_state()
	api.fetch_events(20)
	api.fetch_rewards(10)
	api.fetch_npcs()


func _on_event_list(data: Array) -> void:
	event_log.clear()
	for e in data:
		if not e is Dictionary:
			continue
		var state: String = str(e.get("state", ""))
		var color := "white"
		if state == "resolved":
			color = "lightgreen"
		elif state == "rejected":
			color = "gray"
		elif state == "active":
			color = "yellow"

		var summary: String = ""
		var payload = e.get("payload", {})
		if payload is Dictionary:
			summary = str(payload.get("summary", ""))

		event_log.append_text("[color=%s][%s][/color] %s\\n" % [
			color,
			str(e.get("template_id", "?")),
			summary,
		])


func _on_reward_list(data: Array) -> void:
	reward_log.clear()
	for r in data:
		if not r is Dictionary:
			continue
		reward_log.append_text("[b]%s[/b]  %.2f  %s\\n" % [
			str(r.get("kind", "?")),
			float(r.get("value", 0)),
			str(r.get("description", "")),
		])


func _on_request_failed(endpoint: String, error: String) -> void:
	push_warning("Request failed: %s -> %s" % [endpoint, error])
	status_label.text = "[color=red]错误: %s[/color]" % error
'''

# ================================================================ Main.tscn

FILES["client/Main.tscn"] = '''[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://main.gd" id="1_main"]

[node name="Main" type="Control"]
layout_mode = 3
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
script = ExtResource("1_main")
'''

# ================================================================ README

FILES["client/README.md"] = '''# EmergentWorld Godot Client

## 首次运行

1. 打开 Godot 4.3+。
2. 点 "导入"（Import）。
3. 选择本目录下的 `project.godot`。
4. 点 "导入并编辑"（Import & Edit）。
5. 确认后端已启动：在项目根目录运行 `uvicorn server.main:app --reload`。
6. 在 Godot 中按 `F5` 运行。

## 界面说明

- **顶部**：世界状态（天数/时间/tick/张力）+ 操作按钮
  - "推进一 tick"：时间 +1，可能自动触发事件
  - "触发事件"：强制触发一次事件
  - "刷新"：重新加载世界状态、NPC、事件、奖励
- **左栏**：NPC 列表，点击选中
- **中栏**：NPC 详情 + 关系 + 对话
  - 在输入框打字按回车或点"发送"和 NPC 对话
- **右栏**：事件日志 + 最近奖励

## 常见问题

**Q: 显示 "错误: transport error"**

后端没启动，或端口不是 8000。先在项目根目录运行 `uvicorn server.main:app --reload`。

**Q: 对话没反应**

该 NPC 还没参与过事件，所以没有记忆。先去触发几个事件，然后回来再对话。

**Q: 事件日志空白**

还没触发过事件。点"触发事件"或多次点"推进一 tick"。

## 后续扩展方向

- NPC 头像（用 `asset_params` 生成 2D 头像）
- 地图视图（显示 NPC 位置）
- 关系图可视化
- 编年史面板（读取 evolve 输出）
'''

# ================================================================ 主流程

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    written = 0
    skipped = 0
    for rel, content in FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and not args.force:
            print(f"[skip]  {rel}")
            skipped += 1
            continue
        p.write_text(content, encoding="utf-8", newline="\n")
        print(f"[write] {rel}")
        written += 1

    print(f"\nPart 6 done. written={written} skipped={skipped}")
    print()
    print("下一步：")
    print("  1. 保持后端运行: uvicorn server.main:app --reload")
    print("  2. 打开 Godot 4.x，导入 client/project.godot")
    print("  3. 按 F5 运行")


if globals().get('__name__') == '__main__':
    main()