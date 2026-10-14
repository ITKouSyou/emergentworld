# 前端：市场面板
from pathlib import Path

# 1. api.gd 加市场方法
p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")

if "func fetch_market" not in t:
    anchor = "func fetch_world_state() -> void:"
    addition = '''signal market_received(data: Dictionary)
signal trade_done(data: Dictionary)

func fetch_market() -> void:
	_request("GET", "/market", {}, "market_received")

func trade_sell(item_id: String) -> void:
	_request("POST", "/trade/sell", {"item_id": item_id}, "trade_done")

func trade_buy(name: String, kind: String, price: int, base_value: float) -> void:
	_request("POST", "/trade/buy",
		{"name": name, "kind": kind, "price": price, "base_value": base_value},
		"trade_done")

'''
    if anchor in t:
        t = t.replace(anchor, addition + anchor, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] api.gd 加市场方法")
    else:
        print("[fail] api.gd 锚点未找到")
else:
    print("[skip] api.gd 已有市场方法")

# 2. main.gd 加市场 Tab
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 2.1 变量
if "var market_log:" not in t:
    anchor = "var reward_log: RichTextLabel\n"
    addition = "var market_log: RichTextLabel\nvar market_buy_row: HBoxContainer\n"
    if anchor in t:
        t = t.replace(anchor, anchor + addition, 1)
        print("[fix] main.gd 加市场变量")

# 2.2 信号连接（强制插）
start = t.find("func _connect_signals() -> void:")
if start >= 0:
    end = t.find("\n\nfunc ", start + 1)
    if end < 0:
        end = len(t)
    body = t[start:end]
    if "api.market_received.connect" not in body:
        anchor = "api.request_failed.connect(_on_request_failed)"
        if anchor not in body:
            anchor = "        api.request_failed.connect(_on_request_failed)"
        if anchor in body:
            indent = anchor[:len(anchor) - len(anchor.lstrip())]
            new_lines = (
                indent + "api.market_received.connect(_on_market_received)\n"
                + indent + "api.trade_done.connect(_on_trade_done)\n"
            )
            body = body.replace(anchor, new_lines + anchor, 1)
            t = t[:start] + body + t[end:]
            print("[fix] 连接市场信号")

# 2.3 在 _build_ui 里加市场 Tab
old_right = '''	_build_event_tab(right_tabs)
	_build_chronicle_tab(right_tabs)
	_build_reward_tab(right_tabs)
	_build_item_tab(right_tabs)'''

new_right = '''	_build_event_tab(right_tabs)
	_build_chronicle_tab(right_tabs)
	_build_market_tab(right_tabs)
	_build_reward_tab(right_tabs)
	_build_item_tab(right_tabs)'''

if old_right in t:
    t = t.replace(old_right, new_right, 1)
    print("[fix] _build_ui 加市场 Tab")
else:
    print("[skip] _build_ui 已改过")

# 2.4 加 _build_market_tab 和 handler
if "_build_market_tab" not in t or t.count("_build_market_tab") < 2:
    tail = '''

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

	market_log.append_text("[b]当前季节：[/b]%s（价格 ×%.2f）\\n" % [season_label, season_mult])
	market_log.append_text("[b]你的铜钱：[/b][color=gold]%d[/color]\\n\\n" % money)

	# 可购买
	market_log.append_text("[b][color=orange]◆ 市场货物[/color][/b]\\n")
	var goods: Array = data.get("goods", [])
	if goods.is_empty():
		market_log.append_text("  （空）\\n")
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
				"[color=%s]·[/color] [url=buy:%s|%s|%d|%.3f][b]%s[/b]（%s）  [color=gold]%d 钱[/color][/url]\\n"
				% [color, name, kind, price, bv, name, kind, price]
			)
		market_log.append_text("\\n[i]点击货物买入[/i]\\n\\n")

	# 可卖出
	market_log.append_text("[b][color=cyan]◆ 你可卖出[/color][/b]\\n")
	var sell_list: Array = data.get("sell_list", [])
	if sell_list.is_empty():
		market_log.append_text("  （你身上没有可卖的东西）\\n")
	else:
		for it in sell_list:
			if not it is Dictionary:
				continue
			var iname := str(it.get("name", "?"))
			var ikind := str(it.get("kind", ""))
			var iprice := int(it.get("sell_price", 0))
			var iid := str(it.get("id", ""))
			market_log.append_text(
				"[url=sell:%s][b]%s[/b]（%s）  [color=gold]卖 %d 钱[/color][/url]\\n"
				% [iid, iname, ikind, iprice]
			)
		market_log.append_text("\\n[i]点击物品卖出[/i]\\n")


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
'''
    t = t.rstrip() + "\n" + tail
    print("[fix] main.gd 加市场 Tab")

# 2.5 在 _on_i18n_received 里也拉一次市场
if "api.fetch_market()" not in t.replace("func fetch_market", "").replace("func _build_market_tab", ""):
    anchor = "\tapi.fetch_chronicles(10)\n"
    if anchor in t:
        t = t.replace(anchor, anchor + "\tapi.fetch_market()\n", 1)
        print("[fix] 刷新时拉市场")
    else:
        # 备用：找 _refresh_all
        i = t.find("func _refresh_all")
        if i >= 0:
            e = t.find("\n\nfunc ", i + 1)
            body = t[i:e]
            if "api.fetch_market" not in body:
                body_new = body.rstrip() + "\n\tapi.fetch_market()\n"
                t = t[:i] + body_new + t[e:]
                print("[fix] _refresh_all 里拉市场")

p.write_text(t, encoding="utf-8")
print()
print("前端完成。重启 uvicorn + Godot 完全关闭重开")