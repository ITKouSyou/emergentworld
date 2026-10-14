# Part 85B：API + 前端 + 迁移
from pathlib import Path

# ============================================================
# 1. main.py：/item/{id}/use 接收 target_type
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

# 找 UseRequest 和 use_item_endpoint
start = t.find("class UseRequest(BaseModel):")
if start < 0:
    print("[fail] 找不到 UseRequest")
    raise SystemExit(1)

# 替换 UseRequest
old_req = '''class UseRequest(BaseModel):
    target_npc_id: str = ""'''
new_req = '''class UseRequest(BaseModel):
    target_npc_id: str = ""
    target_type: str = "auto"'''
if old_req in t:
    t = t.replace(old_req, new_req, 1)
    print("[fix] UseRequest 加 target_type")

# 替换 use_item_endpoint
old_ep = '''@app.post("/item/{item_id}/use")
async def use_item_endpoint(item_id: str, req: UseRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        result = await item_use.use_item(
            s, world, item_id=item_id,
            user_id="player", target_npc_id=req.target_npc_id,
        )
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "use failed"))
        return result'''

new_ep = '''@app.post("/item/{item_id}/use")
async def use_item_endpoint(item_id: str, req: UseRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        result = await item_use.use_item(
            s, world, item_id=item_id,
            user_id="player",
            target_npc_id=req.target_npc_id,
            target_type=req.target_type,
        )
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "use failed"))
        return result'''

if old_ep in t:
    t = t.replace(old_ep, new_ep, 1)
    print("[fix] use_item_endpoint 传 target_type")

# _row_to_item 返回 category / use_effect / slot
old_item = '''        "owner_id": owner_id,
        "owner_label": owner_label,
        "consumed": r.consumed,
        "durability": getattr(r, "durability", 100),
        "max_durability": getattr(r, "max_durability", 100),
    }'''
new_item = '''        "owner_id": owner_id,
        "owner_label": owner_label,
        "consumed": r.consumed,
        "durability": getattr(r, "durability", 100),
        "max_durability": getattr(r, "max_durability", 100),
        "category": getattr(r, "category", "material") or "material",
        "slot": getattr(r, "slot", "") or "",
    }'''
if old_item in t:
    t = t.replace(old_item, new_item, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] /item 返回 category/slot")

p.write_text(t, encoding="utf-8")

# ============================================================
# 2. 数据迁移脚本：给已有物品补 category
# ============================================================
Path("tools/migrate_items.py").write_text('''# 给已有物品补 category / use_effect / slot
from sqlmodel import Session, create_engine, select

from server.config import settings
from server.models.db import ItemRow
from server.systems import item_meta

import json


def main():
    engine = create_engine(f"sqlite:///{settings.db_path}")
    with Session(engine) as s:
        rows = list(s.exec(select(ItemRow)).all())
        n = 0
        for r in rows:
            cat = getattr(r, "category", "") or ""
            if not cat or cat == "material":
                cat = item_meta.infer_category(r.kind)
                r.category = cat
            if cat == "consumable":
                eff = item_meta.infer_effect(r.kind)
                if eff:
                    r.use_effect_json = json.dumps(eff, ensure_ascii=False)
            if cat == "equipment":
                r.slot = item_meta.infer_slot(r.kind)
                if not r.max_durability:
                    r.max_durability = 100
                    r.durability = 100
            else:
                # 非装备不给耐久
                r.durability = 0
                r.max_durability = 0
            s.add(r)
            n += 1
        s.commit()
        print("migrated %d items" % n)


if __name__ == "__main__":
    main()
''', encoding="utf-8")
print("[write] tools/migrate_items.py")

# ============================================================
# 3. api.gd：use_item 带 target_type
# ============================================================
p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")

old_use = '''func use_item(item_id: String, target_npc_id: String) -> void:
	_item_request("POST", "/item/%s/use" % item_id, {"target_npc_id": target_npc_id}, "use")'''
new_use = '''func use_item(item_id: String, target_npc_id: String, target_type: String = "auto") -> void:
	_item_request("POST", "/item/%s/use" % item_id, {
		"target_npc_id": target_npc_id,
		"target_type": target_type,
	}, "use")'''
if old_use in t:
    t = t.replace(old_use, new_use, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] api.gd use_item 加 target_type")

# ============================================================
# 4. main.gd：使用弹窗改成 4 选 1
# ============================================================
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 4.1 _on_use_pressed 改成根据 category 弹窗
old_press = '''func _on_use_pressed() -> void:
	if current_item_id == "":
		return
	_show_target_picker("对谁使用？（可无目标）", func(target_id: String):
		api.use_item(current_item_id, target_id)
	)'''

new_press = '''func _on_use_pressed() -> void:
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
		item_detail.append_text("\\n\\n[color=gray]（这是材料/剧情物品，不能直接使用）[/color]")
		return

	if cat == "equipment":
		# 装备走装备流程（下一轮完整实现）
		item_detail.append_text("\\n\\n[color=gray]（装备系统下一轮实现，先占位）[/color]")
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

	popup.popup_centered(Vector2i(340, 220))'''

if old_press in t:
    t = t.replace(old_press, new_press, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] _on_use_pressed 按 category 分支")

# 4.2 物品详情：只对 equipment 显示耐久
t = p.read_text(encoding="utf-8")
old_dur = '''		# 耐久
		var dur: int = int(it.get("durability", 100))
		var max_dur: int = int(it.get("max_durability", 100))
		if max_dur > 0:
			var dcolor := "lightgreen"
			if dur <= max_dur * 0.3:
				dcolor = "red"
			elif dur <= max_dur * 0.6:
				dcolor = "yellow"
			lines.append("耐久：[color=%s]%d / %d[/color]" % [dcolor, dur, max_dur])'''
new_dur = '''		# 耐久（只对装备显示）
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
		var cat_label := {
			"consumable": "消耗品",
			"equipment": "装备",
			"material": "材料",
			"key": "钥匙",
			"quest": "剧情物品",
		}.get(cat, "材料")
		lines.append("类别：[color=cyan]%s[/color]" % cat_label)'''
if old_dur in t:
    t = t.replace(old_dur, new_dur, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 物品详情按类别显示")

print()
print("========== 全部完成 ==========")
print("运行：")
print("  python fix85a.py")
print("  python fix85b.py")
print("  python tools/migrate_items.py")
print("  pytest -v")
print("  uvicorn server.main:app")
print("Godot 完全关闭重开")