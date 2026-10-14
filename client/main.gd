extends Control

var api: GameApi

var i18n_traits: Dictionary = {}
var i18n_needs: Dictionary = {}
var i18n_templates: Dictionary = {}
var i18n_locations: Dictionary = {}
var i18n_reward_kinds: Dictionary = {}
var i18n_states: Dictionary = {}
var i18n_seasons: Dictionary = {}
var i18n_weathers: Dictionary = {}

# 顶层 UI
var status_label: RichTextLabel
var loading_label: Label
var player_tab_panel: VBoxContainer
var create_overlay: Control

# 左侧
var npc_list: ItemList

# 中间
var map_view: MapView
var npc_detail: RichTextLabel
var npc_items_label: RichTextLabel
var relationship_label: RichTextLabel
var dialogue_log: RichTextLabel
var dialogue_input: LineEdit

# 右侧
var event_log: RichTextLabel
var event_action_panel: VBoxContainer
var chronicle_log: RichTextLabel
var chronicle_title_input: LineEdit
var reward_log: RichTextLabel
var market_log: RichTextLabel
var quest_log: RichTextLabel
var faction_log: RichTextLabel
var craft_log: RichTextLabel
var all_recipes: Array = []
var goal_log: RichTextLabel
var market_buy_row: HBoxContainer
var item_list: ItemList
var item_detail: RichTextLabel
var use_btn: Button
var give_btn: Button
var take_btn: Button
var drop_btn: Button

# 顶部按钮
var trigger_btn: Button
var step_btn: Button
var step24_btn: Button
var refresh_btn: Button
var loading_timer: Timer
var loading_started_ms: int = 0
var loading_message: String = ""
var is_step_24_running: bool = false
var step_24_done: int = 0

# 数据
var current_npc_id: String = ""
var current_event_id: String = ""
var event_filter_tag: String = ""
var all_events_cache: Array = []
var event_filter_row: HBoxContainer
var pending_only: bool = false
var npc_data: Dictionary = {}
var npc_order: Array[String] = []
var pending_events_by_id: Dictionary = {}
var items: Array = []
var item_order: Array[String] = []
var current_item_id: String = ""
var npc_quests_panel: VBoxContainer
var npc_quests_data: Array = []
var equip_btn: Button
var equip_slot_labels: Dictionary = {}
var player_data: Dictionary = {}
var player_created: bool = false

# "我"面板的引用（用于刷新）
var player_stats_label: RichTextLabel
var player_attr_rows: Dictionary = {}   # attr_key -> {label: Label, btn: Button}
var player_name_label: Label
var explore_btn: Button
var explore_result_label: RichTextLabel
var action_result_label: RichTextLabel
var travel_option: OptionButton
var travel_btn: Button
var travel_result_label: RichTextLabel
var action_buttons_row: HBoxContainer

var map_poll_timer: Timer


func _ready() -> void:
	api = GameApi.new()
	add_child(api)
	_connect_signals()
	_build_ui()
	_ensure_action_ui()
	_build_goal_section()
	_build_travel_row()
	# 先拉玩家，再拉 i18n
	api.fetch_player()
	api.fetch_i18n()

	map_poll_timer = Timer.new()
	map_poll_timer.wait_time = 3.0
	map_poll_timer.autostart = true
	map_poll_timer.timeout.connect(func(): api.fetch_map())
	add_child(map_poll_timer)

	var npc_poll_timer := Timer.new()
	npc_poll_timer.wait_time = 6.0
	npc_poll_timer.autostart = true
	npc_poll_timer.timeout.connect(func():
		if player_created:
			api.fetch_npcs()
	)
	add_child(npc_poll_timer)


func _connect_signals() -> void:
	api.i18n_received.connect(_on_i18n_received)
	api.player_received.connect(_on_player_received)
	api.player_created.connect(_on_player_created)
	api.player_allocated.connect(_on_player_allocated)
	api.explore_done.connect(_on_explore_done)
	api.world_state_received.connect(_on_world_state)
	api.npc_list_received.connect(_on_npc_list)
	api.npc_detail_received.connect(_on_npc_detail)
	api.npc_items_received.connect(_on_npc_items)
	api.dialogue_received.connect(_on_dialogue)
	api.event_triggered.connect(_on_event_triggered)
	api.event_list_received.connect(_on_event_list)
	api.event_resolved.connect(_on_event_resolved)
	api.relationships_received.connect(_on_relationships)
	api.reward_list_received.connect(_on_reward_list)
	api.item_list_received.connect(_on_item_list)
	api.item_action_done.connect(_on_item_action_done)
	api.map_received.connect(_on_map_received)
	api.chronicle_list_received.connect(_on_chronicle_list)
	api.chronicle_generated.connect(_on_chronicle_generated)
	api.action_done.connect(_on_action_done)
	api.travel_done.connect(_on_travel_done)
	api.market_received.connect(_on_market_received)
	api.trade_done.connect(_on_trade_done)
	api.goals_received.connect(_on_goals_received)
	api.goal_claimed.connect(_on_goal_claimed)
	api.quest_list_received.connect(_on_quest_list_received)
	api.factions_received.connect(_on_factions_received)
	api.quest_abandoned.connect(_on_quest_abandoned)
	api.request_failed.connect(_on_request_failed)
	api.recipes_received.connect(_on_recipes_received)
	api.craft_done.connect(_on_craft_done)
	api.equip_done.connect(_on_equip_done)
	api.unequip_done.connect(_on_unequip_done)
	api.npc_quests_received.connect(_on_npc_quests_received)
	api.quest_accepted.connect(_on_quest_accepted)
	api.npc_active_quests_received.connect(_on_npc_active_quests_received)
	api.quest_turned_in.connect(_on_quest_turned_in)

func _safe_str(v) -> String:
	if v == null:
		return ""
	return str(v)


# ================================================================
# UI 构建
# ================================================================

func _make_small_tab_theme() -> Theme:
	var theme := Theme.new()
	theme.set_font_size("font_size", "TabBar", 12)
	return theme


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

	# 三栏分屏
	var split := HSplitContainer.new()
	split.size_flags_vertical = Control.SIZE_EXPAND_FILL
	split.add_theme_constant_override("separation", 8)
	root.add_child(split)

	# --- 左栏：我（只允许纵向滚动）---
	var left_scroll := ScrollContainer.new()
	left_scroll.custom_minimum_size = Vector2(340, 0)
	left_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	left_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	split.add_child(left_scroll)

	var left_panel := VBoxContainer.new()
	left_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left_panel.add_theme_constant_override("separation", 6)
	left_scroll.add_child(left_panel)
	_build_player_tab(left_panel)

	# --- 中栏：地图 / 人物 ---
	var mid_tabs := TabContainer.new()
	mid_tabs.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	mid_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	mid_tabs.add_theme_font_size_override("font_size", 12)
	mid_tabs.add_theme_stylebox_override("tab_selected", StyleBoxEmpty.new())
	split.add_child(mid_tabs)
	_build_map_tab(mid_tabs)
	_build_npc_tab(mid_tabs)

	# --- 右栏：事件 / 史册 / 奖励 / 物品 ---
	var right_tabs := TabContainer.new()
	right_tabs.custom_minimum_size = Vector2(440, 0)
	right_tabs.size_flags_horizontal = Control.SIZE_SHRINK_END
	right_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	right_tabs.add_theme_font_size_override("font_size", 11)
	split.add_child(right_tabs)
	_build_event_tab(right_tabs)
	_build_quest_tab(right_tabs)
	_build_faction_tab(right_tabs)
	_build_chronicle_tab(right_tabs)
	_build_market_tab(right_tabs)
	_build_reward_tab(right_tabs)
	_build_item_tab(right_tabs)
	_build_craft_tab(right_tabs)
	_ensure_explore_ui()


func _build_top_bar(root: VBoxContainer) -> void:
	var top := HBoxContainer.new()
	top.add_theme_constant_override("separation", 12)
	root.add_child(top)

	status_label = RichTextLabel.new()
	status_label.bbcode_enabled = true
	status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status_label.fit_content = false
	status_label.scroll_active = false
	status_label.text = "加载中..."
	status_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(status_label)

	loading_label = Label.new()
	loading_label.text = ""
	loading_label.add_theme_color_override("font_color", Color(1.0, 0.85, 0.3))
	top.add_child(loading_label)

	step_btn = Button.new()
	step_btn.text = "推进 1 回合"
	step_btn.pressed.connect(_on_step_once)
	top.add_child(step_btn)

	step24_btn = Button.new()
	step24_btn.text = "推进 24 回合"
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

	loading_timer = Timer.new()
	loading_timer.wait_time = 0.5
	loading_timer.autostart = false
	loading_timer.timeout.connect(_on_loading_tick)
	add_child(loading_timer)


# ---------------- 我（玩家） Tab ----------------

func _build_player_tab(parent: Container) -> void:
	player_tab_panel = VBoxContainer.new()
	player_tab_panel.add_theme_constant_override("separation", 8)
	parent.add_child(player_tab_panel)

	var title := Label.new()
	title.text = "[我]"
	title.add_theme_font_size_override("font_size", 18)
	player_tab_panel.add_child(title)

	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 12)
	player_tab_panel.add_child(header)

	player_name_label = Label.new()
	player_name_label.text = "加载中..."
	player_name_label.add_theme_font_size_override("font_size", 20)
	header.add_child(player_name_label)

	player_stats_label = RichTextLabel.new()
	player_stats_label.bbcode_enabled = true
	player_stats_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	player_stats_label.fit_content = true
	player_stats_label.custom_minimum_size = Vector2(0, 120)
	player_tab_panel.add_child(player_stats_label)

	var equip_title := Label.new()
	equip_title.text = "[装备槽]"
	equip_title.add_theme_font_size_override("font_size", 14)
	player_tab_panel.add_child(equip_title)

	# 三个槽位显示
	for slot_key in ["weapon", "armor", "accessory", "tool"]:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 6)

		var slot_lbl := Label.new()
		slot_lbl.custom_minimum_size = Vector2(60, 0)
		slot_lbl.text = {"weapon": "武器", "armor": "护甲", "accessory": "饰物", "tool": "工具"}.get(slot_key, slot_key)
		row.add_child(slot_lbl)

		var val_lbl := Label.new()
		val_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		val_lbl.text = "（空）"
		row.add_child(val_lbl)

		var un_btn := Button.new()
		un_btn.text = "卸下"
		un_btn.disabled = true
		var sk: String = str(slot_key)
		un_btn.pressed.connect(func(): _on_unequip_pressed(sk))
		row.add_child(un_btn)

		player_tab_panel.add_child(row)
		equip_slot_labels[slot_key] = {"label": val_lbl, "btn": un_btn}

	var attr_title := Label.new()
	attr_title.text = "属性（可分配点 [+] 可加到 20，行动自然成长上限 15）"
	player_tab_panel.add_child(attr_title)

	var attr_box := VBoxContainer.new()
	attr_box.add_theme_constant_override("separation", 4)
	player_tab_panel.add_child(attr_box)

	# 六个属性行：预创建，稍后填数值
	var attr_keys := ["strength", "agility", "intelligence", "perception", "charisma", "luck"]
	var attr_labels := ["力量", "敏捷", "智慧", "感知", "魅力", "运气"]
	var attr_desc := [
		"肉体对抗、搬运、战斗",
		"躲避、逃脱、潜行",
		"推理、查证、计谋",
		"观察、听风、发现线索",
		"说服、社交、调解",
		"巧合、意外之财、逃过一劫",
	]

	for i in range(attr_keys.size()):
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 8)

		var lbl := Label.new()
		lbl.text = attr_labels[i]
		lbl.custom_minimum_size = Vector2(60, 0)
		row.add_child(lbl)

		var val_lbl := Label.new()
		val_lbl.text = "-"
		val_lbl.custom_minimum_size = Vector2(40, 0)
		row.add_child(val_lbl)

		var desc_lbl := Label.new()
		desc_lbl.text = attr_desc[i]
		desc_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		desc_lbl.clip_text = true
		desc_lbl.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		desc_lbl.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
		row.add_child(desc_lbl)

		var btn := Button.new()
		btn.text = "+"
		btn.disabled = true
		btn.custom_minimum_size = Vector2(36, 0)
		var akey: String = str(attr_keys[i])
		btn.pressed.connect(func(): _on_attr_plus_pressed(akey))
		row.add_child(btn)

		attr_box.add_child(row)
		player_attr_rows[akey] = {"label": val_lbl, "btn": btn}


func _render_player_panel() -> void:
	if not player_created:
		player_name_label.text = "尚未创建角色"
		player_stats_label.text = "[i]点击下方按钮创建角色[/i]"
		for key in player_attr_rows.keys():
			var r: Dictionary = player_attr_rows[key]
			(r["label"] as Label).text = "-"
			(r["btn"] as Button).disabled = true
		return

	var name_s: String = str(player_data.get("name", "无名者"))
	var gender_s: String = str(player_data.get("gender", "unknown"))
	var gender_zh: String = {"male": "男", "female": "女"}.get(gender_s, "未知")
	var bg: String = str(player_data.get("background", ""))
	var level: int = int(player_data.get("level", 1))
	var exp: int = int(player_data.get("exp", 0))
	var exp_next: int = int(player_data.get("exp_next", 100))
	var unspent: int = int(player_data.get("unspent_points", 0))
	var rep: int = int(player_data.get("reputation", 0))
	var loc_id: String = str(player_data.get("location_id", "village_square"))
	var loc_label: String = _tr(i18n_locations, loc_id)

	player_name_label.text = "%s  %s  %d 岁" % [name_s, gender_zh, int(player_data.get("age", 22))]

	var lines: Array[String] = []
	if bg != "":
		lines.append("[b]出身：[/b]%s" % bg)
	lines.append("[b]等级：[/b]%d   [b]经验：[/b]%d / %d" % [level, exp, exp_next])
	var hp: int = int(player_data.get("hp", 100))
	var max_hp: int = int(player_data.get("max_hp", 100))
	var hp_color := "lightgreen"
	if max_hp > 0 and hp < max_hp * 0.3:
		hp_color = "red"
	elif max_hp > 0 and hp < max_hp * 0.7:
		hp_color = "yellow"
	lines.append("[b]生命：[/b][color=%s]%d / %d[/color]" % [hp_color, hp, max_hp])
	var money: int = int(player_data.get("money", 0))
	lines.append("[b]铜钱：[/b][color=gold]%d[/color]" % money)
	lines.append("[b]可分配点：[/b]%d" % unspent)
	lines.append("[b]声誉：[/b]%d" % rep)
	# 优先用 i18n 表，fallback 用硬编码
	if loc_label == loc_id or loc_label == "":
		var fallback := {
			"village_square": "村庄广场",
			"market": "市场",
			"tavern": "酒馆",
			"home": "住处",
			"forest": "森林",
			"village_edge": "村庄边缘",
			"village_hall": "村公所",
			"deep_forest": "深山老林",
			"old_mine": "废弃矿洞",
			"river_bend": "河湾",
			"old_shrine": "古庙遗址",
			"abandoned_farm": "荒废农舍",
			"mountain_pass": "山道",
		}
		loc_label = fallback.get(loc_id, loc_id)
	lines.append("[b]所在地：[/b]%s" % loc_label)
	player_stats_label.text = "\n".join(lines)

	# 属性显示用"基础 + 装备加成"
	var base_attrs: Dictionary = player_data.get("attributes", {})
	var total_attrs: Dictionary = player_data.get("total_attributes", base_attrs)
	for key in player_attr_rows.keys():
		var r: Dictionary = player_attr_rows[key]
		var v: int = int(base_attrs.get(key, 5))
		var tv: int = int(total_attrs.get(key, v))
		if tv != v:
			(r["label"] as Label).text = "%d [color=gold](%d)[/color]" % [v, tv]
		else:
			(r["label"] as Label).text = str(v)
		(r["btn"] as Button).disabled = unspent <= 0 or v >= 20

	# 装备槽
	var eq_slots: Array = player_data.get("equipment_slots", [])
	for slot_data in eq_slots:
		if not slot_data is Dictionary:
			continue
		var sk: String = str(slot_data.get("slot", ""))
		if not equip_slot_labels.has(sk):
			continue
		var rec: Dictionary = equip_slot_labels[sk]
		var nm: String = str(slot_data.get("item_name", "（空）"))
		var item_id: String = str(slot_data.get("item_id", ""))
		if nm == "" or nm == "（空）":
			(rec["label"] as Label).text = "（空）"
			(rec["btn"] as Button).disabled = true
		else:
			var attrs_dict: Dictionary = slot_data.get("attributes", {})
			var attr_strs: Array[String] = []
			for k in attrs_dict.keys():
				var k_zh: String = {
					"strength": "力量", "agility": "敏捷", "intelligence": "智慧",
					"perception": "感知", "charisma": "魅力", "luck": "运气",
				}.get(str(k), str(k))
				attr_strs.append("%s+%d" % [k_zh, int(attrs_dict[k])])
			(rec["label"] as Label).text = "%s  %s" % [nm, " ".join(attr_strs)]
			(rec["btn"] as Button).disabled = false
	_refresh_travel_options()


func _on_attr_plus_pressed(attribute: String) -> void:
	if not player_created:
		return
	api.allocate_point(attribute, 1)


# ---------------- 世界 Tab（地图 / 档案 / 编年史 / 史册 / 奖励 / 物品） ----------------

func _build_map_tab(parent: TabContainer) -> void:
	map_view = MapView.new()
	map_view.name = "地图"
	map_view.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	map_view.size_flags_vertical = Control.SIZE_EXPAND_FILL
	map_view.npc_clicked.connect(_on_map_npc_clicked)
	map_view.location_clicked.connect(_on_map_location_clicked)
	parent.add_child(map_view)


func _build_npc_tab(parent: TabContainer) -> void:
	var panel := HSplitContainer.new()
	panel.name = "人物"
	panel.add_theme_constant_override("separation", 8)
	parent.add_child(panel)

	# 左：NPC 列表
	var left := VBoxContainer.new()
	left.custom_minimum_size = Vector2(220, 0)
	left.add_theme_constant_override("separation", 6)
	panel.add_child(left)

	var title := Label.new()
	title.text = "居民"
	left.add_child(title)

	npc_list = ItemList.new()
	npc_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	npc_list.item_selected.connect(_on_npc_selected)
	left.add_child(npc_list)

	# 右：NPC 详情 + 对话
	var right := VBoxContainer.new()
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	right.add_theme_constant_override("separation", 6)
	panel.add_child(right)

	var detail_scroll := ScrollContainer.new()
	detail_scroll.custom_minimum_size = Vector2(0, 180)
	detail_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	right.add_child(detail_scroll)

	npc_detail = RichTextLabel.new()
	npc_detail.bbcode_enabled = true
	npc_detail.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	npc_detail.fit_content = true
	npc_detail.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	npc_detail.text = "从左侧选择一位居民"
	detail_scroll.add_child(npc_detail)

	npc_items_label = RichTextLabel.new()
	npc_items_label.bbcode_enabled = true
	npc_items_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	npc_items_label.fit_content = true
	npc_items_label.custom_minimum_size = Vector2(0, 60)
	right.add_child(npc_items_label)

	relationship_label = RichTextLabel.new()
	relationship_label.bbcode_enabled = true
	relationship_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	relationship_label.fit_content = true
	relationship_label.custom_minimum_size = Vector2(0, 60)
	right.add_child(relationship_label)

	# NPC 委托任务面板
	npc_quests_panel = VBoxContainer.new()
	npc_quests_panel.add_theme_constant_override("separation", 4)
	npc_quests_panel.name = "QuestOfferPanel"
	right.add_child(npc_quests_panel)

	var dlg_title := Label.new()
	dlg_title.text = "对话"
	right.add_child(dlg_title)

	var dlg_scroll := ScrollContainer.new()
	dlg_scroll.custom_minimum_size = Vector2(0, 120)
	dlg_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	right.add_child(dlg_scroll)

	dialogue_log = RichTextLabel.new()
	dialogue_log.bbcode_enabled = true
	dialogue_log.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	dialogue_log.fit_content = true
	dialogue_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	dlg_scroll.add_child(dialogue_log)

	var dlg_row := HBoxContainer.new()
	dlg_row.add_theme_constant_override("separation", 6)
	right.add_child(dlg_row)

	dialogue_input = LineEdit.new()
	dialogue_input.placeholder_text = "说点什么..."
	dialogue_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	dialogue_input.text_submitted.connect(_on_dialogue_submit)
	dlg_row.add_child(dialogue_input)

	var send_btn := Button.new()
	send_btn.text = "发送"
	send_btn.pressed.connect(func(): _on_dialogue_submit(dialogue_input.text))
	dlg_row.add_child(send_btn)


func _build_event_tab(parent: TabContainer) -> void:
	var ev_tab := VBoxContainer.new()
	ev_tab.name = "事件"
	ev_tab.add_theme_constant_override("separation", 6)
	parent.add_child(ev_tab)

	var ev_scroll := ScrollContainer.new()
	ev_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	ev_tab.add_child(ev_scroll)

	event_log = RichTextLabel.new()
	event_log.bbcode_enabled = true
	event_log.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	event_log.fit_content = true
	event_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	event_log.meta_clicked.connect(_on_event_meta_clicked)
	ev_scroll.add_child(event_log)

	event_filter_row = HBoxContainer.new()
	event_filter_row.add_theme_constant_override("separation", 4)
	ev_tab.add_child(event_filter_row)

	var filters := [
		["", "全部"],
		["__pending__", "待处理"],
		["conflict", "冲突"],
		["social", "社交"],
		["daily", "日常"],
		["mystery", "悬疑"],
		["action", "我的行动"],
	]
	for pair in filters:
		var b := Button.new()
		b.text = str(pair[1])
		var tag: String = str(pair[0])
		b.pressed.connect(func(): _set_event_filter(tag))
		event_filter_row.add_child(b)

	event_action_panel = VBoxContainer.new()
	event_action_panel.add_theme_constant_override("separation", 4)
	ev_tab.add_child(event_action_panel)


func _build_chronicle_tab(parent: TabContainer) -> void:
	var chr_tab := VBoxContainer.new()
	chr_tab.name = "史册"
	chr_tab.add_theme_constant_override("separation", 6)
	parent.add_child(chr_tab)

	var chr_scroll := ScrollContainer.new()
	chr_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	chr_tab.add_child(chr_scroll)

	chronicle_log = RichTextLabel.new()
	chronicle_log.bbcode_enabled = true
	chronicle_log.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	chronicle_log.fit_content = true
	chronicle_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	chr_scroll.add_child(chronicle_log)

	var ctrl := HBoxContainer.new()
	ctrl.add_theme_constant_override("separation", 6)
	chr_tab.add_child(ctrl)

	chronicle_title_input = LineEdit.new()
	chronicle_title_input.placeholder_text = "标题（可空）"
	chronicle_title_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ctrl.add_child(chronicle_title_input)

	var chr_btn := Button.new()
	chr_btn.text = "生成史册"
	chr_btn.pressed.connect(_on_generate_chronicle)
	ctrl.add_child(chr_btn)


func _build_reward_tab(parent: TabContainer) -> void:
	var rwd_scroll := ScrollContainer.new()
	rwd_scroll.name = "奖励"
	parent.add_child(rwd_scroll)
	reward_log = RichTextLabel.new()
	reward_log.bbcode_enabled = true
	reward_log.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	reward_log.fit_content = true
	reward_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rwd_scroll.add_child(reward_log)


func _build_item_tab(parent: TabContainer) -> void:
	var item_tab := VBoxContainer.new()
	item_tab.name = "物品"
	item_tab.add_theme_constant_override("separation", 6)
	parent.add_child(item_tab)

	item_list = ItemList.new()
	item_list.custom_minimum_size = Vector2(0, 200)
	item_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	item_list.item_selected.connect(_on_item_selected)
	item_tab.add_child(item_list)

	var detail_scroll := ScrollContainer.new()
	detail_scroll.custom_minimum_size = Vector2(0, 140)
	item_tab.add_child(detail_scroll)

	item_detail = RichTextLabel.new()
	item_detail.bbcode_enabled = true
	item_detail.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	item_detail.fit_content = true
	item_detail.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	item_detail.text = "选中一件物品查看详情"
	detail_scroll.add_child(item_detail)

	var item_buttons := HBoxContainer.new()
	item_buttons.add_theme_constant_override("separation", 6)
	item_tab.add_child(item_buttons)

	use_btn = Button.new()
	use_btn.text = "使用"
	use_btn.pressed.connect(_on_use_pressed)
	item_buttons.add_child(use_btn)

	equip_btn = Button.new()
	equip_btn.text = "装备"
	equip_btn.pressed.connect(_on_equip_pressed)
	item_buttons.add_child(equip_btn)

	give_btn = Button.new()
	give_btn.text = "给予"
	give_btn.pressed.connect(_on_give_pressed)
	item_buttons.add_child(give_btn)

	take_btn = Button.new()
	take_btn.text = "拿回"
	take_btn.pressed.connect(_on_take_pressed)
	item_buttons.add_child(take_btn)

	drop_btn = Button.new()
	drop_btn.text = "丢弃"
	drop_btn.pressed.connect(_on_drop_pressed)
	item_buttons.add_child(drop_btn)

	_set_item_buttons_enabled(false)


func _set_item_buttons_enabled(enabled: bool) -> void:
	if not enabled:
		use_btn.disabled = true
		give_btn.disabled = true
		take_btn.disabled = true
		drop_btn.disabled = true


# ================================================================
# 创建角色弹窗
# ================================================================

func _show_create_dialog() -> void:
	if create_overlay != null and is_instance_valid(create_overlay):
		return

	create_overlay = Control.new()
	create_overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	create_overlay.mouse_filter = Control.MOUSE_FILTER_STOP

	# 半透明遮罩
	var bg := ColorRect.new()
	bg.color = Color(0, 0, 0, 0.75)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	create_overlay.add_child(bg)

	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	create_overlay.add_child(center)

	var panel := PanelContainer.new()
	panel.custom_minimum_size = Vector2(420, 0)
	center.add_child(panel)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 12)
	vbox.add_theme_constant_override("margin_left", 20)
	vbox.add_theme_constant_override("margin_right", 20)
	vbox.add_theme_constant_override("margin_top", 20)
	vbox.add_theme_constant_override("margin_bottom", 20)
	panel.add_child(vbox)

	var title := Label.new()
	title.text = "你是谁？"
	title.add_theme_font_size_override("font_size", 22)
	vbox.add_child(title)

	var desc := Label.new()
	desc.text = "你刚来到这个偏远的村庄。\n在决定留下之前，先想清楚自己从哪来、叫什么。"
	desc.add_theme_color_override("font_color", Color(0.75, 0.75, 0.75))
	vbox.add_child(desc)

	# 姓名
	var name_row := HBoxContainer.new()
	name_row.add_theme_constant_override("separation", 8)
	vbox.add_child(name_row)

	var name_lbl := Label.new()
	name_lbl.text = "姓名"
	name_lbl.custom_minimum_size = Vector2(60, 0)
	name_row.add_child(name_lbl)

	var name_input := LineEdit.new()
	name_input.placeholder_text = "输入你的名字"
	name_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	name_row.add_child(name_input)

	# 性别
	var gender_row := HBoxContainer.new()
	gender_row.add_theme_constant_override("separation", 8)
	vbox.add_child(gender_row)

	var gender_lbl := Label.new()
	gender_lbl.text = "性别"
	gender_lbl.custom_minimum_size = Vector2(60, 0)
	gender_row.add_child(gender_lbl)

	var gender_opt := OptionButton.new()
	gender_opt.add_item("男")
	gender_opt.set_item_metadata(0, "male")
	gender_opt.add_item("女")
	gender_opt.set_item_metadata(1, "female")
	gender_opt.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	gender_row.add_child(gender_opt)

	# 出身
	var bg_row := HBoxContainer.new()
	bg_row.add_theme_constant_override("separation", 8)
	vbox.add_child(bg_row)

	var bg_lbl := Label.new()
	bg_lbl.text = "出身"
	bg_lbl.custom_minimum_size = Vector2(60, 0)
	bg_row.add_child(bg_lbl)

	var bg_opt := OptionButton.new()
	var bgs := [
		"游历的行商",
		"山里来的猎户",
		"读书人",
		"流浪艺人",
		"逃荒的农夫",
		"不明来历",
	]
	for i in range(bgs.size()):
		bg_opt.add_item(bgs[i])
		bg_opt.set_item_metadata(i, bgs[i])
	bg_opt.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bg_row.add_child(bg_opt)

	var bg_hint := Label.new()
	bg_hint.text = "不同的出身会略微影响初始属性"
	bg_hint.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
	bg_hint.add_theme_font_size_override("font_size", 12)
	vbox.add_child(bg_hint)

	# 按钮
	var btn_row := HBoxContainer.new()
	btn_row.add_theme_constant_override("separation", 8)
	btn_row.alignment = BoxContainer.ALIGNMENT_END
	vbox.add_child(btn_row)

	var ok_btn := Button.new()
	ok_btn.text = "踏入村庄"
	ok_btn.pressed.connect(func():
		var nm := name_input.text.strip_edges()
		if nm == "":
			name_input.placeholder_text = "（名字不能为空）"
			return
		var gender: String = str(gender_opt.get_item_metadata(gender_opt.selected))
		var background: String = str(bg_opt.get_item_metadata(bg_opt.selected))
		_set_loading("正在创建角色...")
		api.create_player(nm, gender, background)
	)
	btn_row.add_child(ok_btn)

	add_child(create_overlay)
	name_input.grab_focus()


func _close_create_dialog() -> void:
	if create_overlay != null and is_instance_valid(create_overlay):
		create_overlay.queue_free()
		create_overlay = null


# ================================================================
# 玩家信号
# ================================================================

func _on_player_received(data: Dictionary) -> void:
	player_created = bool(data.get("created", false))
	player_data = data
	_render_player_panel()
	if not player_created:
		_show_create_dialog()


func _on_player_created(data: Dictionary) -> void:
	_set_loading("")
	player_data = data
	player_created = true
	_render_player_panel()
	_close_create_dialog()
	_refresh_all()


func _on_player_allocated(data: Dictionary) -> void:
	player_data = data
	_render_player_panel()


# ================================================================
# loading
# ================================================================

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

	# 兜底：超过 90 秒强制清除
	if elapsed > 90.0:
		print("[ui] loading 超过 90 秒，强制清除")
		is_step_24_running = false
		step_24_done = 0
		_set_loading("")
		status_label.text = "[color=red]请求超时（90s），请再试一次[/color]"


func _on_step_once() -> void:
	_set_loading("正在推进...")
	api.step_world()


func _on_trigger_event() -> void:
	_set_loading("正在生成事件（调用 LLM，请稍候）...")
	api.trigger_event()


func _on_step_24() -> void:
	is_step_24_running = true
	step_24_done = 0
	step24_btn.disabled = true
	_set_loading("推进 24 回合 (0/24)")
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
	_step_24_recursive(remaining - 1)


func _refresh_all() -> void:
	if not player_created:
		return
	api.fetch_world_state()
	api.fetch_npcs()
	api.fetch_events(50)
	api.fetch_rewards(20)
	api.fetch_items(100)
	api.fetch_map()
	api.fetch_chronicles(10)
	api.fetch_goals()
	api.fetch_quests()
	api.fetch_factions()
	api.fetch_recipes()

func _on_i18n_received(data: Dictionary) -> void:
	i18n_traits = data.get("traits", {})
	i18n_needs = data.get("needs", {})
	i18n_templates = data.get("templates", {})
	i18n_locations = data.get("locations", {})
	i18n_reward_kinds = data.get("reward_kinds", {})
	i18n_states = data.get("states", {})
	i18n_seasons = data.get("seasons", {})
	i18n_weathers = data.get("weathers", {})
	if player_created:
		_refresh_all()


func _tr(dict: Dictionary, key: String) -> String:
	if dict.has(key):
		return str(dict[key])
	return key


# ================================================================
# 世界状态 / 地图 / NPC
# ================================================================

func _on_world_state(data: Dictionary) -> void:
	var season_zh: String = str(data.get("season_label", ""))
	var weather_zh: String = str(data.get("weather_label", ""))
	status_label.text = "第 %d 天  %02d:00   %s · %s   第 %d 回合   张力 %.2f" % [
		int(data.get("day", 0)),
		int(data.get("hour", 0)),
		season_zh, weather_zh,
		int(data.get("tick", 0)),
		float(data.get("tension", 0.0)),
	]


func _on_map_received(data: Dictionary) -> void:
	if map_view:
		map_view.set_data(data)
		map_view.set_selected(current_npc_id)


func _on_map_npc_clicked(npc_id: String) -> void:
	for i in range(npc_order.size()):
		if npc_order[i] == npc_id:
			npc_list.select(i)
			_on_npc_selected(i)
			break


func _on_npc_list(data: Array) -> void:
	npc_data.clear()
	npc_order.clear()
	npc_list.clear()
	for npc in data:
		if not npc is Dictionary:
			continue
		var id: String = str(npc.get("id", ""))
		var name: String = str(npc.get("name", "?"))
		var gz: String = str(npc.get("gender_label", ""))
		var loc: String = str(npc.get("location_label", ""))
		npc_data[id] = npc
		npc_order.append(id)
		npc_list.add_item("%s %s @ %s" % [name, gz, loc])


func _on_npc_selected(index: int) -> void:
	if index < 0 or index >= npc_order.size():
		return
	current_npc_id = npc_order[index]
	api.fetch_npc_detail(current_npc_id)
	api.fetch_relationships(current_npc_id)
	api.fetch_npc_items(current_npc_id)
	api.fetch_npc_quests(current_npc_id)
	if map_view:
		map_view.set_selected(current_npc_id)
	var name: String = str(npc_data[current_npc_id].get("name", "?"))
	dialogue_log.text = "[i]你走近 %s...[/i]" % name


func _on_npc_detail(data: Dictionary) -> void:
	var lines: Array[String] = []
	var gender_zh: String = str(data.get("gender_label", "未知"))
	lines.append("[b][color=yellow]%s[/color][/b]   %s   %d 岁" % [
		str(data.get("name", "?")), gender_zh, int(data.get("age", 0)),
	])
	lines.append("所在地：%s" % str(data.get("location_label", "")))
	var fac_label: String = str(data.get("faction_label", ""))
	if fac_label != "" and fac_label != "中立":
		lines.append("所属派系：[color=gold]%s[/color]" % fac_label)
	lines.append("")
	lines.append("[b]性格[/b]")
	for t2 in data.get("traits", []):
		if t2 is Dictionary:
			lines.append("   %s：%.2f" % [str(t2.get("label", "?")), float(t2.get("value", 0))])
	lines.append("")
	lines.append("[b]需求[/b]")
	for n in data.get("needs", []):
		if n is Dictionary:
			lines.append("   %s：%.2f" % [str(n.get("label", "?")), float(n.get("value", 0))])
	lines.append("")
	lines.append("[b]目标[/b]")
	for g in data.get("goals", []):
		lines.append("   · %s" % str(g))

	# 对你的印象（放在目标之后，家庭之前）
	var impr: Array = data.get("impressions", [])
	if not impr.is_empty():
		lines.append("")
		lines.append("[b][color=cyan]对你的印象[/color][/b]")
		for s in impr:
			lines.append("   · %s" % str(s))

	# 日程
	var sched: Array = data.get("schedule", [])
	if not sched.is_empty():
		lines.append("")
		lines.append("[b]日常作息[/b]")
		for s in sched:
			lines.append("   %s" % str(s))

	# 家庭
	var fam: Dictionary = data.get("family", {})
	if fam is Dictionary:
		var fam_lines: Array[String] = []
		if str(fam.get("spouse_name", "")) != "":
			fam_lines.append("   配偶：%s" % str(fam["spouse_name"]))
		var ch_arr = fam.get("children_names", [])
		if ch_arr != null and ch_arr.size() > 0:
			var ch_names: Array[String] = []
			for c in ch_arr:
				ch_names.append(str(c))
			fam_lines.append("   子女：%s" % "、".join(ch_names))
		var pa_arr = fam.get("parents_names", [])
		if pa_arr != null and pa_arr.size() > 0:
			var pa_names: Array[String] = []
			for c in pa_arr:
				pa_names.append(str(c))
			fam_lines.append("   父母：%s" % "、".join(pa_names))
		var si_arr = fam.get("siblings_names", [])
		if si_arr != null and si_arr.size() > 0:
			var si_names: Array[String] = []
			for c in si_arr:
				si_names.append(str(c))
			fam_lines.append("   兄弟姐妹：%s" % "、".join(si_names))
		if not fam_lines.is_empty():
			lines.append("")
			lines.append("[b]家庭[/b]")
			for fl in fam_lines:
				lines.append(fl)

	npc_detail.text = "\n".join(lines)
func _on_npc_items(data: Array) -> void:
	if data.is_empty():
		npc_items_label.text = "[b]持有物[/b]\n   （空）"
		return
	var lines: Array[String] = ["[b]持有物[/b]"]
	for it in data:
		if it is Dictionary:
			lines.append("   · %s（%s）" % [
				str(it.get("name", "?")), str(it.get("kind", "")),
			])
	npc_items_label.text = "\n".join(lines)


func _on_relationships(data: Array) -> void:
	if data.is_empty():
		relationship_label.text = "[b]关系[/b]\n   （暂无）"
		return
	var lines: Array[String] = ["[b]关系[/b]"]
	for r in data:
		if not r is Dictionary:
			continue
		lines.append("   %s  信任 %+.2f  好感 %+.2f" % [
			str(r.get("other_name", "?")),
			float(r.get("trust", 0)),
			float(r.get("affection", 0)),
		])
	relationship_label.text = "\n".join(lines)


func _on_dialogue_submit(text: String) -> void:
	text = text.strip_edges()
	if text == "" or current_npc_id == "":
		return
	dialogue_log.append_text("\n[b]你：[/b]%s" % text)
	dialogue_input.text = ""
	api.send_dialogue(current_npc_id, text)


func _on_dialogue(data: Dictionary) -> void:
	var name: String = str(data.get("npc_name", "NPC"))
	var reply: String = str(data.get("reply", ""))
	dialogue_log.append_text("\n[b][color=cyan]%s：[/color][/b]%s\n" % [name, reply])


# ================================================================
# 事件
# ================================================================

func _on_event_triggered(data: Dictionary) -> void:
	if is_step_24_running:
		step_24_done += 1
		_set_loading("推进 24 回合 (%d/24)" % step_24_done)
	else:
		_set_loading("")

	var new_event_id: String = str(data.get("event", ""))
	var tpl_label: String = str(data.get("template_label", ""))
	var summary: String = str(data.get("event_summary", ""))
	var awaiting: bool = bool(data.get("awaiting_player", false))

	# 先给用户一个明确的"刚刚发生了什么"提示
	if new_event_id != "" and summary != "":
		var marker := "☆ 新事件"
		if awaiting:
			marker = "★ 等你决定"
		status_label.text = "[color=orange]%s：%s[/color]" % [marker, tpl_label]

	if data.has("social_dialogue") and data.get("social_dialogue") != null:
		var sd = data.get("social_dialogue")
		if sd is Dictionary:
			_render_social(sd)

	api.fetch_events(50)
	api.fetch_rewards(20)
	api.fetch_items(100)
	api.fetch_map()
	api.fetch_world_state()
	api.fetch_npcs()
	if current_npc_id != "":
		api.fetch_npc_items(current_npc_id)


func _render_social(sd: Dictionary) -> void:
	var a_name := str(sd.get("a_name", "?"))
	var b_name := str(sd.get("b_name", "?"))
	var loc := str(sd.get("location_label", ""))
	var lines: Array = sd.get("lines", [])

	event_log.append_text("\n[color=cyan]·[/color] [b]闲谈[/b]（%s，%s，%s）\n" % [
		a_name, b_name, loc,
	])
	for line in lines:
		if line is Dictionary:
			event_log.append_text("    [b]%s[/b]：%s\n" % [
				str(line.get("speaker", "")), str(line.get("text", "")),
			])
	event_log.append_text("\n")


func _on_event_list(data: Array) -> void:
	all_events_cache = data
	_render_event_list()


func _set_event_filter(tag: String) -> void:
	event_filter_tag = tag
	_render_event_list()


func _event_matches_filter(e: Dictionary) -> bool:
	if event_filter_tag == "":
		return true
	if event_filter_tag == "__pending__":
		return bool(e.get("awaiting_player", false))
	var tags: Array = e.get("tags", [])
	return tags.has(event_filter_tag)


func _render_event_list() -> void:
	event_log.clear()
	pending_events_by_id.clear()

	var awaiting: Array = []
	var world_events: Array = []
	var player_actions: Array = []

	for e in all_events_cache:
		if not e is Dictionary:
			continue
		if bool(e.get("awaiting_player", false)):
			pending_events_by_id[str(e.get("id", ""))] = e

		if not _event_matches_filter(e):
			continue

		if bool(e.get("awaiting_player", false)):
			awaiting.append(e)
			continue

		# 检查是否玩家的行动
		var tags: Array = e.get("tags", [])
		var is_action: bool = tags.has("action")
		var payload = e.get("payload", {})
		if payload is Dictionary and bool(payload.get("is_player_action", false)):
			is_action = true

		if is_action:
			player_actions.append(e)
		else:
			world_events.append(e)

	# 1. 待处理
	if not awaiting.is_empty():
		event_log.append_text("[b][color=orange]=== 等待你的决定 ===[/color][/b]\n\n")
		for e in awaiting:
			_render_event_entry(e, true)
		event_log.append_text("\n")

	# 2. 世界事件
	if not world_events.is_empty():
		event_log.append_text("[b]—— 世界事件 ——[/b]\n\n")
		for e in world_events:
			_render_event_entry(e, false)
		event_log.append_text("\n")

	# 3. 玩家行动（折叠到最下面）
	if not player_actions.is_empty():
		event_log.append_text("[b][color=gray]—— 我的行动 ——[/color][/b]\n\n")
		for e in player_actions:
			_render_event_entry(e, false)

	_refresh_event_action_panel()
func _render_event_entry(e: Dictionary, pending: bool) -> void:
	var eid: String = _safe_str(e.get("id", ""))
	var is_action := false
	var p2 = e.get("payload", {})
	if p2 is Dictionary and bool(p2.get("is_player_action", false)):
		is_action = true
	var state: String = str(e.get("state", ""))
	var state_zh: String = str(e.get("state_label", state))
	var created_at: int = int(e.get("created_at", 0))
	var eid_short: String = eid
	if eid.length() > 10:
		eid_short = eid.substr(eid.length() - 6)
	var as_message: bool = bool(e.get("as_message", false))

	var tpl_label: String = _safe_str(e.get("template_label", e.get("template_id", "?")))
	var loc_label: String = _safe_str(e.get("location_label", ""))
	var names_arr: Array = e.get("participant_names", [])
	var names_str := ""
	if not names_arr.is_empty():
		var ns: Array[String] = []
		for n in names_arr:
			var nname := _safe_str(n)
			ns.append(_color_name(nname))
		names_str = "（" + "、".join(ns) + "）"

	var summary: String = _highlight_names(_safe_str(e.get("summary", "")))
	var narrative: String = _highlight_names(_safe_str(e.get("narrative", "")))
	var outcome: String = _safe_str(e.get("outcome", ""))
	var choice_label: String = _safe_str(e.get("choice_label", ""))
	var check = e.get("check", {})
	var exp_gain: int = int(e.get("exp_gain", 0))
	var rep_gain: int = int(e.get("rep_gain", 0))

	if pending:
		event_log.append_text("[color=orange]·[/color] [color=gray][第 %d 回合][/color] [url=%s][b]%s[/b] %s（%s，%s）[/url]\n" % [
			created_at, eid, tpl_label, names_str, loc_label, state_zh,
		])
		if narrative != "":
			event_log.append_text("    [i]%s[/i]\n" % narrative)
		event_log.append_text("    [color=orange]点此做出选择[/color]\n\n")
	else:
		var color := "white"
		if state == "resolved":
			color = "lightgreen" if not as_message else "gray"
		elif state == "expired":
			color = "darkgray"
		elif state == "rejected":
			color = "dimgray"

		event_log.append_text("[color=%s]·[/color] [color=gray][第 %d 回合 #%s][/color] [b]%s[/b] %s（%s，%s）\n" % [
			color, created_at, eid_short, tpl_label, names_str, loc_label, state_zh,
		])
		if summary != "":
			event_log.append_text("    %s\n" % summary)
		if choice_label != "" and choice_label != "<null>":
			event_log.append_text("    [i]你的选择：%s[/i]\n" % choice_label)

		# 骰子判定展示
		if check is Dictionary and check.has("result"):
			var result_zh: String = {
				"critical": "大成功",
				"success": "成功",
				"partial": "勉强",
				"failure": "失败",
			}.get(str(check.get("result", "")), "")
			event_log.append_text(
				"    [color=cyan]%s %d + 骰 %d = %d vs 难度 %d → [b]%s[/b][/color]\n" % [
					_attr_label_from_dict(check),
					int(check.get("base", 0)),
					int(check.get("roll", 0)),
					int(check.get("total", 0)),
					int(check.get("threshold", 0)),
					result_zh,
				])

		if outcome != "" and outcome != "<null>":
			event_log.append_text("    [color=lightgreen]%s[/color]\n" % outcome)

		if exp_gain > 0 or rep_gain != 0:
			var bits: Array[String] = []
			if exp_gain > 0:
				bits.append("经验 +%d" % exp_gain)
			if rep_gain > 0:
				bits.append("声誉 +%d" % rep_gain)
			elif rep_gain < 0:
				bits.append("声誉 %d" % rep_gain)
			event_log.append_text("    [color=yellow]%s[/color]\n" % "，".join(bits))

		event_log.append_text("\n")


func _attr_label_from_dict(check: Dictionary) -> String:
	var key := str(check.get("attribute", ""))
	var map := {
		"strength": "力量", "agility": "敏捷", "intelligence": "智慧",
		"perception": "感知", "charisma": "魅力", "luck": "运气",
	}
	return map.get(key, key)


func _on_event_meta_clicked(meta) -> void:
	var eid := str(meta)
	if eid == "" or not pending_events_by_id.has(eid):
		return
	current_event_id = eid
	_refresh_event_action_panel()


func _refresh_event_action_panel() -> void:
	if event_action_panel == null:
		return
	for child in event_action_panel.get_children():
		child.queue_free()

	if current_event_id == "" or not pending_events_by_id.has(current_event_id):
		var hint := Label.new()
		hint.text = "（点击上方橙色事件做出选择）"
		hint.add_theme_font_size_override("font_size", 12)
		event_action_panel.add_child(hint)
		return

	var e: Dictionary = pending_events_by_id[current_event_id]
	print("[ui] 事件 %s 的 choices = %s" % [
		current_event_id,
		JSON.stringify(e.get("choices", [])),
	])
	var title := Label.new()
	title.text = "你打算怎么做？ —— %s" % str(e.get("template_label", ""))
	event_action_panel.add_child(title)

	var choices: Array = e.get("choices", [])
	if choices.is_empty():
		var hint := Label.new()
		hint.text = "（此事件没有选项，稍后会自动结算）"
		event_action_panel.add_child(hint)
		return

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	event_action_panel.add_child(row)

	for c in choices:
		if not c is Dictionary:
			continue
		var lbl := str(c.get("label", "?"))
		var attr_label := str(c.get("attribute_label", ""))
		var btn := Button.new()
		if attr_label != "":
			btn.text = "%s（%s）" % [lbl, attr_label]
		else:
			btn.text = lbl
		var cid := str(c.get("id", ""))
		var eid := current_event_id
		btn.pressed.connect(func(): _on_event_choice_pressed(eid, cid))
		row.add_child(btn)


func _on_event_choice_pressed(event_id: String, choice_id: String) -> void:
	print("[ui] 用户点击选项：event_id=[%s] choice_id=[%s]" % [event_id, choice_id])
	if event_id == "" or choice_id == "":
		print("[ui] 参数为空，忽略")
		return
	_set_loading("正在结算（调用 LLM）...")
	for child in event_action_panel.get_children():
		_disable_recursive(child)
	api.resolve_event(event_id, choice_id)


func _disable_recursive(node: Node) -> void:
	if node is Button:
		(node as Button).disabled = true
	for child in node.get_children():
		_disable_recursive(child)


func _on_event_resolved(data: Dictionary) -> void:
	_set_loading("")
	current_event_id = ""
	# 显示升级提示
	if bool(data.get("leveled_up", false)):
		var new_level: int = int(data.get("new_level", 1))
		status_label.text = "[color=gold]★ 升级！你现在是 %d 级[/color]" % new_level
	_refresh_all()
	# 重新拉玩家面板（升级后属性可能有变化）
	api.fetch_player()


# ================================================================
# 奖励 / 物品
# ================================================================

func _on_reward_list(data: Array) -> void:
	reward_log.clear()
	if data.is_empty():
		reward_log.text = "[i]还没有奖励[/i]"
		return

	# 按 kind 分组
	var groups: Dictionary = {}
	var kind_order: Array = []
	for r in data:
		if not r is Dictionary:
			continue
		var k: String = str(r.get("kind", "item"))
		if not groups.has(k):
			groups[k] = []
			kind_order.append(k)
		groups[k].append(r)

	var color_map := {
		"item": "#d8a850",
		"relationship": "#6ac070",
		"info": "#5aa8d8",
		"reputation": "#c870c8",
		"skill": "#e0a060",
		"story": "#a080d0",
	}

	for k in kind_order:
		var color: String = str(color_map.get(k, "#cccccc"))
		var label: String = str({
			"item": "物品",
			"relationship": "关系",
			"info": "情报",
			"reputation": "声望",
			"skill": "技能",
			"story": "剧情",
		}.get(k, k))
		reward_log.append_text("[b][color=%s]◆ %s[/color][/b]\n" % [color, label])
		for r in groups[k]:
			var v: float = float(r.get("value", 0))
			var desc: String = _safe_str(r.get("description", ""))
			reward_log.append_text("    %.2f  %s\n" % [v, _highlight_names(desc)])
		reward_log.append_text("\n")


func _on_item_list(data: Array) -> void:
	items = data
	item_order.clear()
	item_list.clear()
	for it in data:
		if not it is Dictionary:
			continue
		var id: String = str(it.get("id", ""))
		var name: String = str(it.get("name", "?"))
		var kind: String = str(it.get("kind", ""))
		var owner_label: String = str(it.get("owner_label", ""))
		item_order.append(id)
		item_list.add_item("%s (%s) —— %s" % [name, kind, owner_label])
	if current_item_id != "":
		for i in range(item_order.size()):
			if item_order[i] == current_item_id:
				item_list.select(i)
				_render_item_detail(current_item_id)
				break


func _on_item_selected(index: int) -> void:
	if index < 0 or index >= item_order.size():
		return
	current_item_id = item_order[index]
	_render_item_detail(current_item_id)


func _render_item_detail(item_id: String) -> void:
	for it in items:
		if str(it.get("id", "")) != item_id:
			continue
		var name: String = str(it.get("name", "?"))
		var kind: String = str(it.get("kind", ""))
		var affixes: Array = it.get("affixes", [])
		var story: String = str(it.get("story", ""))
		var value: float = float(it.get("value", 0))
		var owner_label: String = str(it.get("owner_label", ""))

		var lines: Array[String] = []
		lines.append("[b][color=gold]%s[/color][/b]  [i](%s)[/i]" % [name, kind])
		lines.append("持有者：%s" % owner_label)
		if not affixes.is_empty():
			var affix_strs: Array[String] = []
			for a in affixes:
				affix_strs.append(str(a))
			lines.append("词缀：%s" % ", ".join(affix_strs))
		if story != "":
			lines.append("[color=lightgray]%s[/color]" % story)
		lines.append("价值：%.2f" % value)

		# 耐久（只对装备显示）
		var cat: String = str(it.get("category", "material"))
		if cat == "equipment":
			var dur: int = int(it.get("durability", 100))
			var max_dur: int = int(it.get("max_durability", 100))
			if max_dur > 0:
				var dcolor := "lightgreen"
				if dur <= max_dur * 0.3:
					dcolor = "red"
				elif dur <= max_dur * 0.6:
					dcolor = "yellow"
				lines.append("耐久：[color=%s]%d / %d[/color]" % [dcolor, dur, max_dur])

		# 类别标签
		var cat_label: String = {
			"consumable": "消耗品",
			"equipment": "装备",
			"material": "材料",
			"key": "钥匙",
			"quest": "剧情物品",
		}.get(cat, "材料")
		lines.append("类别：[color=cyan]%s[/color]" % cat_label)

		item_detail.text = "\n".join(lines)

		var owner_id: String = str(it.get("owner_id", ""))
		var is_player := owner_id == "player"
		var is_npc := owner_id != "" and owner_id != "player"
		use_btn.disabled = not is_player
		give_btn.disabled = not is_player
		drop_btn.disabled = not is_player
		take_btn.disabled = not is_npc

		# 装备按钮：仅装备类可用
		var cat_eq: String = str(it.get("category", "material"))
		if equip_btn != null:
			equip_btn.disabled = not (is_player and cat_eq == "equipment")
		return


func _on_item_action_done(action: String, data: Dictionary) -> void:
	if action == "use":
		var effect: String = str(data.get("effect", ""))
		var consumed: bool = bool(data.get("consumed", false))
		item_detail.append_text("\n\n[b][color=cyan]使用效果：[/color][/b]%s" % effect)
		if consumed:
			item_detail.append_text("\n[i]（物品已消耗）[/i]")
	_refresh_all()


func _on_take_pressed() -> void:
	if current_item_id != "":
		api.take_item(current_item_id)


func _on_drop_pressed() -> void:
	if current_item_id != "":
		api.drop_item(current_item_id)


func _on_give_pressed() -> void:
	if current_item_id == "":
		return
	_show_target_picker("给予给谁？", func(target_id: String):
		if target_id != "":
			api.give_item(current_item_id, target_id)
	)


func _on_use_pressed() -> void:
	if current_item_id == "":
		return
	# 检查类别
	var cat: String = ""
	for it in items:
		if str(it.get("id", "")) == current_item_id:
			cat = str(it.get("category", "material"))
			break

	if cat == "material" or cat == "quest":
		# 直接提示不能使用
		item_detail.append_text("\n\n[color=gray]（这是材料/剧情物品，不能直接使用）[/color]")
		return

	if cat == "equipment":
		# 装备走装备流程（下一轮完整实现）
		# 装备走 /equip 端点
		api.equip_item(current_item_id)
		return

	if cat == "consumable":
		# 消耗品：可以对自己、对NPC、无目标
		_show_use_consumable_dialog()
		return

	if cat == "key":
		# 钥匙：对场景使用
		api.use_item(current_item_id, "", "scene")
		return

	# 兜底
	_show_target_picker("对谁使用？", func(target_id: String):
		api.use_item(current_item_id, target_id)
	)


func _show_use_consumable_dialog() -> void:
	var popup := PopupPanel.new()
	add_child(popup)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 8)
	vbox.custom_minimum_size = Vector2(320, 0)
	popup.add_child(vbox)

	var label := Label.new()
	label.text = "怎么使用？"
	vbox.add_child(label)

	# 自己
	var self_btn := Button.new()
	self_btn.text = "对自己使用"
	self_btn.pressed.connect(func():
		api.use_item(current_item_id, "", "self")
		popup.queue_free()
	)
	vbox.add_child(self_btn)

	# NPC
	var npc_row := HBoxContainer.new()
	npc_row.add_theme_constant_override("separation", 6)
	vbox.add_child(npc_row)

	var option := OptionButton.new()
	option.add_item("（选择 NPC）")
	for npc_id in npc_order:
		option.add_item(str(npc_data[npc_id].get("name", "?")))
	option.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	npc_row.add_child(option)

	var npc_btn := Button.new()
	npc_btn.text = "对 NPC 使用"
	npc_btn.pressed.connect(func():
		var sel := option.selected
		if sel <= 0:
			return
		var target_id := npc_order[sel - 1]
		api.use_item(current_item_id, target_id, "npc")
		popup.queue_free()
	)
	npc_row.add_child(npc_btn)

	# 取消
	var cancel := Button.new()
	cancel.text = "取消"
	cancel.pressed.connect(func(): popup.queue_free())
	vbox.add_child(cancel)

	popup.popup_centered(Vector2i(340, 220))


func _show_target_picker(title: String, on_confirm: Callable) -> void:
	var popup := PopupPanel.new()
	add_child(popup)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 8)
	vbox.custom_minimum_size = Vector2(280, 0)
	popup.add_child(vbox)

	var label := Label.new()
	label.text = title
	vbox.add_child(label)

	var option := OptionButton.new()
	option.add_item("（无目标）")
	for npc_id in npc_order:
		option.add_item(str(npc_data[npc_id].get("name", "?")))
	vbox.add_child(option)

	var btns := HBoxContainer.new()
	btns.add_theme_constant_override("separation", 8)
	vbox.add_child(btns)

	var ok_btn := Button.new()
	ok_btn.text = "确认"
	btns.add_child(ok_btn)

	var cancel_btn := Button.new()
	cancel_btn.text = "取消"
	btns.add_child(cancel_btn)

	ok_btn.pressed.connect(func():
		var sel := option.selected
		var target := ""
		if sel > 0 and sel - 1 < npc_order.size():
			target = npc_order[sel - 1]
		on_confirm.call(target)
		popup.queue_free()
	)
	cancel_btn.pressed.connect(func(): popup.queue_free())

	popup.popup_centered(Vector2i(300, 140))


# ================================================================
# 史册
# ================================================================

func _on_chronicle_list(data: Array) -> void:
	chronicle_log.clear()
	if data.is_empty():
		chronicle_log.text = "[i]还没有史册。点击下方按钮生成一份。[/i]"
		return
	for c in data:
		if not c is Dictionary:
			continue
		var title: String = str(c.get("title", "?"))
		title = _replace_template_ids(title)
		chronicle_log.append_text("[b][color=gold]%s[/color][/b]\n" % title)

		var body: String = str(c.get("body", ""))
		body = _replace_template_ids(body)
		body = _highlight_names(body)
		chronicle_log.append_text("[color=lightgray]%s[/color]\n\n" % body)

		chronicle_log.append_text("[i]——  记录于第 %d 回合[/i]\n\n" % int(c.get("created_at", 0)))


func _on_generate_chronicle() -> void:
	var hint: String = chronicle_title_input.text.strip_edges()
	_set_loading("正在编纂史册（调用 LLM）...")
	api.generate_chronicle(hint)


func _on_chronicle_generated(data: Dictionary) -> void:
	_set_loading("")
	chronicle_title_input.text = ""
	api.fetch_chronicles(10)


func _on_request_failed(endpoint: String, error: String) -> void:
	push_warning("Request failed: %s -> %s" % [endpoint, error])
	status_label.text = "[color=red]错误：%s[/color]" % error
	if is_step_24_running:
		is_step_24_running = false
		step_24_done = 0
	_set_loading("")


func _on_explore_pressed() -> void:
	if not player_created:
		return
	explore_btn.disabled = true
	explore_result_label.text = "[i]你走出村庄，四处张望...[/i]"
	api.explore()


func _on_explore_done(data: Dictionary) -> void:
	explore_btn.disabled = false

	var lines: Array[String] = []

	# 地点
	if data.get("found_location", false):
		lines.append("[color=gold][b]发现新地点：%s[/b][/color]" % str(data.get("target_label", "")))
	else:
		lines.append("[color=gray]未能发现新地点[/color]")

	# flavor
	var flavor: String = str(data.get("flavor", ""))
	if flavor != "":
		lines.append("[i]%s[/i]" % flavor)

	# check
	var check = data.get("check", {})
	if check is Dictionary and check.has("result"):
		var result_zh: String = {
			"critical": "大成功",
			"success": "成功",
			"partial": "勉强",
			"failure": "失败",
		}.get(str(check.get("result", "")), "")
		lines.append("[color=cyan]感知 %d + 骰 %d = %d vs 难度 %d → [b]%s[/b][/color]" % [
			int(check.get("base", 0)),
			int(check.get("roll", 0)),
			int(check.get("total", 0)),
			int(check.get("threshold", 0)),
			result_zh,
		])

	# message
	var combat = data.get("combat")
	if combat is Dictionary:
		var enemy: String = str(combat.get("enemy", ""))
		if enemy != "":
			lines.append("")
			lines.append("[color=red]⚔ 遭遇：%s[/color]" % enemy)

	var msg: String = str(data.get("message", ""))
	if msg != "":
		lines.append(msg)

	var hp_before = data.get("hp_before")
	var hp_after = data.get("hp_after")
	if hp_before != null and hp_after != null:
		var dmg: int = int(data.get("damage", 0))
		if dmg > 0:
			lines.append("[color=red]损失生命 %d（现 %d）[/color]" % [dmg, int(hp_after)])
		else:
			lines.append("[color=lightgreen]安然无恙[/color]")

	# item
	var it = data.get("found_item")
	if it is Dictionary:
		lines.append("[color=gold]拾得：[b]%s[/b]（%s）[/color]" % [
			str(it.get("name", "?")), str(it.get("kind", "")),
		])

	# exp
	var exp_gain: int = int(data.get("exp_gain", 0))
	if exp_gain > 0:
		lines.append("[color=yellow]经验 +%d[/color]" % exp_gain)

	explore_result_label.text = "\n".join(lines)

	# 刷新 player 与地图
	var p_data = data.get("player")
	if p_data is Dictionary:
		player_data = p_data
		_render_player_panel()

	api.fetch_world_state()
	api.fetch_map()
	api.fetch_items(100)
	if current_npc_id != "":
		api.fetch_npc_items(current_npc_id)


func _ensure_explore_ui() -> void:
	if player_tab_panel == null:
		push_warning("player_tab_panel 未初始化，无法加探索按钮")
		return

	# 避免重复
	if explore_btn != null and is_instance_valid(explore_btn):
		return

	# 在 player_tab_panel 里找一个位置插入，放在"属性"标题上方
	var insert_index := player_tab_panel.get_child_count()
	for i in range(player_tab_panel.get_child_count()):
		var c := player_tab_panel.get_child(i)
		if c is Label:
			var lbl := c as Label
			if lbl.text.begins_with("属性"):
				insert_index = i
				break

	# 探索行
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)

	explore_btn = Button.new()
	explore_btn.text = "外出探索"
	explore_btn.pressed.connect(_on_explore_pressed)
	row.add_child(explore_btn)

	player_tab_panel.add_child(row)
	player_tab_panel.move_child(row, insert_index)

	# 结果框
	explore_result_label = RichTextLabel.new()
	explore_result_label.bbcode_enabled = true
	explore_result_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	explore_result_label.fit_content = true
	explore_result_label.custom_minimum_size = Vector2(0, 90)
	player_tab_panel.add_child(explore_result_label)
	player_tab_panel.move_child(explore_result_label, insert_index + 1)


func _ensure_action_ui() -> void:
	if explore_btn != null and is_instance_valid(explore_btn):
		explore_btn.visible = false
		if explore_result_label != null and is_instance_valid(explore_result_label):
			explore_result_label.visible = false
	if player_tab_panel == null:
		return
	if action_buttons_row != null and is_instance_valid(action_buttons_row):
		return

	action_buttons_row = HBoxContainer.new()
	action_buttons_row.add_theme_constant_override("separation", 4)

	var actions := [
		["explore", "外出探索"],
		["gather", "采集"],
		["hunt", "打猎"],
		["train", "修炼"],
		["socialize", "社交"],
	]
	for pair in actions:
		var btn := Button.new()
		btn.text = pair[1]
		var akey: String = str(pair[0])
		btn.pressed.connect(func(): _on_action_pressed(akey))
		action_buttons_row.add_child(btn)

	action_result_label = RichTextLabel.new()
	action_result_label.bbcode_enabled = true
	action_result_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	action_result_label.fit_content = true
	action_result_label.custom_minimum_size = Vector2(0, 100)

	# 插入到 player_tab_panel 里"属性"标题之前
	var insert_index := player_tab_panel.get_child_count()
	for i in range(player_tab_panel.get_child_count()):
		var c := player_tab_panel.get_child(i)
		if c is Label:
			var lbl := c as Label
			if lbl.text.begins_with("属性"):
				insert_index = i
				break

	player_tab_panel.add_child(action_buttons_row)
	player_tab_panel.move_child(action_buttons_row, insert_index)
	player_tab_panel.add_child(action_result_label)
	player_tab_panel.move_child(action_result_label, insert_index + 1)


func _on_action_pressed(action_name: String) -> void:
	if not player_created:
		return
	# 禁用所有按钮
	if action_buttons_row != null:
		for c in action_buttons_row.get_children():
			if c is Button:
				(c as Button).disabled = true
	if action_result_label != null:
		action_result_label.text = "[i]你开始了...[/i]"
	api.do_action(action_name)


func _on_action_done(data: Dictionary) -> void:
	if action_buttons_row != null:
		for c in action_buttons_row.get_children():
			if c is Button:
				(c as Button).disabled = false

	var lines: Array[String] = []
	var action_label: String = str(data.get("action_label", ""))

	# 判定结果
	var check = data.get("check", {})
	if check is Dictionary and check.has("result"):
		var result_zh: String = {
			"critical": "大成功",
			"success": "成功",
			"partial": "勉强",
			"failure": "失败",
		}.get(str(check.get("result", "")), "")
		var attr_key: String = str(check.get("attribute", ""))
		var attr_zh: String = {
			"strength": "力量",
			"agility": "敏捷",
			"intelligence": "智慧",
			"perception": "感知",
			"charisma": "魅力",
			"luck": "运气",
		}.get(attr_key, attr_key)
		lines.append("[color=cyan]%s %d + 骰 %d = %d vs 难度 %d → [b]%s[/b][/color]" % [
			attr_zh,
			int(check.get("base", 0)),
			int(check.get("roll", 0)),
			int(check.get("total", 0)),
			int(check.get("threshold", 0)),
			result_zh,
		])

	var msg: String = str(data.get("message", ""))
	if msg != "":
		lines.append(msg)

	var it = data.get("found_item")
	if it is Dictionary:
		lines.append("[color=gold]拾得：[b]%s[/b]（%s）[/color]" % [
			str(it.get("name", "?")), str(it.get("kind", "")),
		])

	var exp_gain: int = int(data.get("exp_gain", 0))
	if exp_gain > 0:
		lines.append("[color=yellow]经验 +%d[/color]" % exp_gain)

	# 属性成长
	var growth = data.get("attribute_growth")
	if growth is Dictionary:
		var attr_label: String = str(growth.get("attribute_label", ""))
		var new_val: int = int(growth.get("new_value", 0))
		if attr_label != "":
			lines.append("[color=gold]★ %s 提升到 %d[/color]" % [attr_label, new_val])

	# 世界事件
	var we = data.get("world_event")
	if we is Dictionary:
		lines.append("")
		lines.append("[color=orange]→ 世界也在转动：[/color][b]%s[/b] %s" % [
			str(we.get("template_label", "")),
			str(we.get("summary", "")),
		])
		if bool(we.get("awaiting_player", false)):
			lines.append("[color=orange]（有一件事正在等你决定，见【事件】Tab）[/color]")

	# 社交
	var sd = data.get("social")
	if sd is Dictionary:
		var lines_arr: Array = sd.get("lines", [])
		if not lines_arr.is_empty():
			lines.append("")
			lines.append("[color=cyan]你听见有人说话：[/color]")
			for line in lines_arr:
				if line is Dictionary:
					lines.append("   [b]%s[/b]：%s" % [
						str(line.get("speaker", "")),
						str(line.get("text", "")),
					])

	if action_result_label != null:
		action_result_label.text = "\n".join(lines)

	# 刷新 player
	var p_data = data.get("player")
	if p_data is Dictionary:
		player_data = p_data
		_render_player_panel()

	# 刷新世界
	api.fetch_world_state()
	api.fetch_map()
	api.fetch_events(50)
	api.fetch_items(100)
	api.fetch_npcs()


func _build_travel_row() -> void:
	# 在 player_tab_panel 里，"外出探索"按钮组上方插入前往行
	if player_tab_panel == null:
		return
	if travel_option != null and is_instance_valid(travel_option):
		return

	# 找一个插入位置：属性标题上方
	var insert_index := player_tab_panel.get_child_count()
	for i in range(player_tab_panel.get_child_count()):
		var c := player_tab_panel.get_child(i)
		if c is Label:
			var lbl := c as Label
			if lbl.text.begins_with("属性"):
				insert_index = i
				break

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	row.name = "TravelRow"

	var lbl_title := Label.new()
	lbl_title.text = "前往："
	row.add_child(lbl_title)

	travel_option = OptionButton.new()
	travel_option.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(travel_option)

	travel_btn = Button.new()
	travel_btn.text = "出发"
	travel_btn.pressed.connect(_on_travel_pressed)
	row.add_child(travel_btn)

	player_tab_panel.add_child(row)
	player_tab_panel.move_child(row, insert_index)

	travel_result_label = RichTextLabel.new()
	travel_result_label.bbcode_enabled = true
	travel_result_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	travel_result_label.fit_content = true
	travel_result_label.custom_minimum_size = Vector2(0, 40)
	player_tab_panel.add_child(travel_result_label)
	player_tab_panel.move_child(travel_result_label, insert_index + 1)


func _refresh_travel_options() -> void:
	if travel_option == null or not is_instance_valid(travel_option):
		return
	travel_option.clear()
	var known: Array = player_data.get("known_locations", [])
	var current_id: String = str(player_data.get("location_id", ""))
	for k in known:
		if not k is Dictionary:
			continue
		var label: String = str(k.get("label", k.get("id", "?")))
		if bool(k.get("current", false)):
			label += "（你在这里）"
		travel_option.add_item(label)
		travel_option.set_item_metadata(travel_option.item_count - 1, str(k.get("id", "")))
	# 默认选中第一个非当前位置
	for i in range(travel_option.item_count):
		var meta: String = str(travel_option.get_item_metadata(i))
		if meta != current_id:
			travel_option.select(i)
			break


func _on_travel_pressed() -> void:
	if not player_created or travel_option == null:
		return
	var idx := travel_option.selected
	if idx < 0:
		return
	var loc_id: String = str(travel_option.get_item_metadata(idx))
	if loc_id == "":
		return
	travel_btn.disabled = true
	travel_result_label.text = "[i]你启程了...[/i]"
	api.travel(loc_id)


func _on_travel_done(data: Dictionary) -> void:
	if travel_btn != null and is_instance_valid(travel_btn):
		travel_btn.disabled = false

	var from_label: String = str(data.get("from_label", ""))
	var to_label: String = str(data.get("to_label", ""))
	if travel_result_label != null:
		travel_result_label.text = "[color=cyan]你从【%s】来到【%s】[/color]" % [from_label, to_label]

	var p_data = data.get("player")
	if p_data is Dictionary:
		player_data = p_data
		_render_player_panel()

	api.fetch_world_state()
	api.fetch_map()
	api.fetch_events(50)


func _replace_template_ids(text: String) -> String:
	var re := RegEx.new()
	re.compile("\\[([a-z_]+)\\]")
	var result := text
	for m in re.search_all(text):
		var tid: String = m.get_string(1)
		var zh: String = tid
		if i18n_templates.has(tid):
			zh = str(i18n_templates[tid])
		result = result.replace("[%s]" % tid, "[%s]" % zh)
	return result


func _highlight_names(text: String) -> String:
	var result := text
	for npc_id in npc_order:
		var npc: Dictionary = npc_data[npc_id]
		var npc_name: String = str(npc.get("name", ""))
		if npc_name == "":
			continue
		var gender: String = str(npc.get("gender", "unknown"))
		var color := "#7ac4e8"
		if gender == "female":
			color = "#f0a0c0"
		elif gender == "male":
			color = "#88b8f0"
		result = result.replace(npc_name, "[color=%s]%s[/color]" % [color, npc_name])
	return result


func _color_name(npc_name: String) -> String:
	for npc_id in npc_order:
		var npc: Dictionary = npc_data[npc_id]
		if str(npc.get("name", "")) == npc_name:
			var gender: String = str(npc.get("gender", "unknown"))
			var color := "#7ac4e8"
			if gender == "female":
				color = "#f0a0c0"
			elif gender == "male":
				color = "#88b8f0"
			return "[color=%s]%s[/color]" % [color, npc_name]
	return npc_name


func _build_market_tab(parent: TabContainer) -> void:
	var tab := VBoxContainer.new()
	tab.name = "市场"
	tab.add_theme_constant_override("separation", 6)
	parent.add_child(tab)

	var ctrl := HBoxContainer.new()
	ctrl.add_theme_constant_override("separation", 6)
	tab.add_child(ctrl)

	var refresh := Button.new()
	refresh.text = "刷新行情"
	refresh.pressed.connect(func(): api.fetch_market())
	ctrl.add_child(refresh)

	var season_hint := Label.new()
	season_hint.text = "（季节影响价格）"
	season_hint.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
	ctrl.add_child(season_hint)

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	tab.add_child(scroll)

	market_log = RichTextLabel.new()
	market_log.bbcode_enabled = true
	market_log.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	market_log.fit_content = true
	market_log.meta_clicked.connect(_on_market_meta_clicked)
	market_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(market_log)


func _on_market_received(data: Dictionary) -> void:
	if market_log == null:
		return
	market_log.clear()

	var season_label: String = str(data.get("season_label", ""))
	var season_mult: float = float(data.get("season_mult", 1.0))
	var money: int = int(data.get("player_money", 0))

	market_log.append_text("[b]当前季节：[/b]%s（价格 ×%.2f）\n" % [season_label, season_mult])
	market_log.append_text("[b]你的铜钱：[/b][color=gold]%d[/color]\n\n" % money)

	# 可购买
	market_log.append_text("[b][color=orange]◆ 市场货物[/color][/b]\n")
	var goods: Array = data.get("goods", [])
	if goods.is_empty():
		market_log.append_text("  （空）\n")
	else:
		for g in goods:
			if not g is Dictionary:
				continue
			var name := str(g.get("name", "?"))
			var kind := str(g.get("kind", ""))
			var price := int(g.get("price", 0))
			var bv := float(g.get("base_value", 0))
			var can_afford := money >= price
			var color := "white" if can_afford else "dimgray"
			market_log.append_text(
				"[color=%s]·[/color] [url=buy:%s|%s|%d|%.3f][b]%s[/b]（%s）  [color=gold]%d 钱[/color][/url]\n"
				% [color, name, kind, price, bv, name, kind, price]
			)
		market_log.append_text("\n[i]点击货物买入[/i]\n\n")

	# 可卖出
	market_log.append_text("[b][color=cyan]◆ 你可卖出[/color][/b]\n")
	var sell_list: Array = data.get("sell_list", [])
	if sell_list.is_empty():
		market_log.append_text("  （你身上没有可卖的东西）\n")
	else:
		for it in sell_list:
			if not it is Dictionary:
				continue
			var iname := str(it.get("name", "?"))
			var ikind := str(it.get("kind", ""))
			var iprice := int(it.get("sell_price", 0))
			var iid := str(it.get("id", ""))
			market_log.append_text(
				"[url=sell:%s][b]%s[/b]（%s）  [color=gold]卖 %d 钱[/color][/url]\n"
				% [iid, iname, ikind, iprice]
			)
		market_log.append_text("\n[i]点击物品卖出[/i]\n")


func _on_market_meta_clicked(meta) -> void:
	var s := str(meta)
	if s.begins_with("sell:"):
		var item_id := s.substr(5)
		api.trade_sell(item_id)
	elif s.begins_with("buy:"):
		var rest := s.substr(4)
		var parts := rest.split("|")
		if parts.size() >= 4:
			var name := str(parts[0])
			var kind := str(parts[1])
			var price := int(parts[2])
			var bv := float(parts[3])
			api.trade_buy(name, kind, price, bv)


func _on_trade_done(data: Dictionary) -> void:
	# 交易完成，刷新市场 + 物品 + 玩家
	api.fetch_market()
	api.fetch_items(100)
	api.fetch_player()


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
	goal_log.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
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

	goal_log.append_text("[color=gold]◆ 今日[/color]\n")
	if daily.is_empty():
		goal_log.append_text("  （无）\n")
	for g in daily:
		if not g is Dictionary:
			continue
		_render_goal(g)
	goal_log.append_text("\n[color=cyan]◆ 长期[/color]\n")
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
		goal_log.append_text("  [color=dimgray]✓ %s  (已领取)[/color]\n" % label)
		return
	if done:
		var reward := []
		if exp_r > 0:
			reward.append("经验 +%d" % exp_r)
		if money_r > 0:
			reward.append("铜钱 +%d" % money_r)
		goal_log.append_text("  [color=gold][url=claim:%s][b]★ %s[/b]  [领取：%s][/url][/color]\n" % [
			gid, label, "、".join(reward),
		])
		return

	goal_log.append_text("  · %s  (%d/%d)\n" % [label, progress, target])


func _on_goal_meta_clicked(meta) -> void:
	var s := str(meta)
	if s.begins_with("claim:"):
		api.claim_goal(s.substr(6))


func _on_goal_claimed(data: Dictionary) -> void:
	# 刷新玩家 + 目标
	api.fetch_player()
	api.fetch_goals()


func _build_quest_tab(parent: TabContainer) -> void:
	var tab := VBoxContainer.new()
	tab.name = "任务"
	tab.add_theme_constant_override("separation", 6)
	parent.add_child(tab)

	var ctrl := HBoxContainer.new()
	ctrl.add_theme_constant_override("separation", 6)
	tab.add_child(ctrl)

	var refresh := Button.new()
	refresh.text = "刷新任务"
	refresh.pressed.connect(func(): api.fetch_quests())
	ctrl.add_child(refresh)

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	tab.add_child(scroll)

	quest_log = RichTextLabel.new()
	quest_log.bbcode_enabled = true
	quest_log.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	quest_log.fit_content = true
	quest_log.meta_clicked.connect(_on_quest_meta_clicked)
	quest_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(quest_log)


func _on_quest_list_received(data: Array) -> void:
	if quest_log == null:
		return
	quest_log.clear()

	if data.is_empty():
		quest_log.text = "[i]你还没有接到任何任务。触发一些事件后，可能会有人找上你。[/i]"
		return

	var active: Array = []
	var done: Array = []
	for q in data:
		if not q is Dictionary:
			continue
		var st: String = str(q.get("state", ""))
		if st == "active":
			active.append(q)
		elif st in ["completed", "failed", "abandoned"]:
			done.append(q)

	if not active.is_empty():
		quest_log.append_text("[b][color=orange]=== 进行中 ===[/color][/b]\n\n")
		for q in active:
			_render_quest_entry(q, true)

	if not done.is_empty():
		quest_log.append_text("\n[b][color=gray]=== 已结束 ===[/color][/b]\n\n")
		for q in done:
			_render_quest_entry(q, false)


func _render_quest_entry(q: Dictionary, active: bool) -> void:
	var qid: String = str(q.get("id", ""))
	var title: String = str(q.get("title", "?"))
	var desc: String = str(q.get("description", ""))
	var giver: String = str(q.get("giver_name", ""))
	var loc_label: String = str(q.get("target_location_label", ""))
	var state: String = str(q.get("state", ""))
	var exp_r: int = int(q.get("reward_exp", 0))
	var money_r: int = int(q.get("reward_money", 0))

	if active:
		quest_log.append_text("[b][color=gold]◆ %s[/color][/b]\n" % title)
		if desc != "":
			quest_log.append_text("    %s\n" % desc)
		if giver != "":
			quest_log.append_text("    [color=lightgray]委托人：%s[/color]\n" % giver)
		if loc_label != "":
			quest_log.append_text("    [color=cyan]目标地点：%s[/color]\n" % loc_label)

		var rk: String = str(q.get("require_item_kind", ""))
		var rc: int = int(q.get("require_item_count", 0))
		if rk != "" and rc > 0:
			quest_log.append_text("    [color=yellow]需要：%s×%d[/color]\n" % [rk, rc])

		var rewards: Array[String] = []
		if exp_r > 0:
			rewards.append("经验 +%d" % exp_r)
		if money_r > 0:
			rewards.append("铜钱 +%d" % money_r)
		if not rewards.is_empty():
			quest_log.append_text("    [color=yellow]奖励：%s[/color]\n" % "、".join(rewards))

		quest_log.append_text("    [url=abandon:%s][放弃任务][/url]\n\n" % qid)
	else:
		var color := "dimgray"
		var state_label := "已结束"
		if state == "completed":
			color = "lightgreen"
			state_label = "✓ 已完成"
		elif state == "abandoned":
			color = "darkgray"
			state_label = "已放弃"
		quest_log.append_text("[color=%s]· %s（%s）[/color]\n\n" % [color, title, state_label])


func _on_quest_meta_clicked(meta) -> void:
	var s := str(meta)
	if s.begins_with("abandon:"):
		api.abandon_quest(s.substr(8))


func _on_quest_abandoned(data: Dictionary) -> void:
	api.fetch_quests()


func _force_clear_loading() -> void:
	is_step_24_running = false
	step_24_done = 0
	_set_loading("")
	if trigger_btn:
		trigger_btn.disabled = false
	if step_btn:
		step_btn.disabled = false
	if step24_btn:
		step24_btn.disabled = false
	if refresh_btn:
		refresh_btn.disabled = false


func _on_map_location_clicked(location_id: String) -> void:
	if not player_created:
		return
	var cur_loc: String = str(player_data.get("location_id", ""))
	if location_id == cur_loc:
		status_label.text = "[color=gray]你已经在这里了[/color]"
		return

	print("[ui] 地图点击前往：%s" % location_id)
	if travel_btn != null and is_instance_valid(travel_btn):
		travel_btn.disabled = true
	if travel_result_label != null:
		travel_result_label.text = "[i]你启程了...[/i]"
	api.travel(location_id)


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
	faction_log.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	faction_log.fit_content = true
	faction_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(faction_log)


func _on_factions_received(data: Dictionary) -> void:
	if faction_log == null:
		return
	faction_log.clear()

	var factions: Array = data.get("factions", [])
	var discount: float = float(data.get("market_discount", 1.0))

	faction_log.append_text("[b][color=gold]◆ 派系声望[/color][/b]\n\n")
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

		faction_log.append_text("[b]%s[/b]  [color=%s]%+d[/color]  [i]%s[/i]\n" % [
			label, color, value, attitude,
		])
		faction_log.append_text("    [color=lightgray]%s[/color]\n\n" % desc)

	faction_log.append_text("\n[b][color=cyan]◆ 市场折扣[/color][/b]\n")
	if discount < 1.0:
		faction_log.append_text("    商帮声望让你享受 [color=green]%.0f%%[/color] 优惠\n" % ((1.0 - discount) * 100))
	elif discount > 1.0:
		faction_log.append_text("    商帮态度冷淡，价格上浮 [color=red]%.0f%%[/color]\n" % ((discount - 1.0) * 100))
	else:
		faction_log.append_text("    无折扣\n")


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
	craft_log.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
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

		craft_log.append_text("[color=%s]%s [b]%s[/b][/color]  [i](%s)[/i]\n" % [
			color, prefix, name, kind,
		])
		craft_log.append_text("    %s\n" % desc)

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
		craft_log.append_text("    材料：%s\n" % "、".join(mat_lines))

		if can_craft:
			craft_log.append_text("    [url=craft:%s][color=green][合成][/color][/url]\n" % rid)
		else:
			craft_log.append_text("    [color=gray]（材料不足）[/color]\n")

		craft_log.append_text("\n")


func _on_craft_meta_clicked(meta) -> void:
	var s := str(meta)
	if s.begins_with("craft:"):
		var rid := s.substr(6)
		api.craft_item(rid)


func _on_craft_done(data: Dictionary) -> void:
	api.fetch_items(200)
	api.fetch_recipes()


func _on_unequip_pressed(slot: String) -> void:
	api.unequip_slot(slot)

func _on_equip_done(data: Dictionary) -> void:
	api.fetch_player()
	api.fetch_items(200)
	status_label.text = "[color=gold]装备：%s（%s）[/color]" % [
		str(data.get("item_name", "")),
		str(data.get("slot_label", "")),
	]

func _on_unequip_done(data: Dictionary) -> void:
	api.fetch_player()
	api.fetch_items(200)
	status_label.text = "[color=gray]已卸下 %s[/color]" % str(data.get("slot", ""))

func _on_equip_pressed() -> void:
	if current_item_id == "":
		return
	api.equip_item(current_item_id)



var _npc_offer_quests: Array = []
var _npc_active_quests: Array = []


func _on_npc_quests_received(data: Array) -> void:
	_npc_offer_quests = data
	_render_npc_quests_panel()


func _on_npc_active_quests_received(data: Array) -> void:
	_npc_active_quests = data
	_render_npc_quests_panel()


func _render_npc_quests_panel() -> void:
	if npc_quests_panel == null:
		return
	for child in npc_quests_panel.get_children():
		child.queue_free()

	# 待提交优先
	if not _npc_active_quests.is_empty():
		var t1 := RichTextLabel.new()
		t1.bbcode_enabled = true
		t1.fit_content = true
		t1.custom_minimum_size = Vector2(0, 20)
		t1.text = "[color=orange][b][待提交][/b][/color]"
		npc_quests_panel.add_child(t1)

		for q in _npc_active_quests:
			if not q is Dictionary:
				continue
			var row := HBoxContainer.new()
			row.add_theme_constant_override("separation", 6)

			var info := RichTextLabel.new()
			info.bbcode_enabled = true
			info.fit_content = true
			info.custom_minimum_size = Vector2(0, 20)
			var title_s: String = str(q.get("title", "?"))
			var exp_r: int = int(q.get("reward_exp", 0))
			var money_r: int = int(q.get("reward_money", 0))
			var ready: bool = bool(q.get("ready", false))
			var rk: String = str(q.get("require_item_kind", ""))
			var rc: int = int(q.get("require_item_count", 0))
			var needs_turn_in: bool = bool(q.get("needs_turn_in", false))

			var status := ""
			if needs_turn_in and rc > 0:
				if ready:
					status = "[color=green]（已集齐%s）[/color]" % rk
				else:
					status = "[color=gray]（还需%s×%d）[/color]" % [rk, rc]

			info.text = "%s  (%d经验,%d钱) %s" % [title_s, exp_r, money_r, status]
			info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			row.add_child(info)

			if needs_turn_in:
				var btn := Button.new()
				btn.text = "提交"
				if not ready:
					btn.disabled = true
				var qid: String = str(q.get("id", ""))
				btn.pressed.connect(func(): _on_turn_in_pressed(qid))
				row.add_child(btn)
			else:
				# 非 fetch 类：显示"等待触发"提示
				var hint := Label.new()
				hint.text = "[去目标地点]"
				hint.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
				row.add_child(hint)

			npc_quests_panel.add_child(row)

	# 可接受
	if not _npc_offer_quests.is_empty():
		var t2 := RichTextLabel.new()
		t2.bbcode_enabled = true
		t2.fit_content = true
		t2.custom_minimum_size = Vector2(0, 20)
		t2.text = "[color=gold][b][可接受][/b][/color]"
		npc_quests_panel.add_child(t2)

		for q in _npc_offer_quests:
			if not q is Dictionary:
				continue
			var row2 := HBoxContainer.new()
			row2.add_theme_constant_override("separation", 6)

			var info2 := RichTextLabel.new()
			info2.bbcode_enabled = true
			info2.fit_content = true
			info2.custom_minimum_size = Vector2(0, 20)
			var title_s2: String = str(q.get("title", "?"))
			var exp_r2: int = int(q.get("reward_exp", 0))
			var money_r2: int = int(q.get("reward_money", 0))
			var loc_label: String = str(q.get("require_location_label", ""))
			info2.text = "%s -> %s (%d经验,%d钱)" % [title_s2, loc_label, exp_r2, money_r2]
			info2.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			row2.add_child(info2)

			var btn2 := Button.new()
			btn2.text = "接受"
			var qid2: String = str(q.get("id", ""))
			var nid := current_npc_id
			btn2.pressed.connect(func(): _on_accept_quest_pressed(nid, qid2))
			row2.add_child(btn2)
			npc_quests_panel.add_child(row2)


func _on_accept_quest_pressed(npc_id: String, quest_def_id: String) -> void:
	api.accept_npc_quest(npc_id, quest_def_id)


func _on_quest_accepted(data: Dictionary) -> void:
	status_label.text = "[color=gold]已接受任务：%s[/color]" % str(data.get("title", ""))
	api.fetch_quests()
	if current_npc_id != "":
		api.fetch_npc_quests(current_npc_id)
		api.fetch_npc_active_quests(current_npc_id)


func _on_turn_in_pressed(quest_id: String) -> void:
	api.turn_in_quest(quest_id)


func _on_quest_turned_in(data: Dictionary) -> void:
	if data.get("ok") == false:
		status_label.text = "[color=red]提交失败：%s[/color]" % str(data.get("error", ""))
		return
	status_label.text = "[color=gold]完成任务：%s（+%d经验 +%d钱）[/color]" % [
		str(data.get("title", "")),
		int(data.get("reward_exp", 0)),
		int(data.get("reward_money", 0)),
	]
	var p_data = data.get("player")
	if p_data is Dictionary:
		player_data = p_data
		_render_player_panel()
	# 刷新
	api.fetch_quests()
	api.fetch_items(200)
	if current_npc_id != "":
		api.fetch_npc_active_quests(current_npc_id)
		api.fetch_npc_quests(current_npc_id)
		api.fetch_npc_items(current_npc_id)
