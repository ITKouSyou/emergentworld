# Part 82B：/craft 端点 + 前端合成 Tab
from pathlib import Path

# ============================================================
# 1. main.py：加 /craft 端点
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

if "/craft" not in t:
    anchor = '''@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''
    addition = '''# ---------- Crafting ----------

@app.get("/craft/recipes")
def list_recipes() -> list[dict]:
    with get_session() as s:
        from server.systems import crafting as craft_sys
        return craft_sys.list_available_recipes(s, "player")


class CraftRequest(BaseModel):
    recipe_id: str


@app.post("/craft")
def do_craft(req: CraftRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")
        from server.systems import crafting as craft_sys
        result = craft_sys.craft(s, world, player, req.recipe_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "craft failed"))
        return result


@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] main.py 加 /craft 端点")

# /item 返回 durability
t = p.read_text(encoding="utf-8")
old = '''        "owner_id": owner_id,
        "owner_label": owner_label,
        "consumed": r.consumed,
    }'''
new = '''        "owner_id": owner_id,
        "owner_label": owner_label,
        "consumed": r.consumed,
        "durability": getattr(r, "durability", 100),
        "max_durability": getattr(r, "max_durability", 100),
    }'''
if old in t and "durability" not in t.split("_row_to_item")[1][:500]:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] /item 返回 durability")

# ============================================================
# 2. api.gd：加 craft 方法
# ============================================================
p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")

if "func fetch_recipes" not in t:
    anchor = "func fetch_world_state() -> void:"
    addition = '''signal recipes_received(data: Array)
signal craft_done(data: Dictionary)

func fetch_recipes() -> void:
	_request("GET", "/craft/recipes", {}, "recipes_received")

func craft_item(recipe_id: String) -> void:
	_request("POST", "/craft", {"recipe_id": recipe_id}, "craft_done")

'''
    if anchor in t:
        t = t.replace(anchor, addition + anchor, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] api.gd 加 craft 方法")

# ============================================================
# 3. main.gd：合成 Tab
# ============================================================
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 3.1 变量
if "var craft_log:" not in t:
    anchor = "var faction_log: RichTextLabel\n"
    if anchor in t:
        t = t.replace(anchor, anchor + "var craft_log: RichTextLabel\nvar all_recipes: Array = []\n", 1)
        print("[fix] 加 craft_log 变量")

# 3.2 信号
start = t.find("func _connect_signals() -> void:")
if start >= 0:
    after = t.find("\nfunc ", start + 1)
    if after < 0:
        after = len(t)
    body = t[start:after]
    if "api.recipes_received.connect" not in body:
        # 找最后一行 connect 做锚点
        lines = body.split("\n")
        insert_idx = -1
        for i in range(len(lines) - 1, -1, -1):
            s = lines[i].strip()
            if s.startswith("api.") and ".connect(" in s:
                insert_idx = i
                break
        if insert_idx >= 0:
            indent = lines[insert_idx][:len(lines[insert_idx]) - len(lines[insert_idx].lstrip())]
            lines.insert(insert_idx + 1, indent + "api.recipes_received.connect(_on_recipes_received)")
            lines.insert(insert_idx + 2, indent + "api.craft_done.connect(_on_craft_done)")
            body = "\n".join(lines)
            t = t[:start] + body + t[after:]
            p.write_text(t, encoding="utf-8")
            print("[fix] 连接 craft 信号")

t = p.read_text(encoding="utf-8")

# 3.3 在 _build_ui 加"合成"Tab
import re
# 找 _build_item_tab(right_tabs) 那行，在它后面加
pattern = re.compile(r"(\n([ \t]+)_build_item_tab\(right_tabs\)\n)")
m = pattern.search(t)
if m and "_build_craft_tab" not in t.split(m.end())[:500]:
    indent = m.group(2)
    insert_line = indent + "_build_craft_tab(right_tabs)\n"
    t = t[:m.end()] + insert_line + t[m.end():]
    p.write_text(t, encoding="utf-8")
    print("[fix] _build_ui 加合成 Tab 调用")

# 3.4 追加函数
t = p.read_text(encoding="utf-8")
if "_build_craft_tab" not in t:
    tail = '''

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

		craft_log.append_text("[color=%s]%s [b]%s[/b][/color]  [i](%s)[/i]\\n" % [
			color, prefix, name, kind,
		])
		craft_log.append_text("    %s\\n" % desc)

		# 材料
		var mats: Array = r.get("materials", [])
		var mat_lines: Array[String] = []
		for m in mats:
			if not m is Dictionary:
				continue
			var mk: String = str(m.get("kind", ""))
			var need: int = int(m.get("count", 0))
			var have: int = int(m.get("have", 0))
			var ok := have >= need
			var mc := "lightgreen" if ok else "red"
			mat_lines.append("[color=%s]%s %d/%d[/color]" % [mc, mk, have, need])
		craft_log.append_text("    材料：%s\\n" % "、".join(mat_lines))

		if can_craft:
			craft_log.append_text("    [url=craft:%s][color=green][合成][/color][/url]\\n" % rid)
		else:
			craft_log.append_text("    [color=gray]（材料不足）[/color]\\n")

		craft_log.append_text("\\n")


func _on_craft_meta_clicked(meta) -> void:
	var s := str(meta)
	if s.begins_with("craft:"):
		var rid := s.substr(6)
		api.craft_item(rid)


func _on_craft_done(data: Dictionary) -> void:
	# 刷新物品 + 配方
	api.fetch_items(200)
	api.fetch_recipes()
'''
    t = t.rstrip() + "\n" + tail
    p.write_text(t, encoding="utf-8")
    print("[fix] main.gd 加合成 Tab")

# 3.5 _refresh_all 拉配方
t = p.read_text(encoding="utf-8")
i = t.find("func _refresh_all() -> void:")
if i >= 0:
    e = t.find("\nfunc ", i + 1)
    body = t[i:e]
    if "api.fetch_recipes" not in body:
        body_new = body.rstrip() + "\n\tapi.fetch_recipes()\n"
        t = t[:i] + body_new + t[e:]
        p.write_text(t, encoding="utf-8")
        print("[fix] _refresh_all 拉配方")

# ============================================================
# 4. 物品详情显示耐久
# ============================================================
t = p.read_text(encoding="utf-8")
old_dur = '''		lines.append("价值：%.2f" % value)
		item_detail.text = "\\n".join(lines)'''
new_dur = '''		lines.append("价值：%.2f" % value)

		# 耐久
		var dur: int = int(it.get("durability", 100))
		var max_dur: int = int(it.get("max_durability", 100))
		if max_dur > 0:
			var dcolor := "lightgreen"
			if dur <= max_dur * 0.3:
				dcolor = "red"
			elif dur <= max_dur * 0.6:
				dcolor = "yellow"
			lines.append("耐久：[color=%s]%d / %d[/color]" % [dcolor, dur, max_dur])

		item_detail.text = "\\n".join(lines)'''
if old_dur in t and "耐久：" not in t:
    t = t.replace(old_dur, new_dur, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 物品详情显示耐久")

print()
print("===== 完成 =====")
print("测试：pytest -v")
print("重启：uvicorn server.main:app")
print("Godot 完全关闭重开")