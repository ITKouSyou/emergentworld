# Part 33B：事件生成任务 + 玩家移动时检查完成 + 对话注入任务
from pathlib import Path

# ============================================================
# 1. event_flow.py：resolve 后生成任务
# ============================================================
p = Path("server/core/event_flow.py")
t = p.read_text(encoding="utf-8")

old = '''    row.state = "resolved"
    row.resolved_at = world.tick
    row.payload_json = dumps(payload)
    session.add(row)
    session.commit()

    save_world(session, world)

    return {
        "ok": True,
        "event_id": event_id,
        "choice_id": choice_id,
        "choice_label": choice_label,
        "outcome": outcome_text,
        "reward_id": reward_id,
        "item_id": item_id,
        "item_owner": item_owner,
    }'''

new = '''    row.state = "resolved"
    row.resolved_at = world.tick
    row.payload_json = dumps(payload)
    session.add(row)
    session.commit()

    # 生成任务
    quest_id = None
    try:
        from server.systems import quest as quest_sys
        from server.core.world import load_npcs as _load_npcs
        npc_names = {n.id: n.name for n in _load_npcs(session)}
        q = quest_sys.maybe_create_quest(
            session, world, event, event.template_id,
            event.participants, npc_names,
        )
        if q is not None:
            quest_id = q.id
    except Exception as e:
        import traceback
        print("[quest] 生成失败：%s" % e)
        traceback.print_exc()

    save_world(session, world)

    return {
        "ok": True,
        "event_id": event_id,
        "choice_id": choice_id,
        "choice_label": choice_label,
        "outcome": outcome_text,
        "reward_id": reward_id,
        "item_id": item_id,
        "item_owner": item_owner,
        "quest_id": quest_id,
    }'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] event_flow resolve 生成任务")
else:
    print("[skip] event_flow 已改过或锚点未匹配")

# ============================================================
# 2. main.py：/travel 时检查任务完成 + 加 /quest 端点
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

# 2.1 /travel 完成检查
old_travel = '''        save_world(s, world)
        p2 = player_sys.load_player(s)

        return {
            "ok": True,
            "from_id": old_loc,
            "from_label": i18n.location_label(old_loc),
            "to_id": req.location_id,
            "to_label": i18n.location_label(req.location_id),
            "player": _player_to_response(s, p2) if p2 else {},
            "tick": world.tick,
            "day": world.day,
            "hour": world.hour,
        }'''

new_travel = '''        # 检查任务完成
        completed_quests = []
        try:
            from server.systems import quest as quest_sys
            p_for_check = player_sys.load_player(s)
            if p_for_check is not None:
                completed_quests = quest_sys.check_location_completion(s, world, p_for_check)
        except Exception as e:
            import traceback
            print("[travel] 任务完成检查失败：%s" % e)
            traceback.print_exc()

        save_world(s, world)
        p2 = player_sys.load_player(s)

        return {
            "ok": True,
            "from_id": old_loc,
            "from_label": i18n.location_label(old_loc),
            "to_id": req.location_id,
            "to_label": i18n.location_label(req.location_id),
            "player": _player_to_response(s, p2) if p2 else {},
            "tick": world.tick,
            "day": world.day,
            "hour": world.hour,
            "completed_quests": completed_quests,
        }'''

if old_travel in t:
    t = t.replace(old_travel, new_travel, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] main.py /travel 检查任务完成")
else:
    print("[skip] /travel 已改过或未匹配")

# 2.2 /action 也检查（因为玩家可能在探索后到达新地点）
# 暂略，因为 explore 自己会变 location，需要单独处理

# 2.3 /quest 端点
if "/quest" in t:
    print("[skip] main.py 已有 /quest")
else:
    anchor = '''@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''
    addition = '''# ---------- Quests ----------

@app.get("/quest")
def quest_list(limit: int = 30) -> list[dict]:
    with get_session() as s:
        from server.systems import quest as quest_sys
        from server.core.world import load_npcs as _load_npcs
        npc_names = {n.id: n.name for n in _load_npcs(s)}
        rows = quest_sys.list_all(s, limit=limit)
        return [
            {
                "id": q.id,
                "title": q.title,
                "description": q.description,
                "kind": q.kind,
                "state": q.state,
                "progress": q.progress,
                "progress_target": q.progress_target,
                "giver_npc_id": q.giver_npc_id,
                "giver_name": npc_names.get(q.giver_npc_id, ""),
                "target_location_id": q.target_location_id,
                "target_location_label": i18n.location_label(q.target_location_id) if q.target_location_id else "",
                "reward_exp": q.reward_exp,
                "reward_money": q.reward_money,
                "created_tick": q.created_tick,
                "completed_tick": q.completed_tick,
            }
            for q in rows
        ]


class AbandonRequest(BaseModel):
    quest_id: str


@app.post("/quest/abandon")
def quest_abandon(req: AbandonRequest) -> dict:
    with get_session() as s:
        from server.systems import quest as quest_sys
        result = quest_sys.abandon_quest(s, req.quest_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "abandon failed"))
        return result


@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] main.py 加 /quest 端点")

# ============================================================
# 3. dialogue.py：注入任务上下文
# ============================================================
p = Path("server/generators/dialogue.py")
t = p.read_text(encoding="utf-8")

old_prompt = '''    # 该 NPC 最近参与的事件
    recent_events = _recent_events_for_npc(session, npc.id, limit=5)
    recent_text = "\\n".join(recent_events) or "（最近没有特别的事）"

    prompt = load_prompt("dialogue.md").format(
        name=npc.name,
        age=npc.age,
        traits=npc.traits,
        goals="，".join(npc.goals) or "（无明确目标）",
        location=npc.location_id,
        relation_desc=relation_desc,
        relationship_hint=relationship_hint,
        recent_events=recent_text,
        memories="\\n".join("- " + m for m in mem_summaries) or "（没有特别的记忆）",
        player_input=player_input,
    )'''

new_prompt = '''    # 该 NPC 最近参与的事件
    recent_events = _recent_events_for_npc(session, npc.id, limit=5)
    recent_text = "\\n".join(recent_events) or "（最近没有特别的事）"

    # 与这个 NPC 相关的进行中任务
    try:
        from server.systems import quest as quest_sys
        quest_lines = quest_sys.summarize_for_prompt(session, npc.id, limit=3)
    except Exception:
        quest_lines = []
    active_quests_text = "\\n".join(quest_lines) or "（没有未了的事）"

    prompt = load_prompt("dialogue.md").format(
        name=npc.name,
        age=npc.age,
        traits=npc.traits,
        goals="，".join(npc.goals) or "（无明确目标）",
        location=npc.location_id,
        relation_desc=relation_desc,
        relationship_hint=relationship_hint,
        recent_events=recent_text,
        active_quests=active_quests_text,
        memories="\\n".join("- " + m for m in mem_summaries) or "（没有特别的记忆）",
        player_input=player_input,
    )'''

if old_prompt in t:
    t = t.replace(old_prompt, new_prompt, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] dialogue.py 注入任务")
else:
    print("[skip] dialogue.py 已改过或未匹配")

# ============================================================
# 4. dialogue.md 加占位符
# ============================================================
p = Path("server/prompts/dialogue.md")
t = p.read_text(encoding="utf-8")

if "{active_quests}" not in t:
    old_md = '''你最近经历的事：
{recent_events}'''
    new_md = '''你最近经历的事：
{recent_events}

你身上未了的事（如果玩家问起，可以提起）：
{active_quests}'''
    if old_md in t:
        t = t.replace(old_md, new_md, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] dialogue.md 加 active_quests")
    else:
        print("[fail] dialogue.md 锚点未找到")
else:
    print("[skip] dialogue.md 已有 active_quests")

print()
print("B 完成。重启 uvicorn + Godot 完全关闭重开")