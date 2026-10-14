# 1. accept 时检查当前位置
# 2. UI 按 kind 显示不同按钮
from pathlib import Path

# ============================================================
# 1. 后端：accept_quest 时立即检查完成
# ============================================================
p = Path("server/systems/quest.py")
t = p.read_text(encoding="utf-8")

old = '''    session.add(row)
    session.commit()
    return {"ok": True, "quest_id": row.id, "title": row.title}'''

new = '''    session.add(row)
    session.commit()

    # 立即检查：玩家是否已经在目标地点？
    from server.systems import player as player_sys
    player = player_sys.load_player(session)
    if player is not None and player.location_id == qdef["require_location"]:
        # 非 fetch 类直接完成
        if qdef["kind"] != "fetch":
            row.state = "completed"
            row.completed_tick = world.tick
            session.add(row)
            session.commit()
            _grant_reward(session, row)
            return {
                "ok": True,
                "quest_id": row.id,
                "title": row.title,
                "auto_completed": True,
            }

    return {"ok": True, "quest_id": row.id, "title": row.title}'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] accept_quest 检查当前位置")
else:
    print("[skip] 已改过或锚点未匹配")

# 顺便：abandon 时也检查状态，允许放弃 active 或 ready
t = p.read_text(encoding="utf-8")
old2 = '''def abandon_quest(session: Session, quest_id: str) -> dict:
    q = session.get(QuestRow, quest_id)
    if q is None:
        return {"ok": False, "error": "quest not found"}
    if q.state != "active":
        return {"ok": False, "error": "quest not active"}
    q.state = "abandoned"
    session.add(q)
    session.commit()
    return {"ok": True, "id": quest_id}'''

new2 = '''def abandon_quest(session: Session, quest_id: str) -> dict:
    q = session.get(QuestRow, quest_id)
    if q is None:
        return {"ok": False, "error": "quest not found"}
    if q.state not in ("active", "ready"):
        return {"ok": False, "error": "该任务已经%s，无法放弃" % (
            {"completed": "完成", "abandoned": "放弃", "failed": "失败"}.get(q.state, q.state)
        )}
    q.state = "abandoned"
    session.add(q)
    session.commit()
    return {"ok": True, "id": quest_id}'''

if old2 in t:
    t = t.replace(old2, new2, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] abandon_quest 允许放弃 ready")

# list_npc_active_quests 里非 fetch 类不显示"提交"
t = p.read_text(encoding="utf-8")
old3 = '''        result.append({
            "id": q.id,
            "title": q.title,
            "kind": q.kind,
            "require_item_kind": q.require_item_kind or "",
            "require_item_count": q.require_item_count,
            "reward_exp": q.reward_exp,
            "reward_money": q.reward_money,
            "ready": ready,
        })'''
new3 = '''        # 非 fetch 类不需要"提交"动作
        needs_turn_in = (q.kind == "fetch" and bool(q.require_item_kind))
        result.append({
            "id": q.id,
            "title": q.title,
            "kind": q.kind,
            "require_item_kind": q.require_item_kind or "",
            "require_item_count": q.require_item_count,
            "reward_exp": q.reward_exp,
            "reward_money": q.reward_money,
            "ready": ready,
            "needs_turn_in": needs_turn_in,
        })'''
if old3 in t:
    t = t.replace(old3, new3, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] active_quests 加 needs_turn_in")

# ============================================================
# 2. 前端：按 needs_turn_in 显示按钮
# ============================================================
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

old4 = '''			var info := RichTextLabel.new()
			info.bbcode_enabled = true
			info.fit_content = true
			info.custom_minimum_size = Vector2(0, 20)
			var title_s: String = str(q.get("title", "?"))
			var exp_r: int = int(q.get("reward_exp", 0))
			var money_r: int = int(q.get("reward_money", 0))
			var ready: bool = bool(q.get("ready", false))
			var rk: String = str(q.get("require_item_kind", ""))
			var rc: int = int(q.get("require_item_count", 0))

			var status := ""
			if rc > 0:
				if ready:
					status = "[color=green]（已集齐%s）[/color]" % rk
				else:
					status = "[color=gray]（还需%s×%d）[/color]" % [rk, rc]

			info.text = "%s  (%d经验,%d钱) %s" % [title_s, exp_r, money_r, status]
			info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			row.add_child(info)

			var btn := Button.new()
			btn.text = "提交"
			if not ready:
				btn.disabled = true
			var qid: String = str(q.get("id", ""))
			btn.pressed.connect(func(): _on_turn_in_pressed(qid))
			row.add_child(btn)
			npc_quests_panel.add_child(row)'''

new4 = '''			var info := RichTextLabel.new()
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

			npc_quests_panel.add_child(row)'''

if old4 in t:
    t = t.replace(old4, new4, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] NPC 面板按 needs_turn_in 显示不同按钮")
else:
    print("[skip] 锚点未找到")

print()
print("重启后端 + Godot 完全关闭重开")