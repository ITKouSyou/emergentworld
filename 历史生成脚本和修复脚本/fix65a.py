# Part 65A：NPC 对玩家的印象系统
from pathlib import Path

# ============================================================
# 1. schemas.py：NPC 加 impressions 字段
# ============================================================
p = Path("server/models/schemas.py")
t = p.read_text(encoding="utf-8")

if "impressions:" not in t:
    old = '''    schedule: dict[str, str] = Field(default_factory=dict)'''
    new = '''    schedule: dict[str, str] = Field(default_factory=dict)
    # 对玩家的印象：{ tag: count }，tag 如 "helped_child" / "betrayed_me"
    impressions: dict[str, int] = Field(default_factory=dict)'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] schemas.py NPC 加 impressions")
    else:
        print("[fail] schemas.py 锚点未找到")
else:
    print("[skip] schemas.py 已有 impressions")

# ============================================================
# 2. db.py：NPCRow 加 impressions_json
# ============================================================
p = Path("server/models/db.py")
t = p.read_text(encoding="utf-8")

if "impressions_json" not in t:
    old = '''    schedule_json: str = "{}"'''
    new = '''    schedule_json: str = "{}"
    impressions_json: str = "{}"'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] db.py NPCRow 加 impressions_json")
    else:
        print("[fail] db.py 锚点未找到")
else:
    print("[skip] db.py 已有 impressions_json")

# ============================================================
# 3. session.py：迁移
# ============================================================
p = Path("server/db/session.py")
t = p.read_text(encoding="utf-8")

if "impressions_json" not in t:
    anchor = '        _add_col(conn, "npc", "schedule_json", "schedule_json TEXT NOT NULL DEFAULT \'{}\'")\n'
    if anchor in t:
        t = t.replace(anchor, anchor + '        _add_col(conn, "npc", "impressions_json", "impressions_json TEXT NOT NULL DEFAULT \'{}\'")\n', 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] session.py 加 impressions_json 迁移")
    else:
        print("[skip] 迁移锚点未找到")
else:
    print("[skip] session.py 已有 impressions_json")

# ============================================================
# 4. world.py：读写 impressions
# ============================================================
p = Path("server/core/world.py")
t = p.read_text(encoding="utf-8")

if "impressions_json" not in t:
    old_save = '    row.schedule_json = dumps(npc.schedule)\n    session.add(row)'
    new_save = '    row.schedule_json = dumps(npc.schedule)\n    row.impressions_json = dumps(npc.impressions)\n    session.add(row)'
    if old_save in t:
        t = t.replace(old_save, new_save, 1)
        print("[fix] world.py save_npc 加 impressions")

    old_load = '''            family=Family(**fam_data) if fam_data else Family(),
            schedule=loads(r.schedule_json) or {},
        ))'''
    new_load = '''            family=Family(**fam_data) if fam_data else Family(),
            schedule=loads(r.schedule_json) or {},
            impressions=loads(r.impressions_json) or {},
        ))'''
    if old_load in t:
        t = t.replace(old_load, new_load, 1)
        print("[fix] world.py load_npcs 加 impressions")

    p.write_text(t, encoding="utf-8")
else:
    print("[skip] world.py 已有 impressions")

# ============================================================
# 5. 新文件：impression.py
# ============================================================
Path("server/systems/impression.py").write_text('''# NPC 对玩家的印象
from __future__ import annotations

from sqlmodel import Session

from server.models.db import NPCRow, dumps, loads

# 印象标签 → 中文描述
TAG_LABELS = {
    "helped_me": "帮过我",
    "saved_my_child": "救过我的孩子",
    "shared_trade": "和我做过生意",
    "gave_gift": "送过我东西",
    "betrayed_me": "坑过我",
    "refused_help": "拒绝过帮忙",
    "showed_courage": "在我面前勇敢过",
    "spread_rumor": "说过我坏话",
}

# 每种行动 → 对应的印象 tag
# 值可以是 str（固定）或 lambda（根据 choice 决定）
def tags_from_event(
    template_id: str,
    choice_id: str,
    roles: dict,
    npc_id: str,
) -> list[str]:
    """根据事件 + 选择 + 角色，推断这个 NPC 对玩家产生的印象。"""
    tags: list[str] = []

    if choice_id == "help":
        tags.append("helped_me")
    elif choice_id == "oppose":
        tags.append("betrayed_me")
    elif choice_id == "observe":
        # 静观其变不留下强烈印象
        return []

    # 特殊事件加成
    if template_id == "lost_child" and roles.get("child") == npc_id:
        if choice_id == "help":
            tags.append("saved_my_child")

    if template_id in ("bandit_raid", "wolves_at_night", "combat"):
        if choice_id == "help":
            tags.append("showed_courage")

    return tags


def add_impression(session: Session, npc_id: str, tag: str, count: int = 1) -> None:
    """给 NPC 加一条印象计数。"""
    row = session.get(NPCRow, npc_id)
    if row is None:
        return
    impr = loads(row.impressions_json) or {}
    impr[tag] = int(impr.get(tag, 0)) + count
    row.impressions_json = dumps(impr)
    session.add(row)
    session.commit()


def get_impressions(session: Session, npc_id: str) -> dict:
    row = session.get(NPCRow, npc_id)
    if row is None:
        return {}
    return loads(row.impressions_json) or {}


def describe_for_prompt(session: Session, npc_id: str, limit: int = 4) -> str:
    """把印象翻译成 LLM 易读的一句话。"""
    impr = get_impressions(session, npc_id)
    if not impr:
        return "（你对他还没有特别的印象）"

    # 按次数排序
    items = sorted(impr.items(), key=lambda kv: -kv[1])
    parts = []
    for tag, count in items[:limit]:
        label = TAG_LABELS.get(tag, tag)
        if count > 1:
            parts.append("%s（%d 次）" % (label, count))
        else:
            parts.append(label)
    return "，".join(parts)


def describe_for_ui(session: Session, npc_id: str) -> list[str]:
    """给前端显示用。"""
    impr = get_impressions(session, npc_id)
    if not impr:
        return []
    items = sorted(impr.items(), key=lambda kv: -kv[1])
    result = []
    for tag, count in items[:6]:
        label = TAG_LABELS.get(tag, tag)
        if count > 1:
            result.append("%s（%d 次）" % (label, count))
        else:
            result.append(label)
    return result


def decay_impressions(session: Session, npc_id: str, decay_ratio: float = 0.05) -> None:
    """长期未联系时印象会淡化。"""
    row = session.get(NPCRow, npc_id)
    if row is None:
        return
    impr = loads(row.impressions_json) or {}
    if not impr:
        return
    for k in list(impr.keys()):
        impr[k] = max(0, int(impr[k]) - int(impr[k] * decay_ratio + 0.5))
        if impr[k] <= 0:
            del impr[k]
    row.impressions_json = dumps(impr)
    session.add(row)
    session.commit()
''', encoding="utf-8")
print("[write] server/systems/impression.py")

# ============================================================
# 6. event_flow.py：resolve 时写印象
# ============================================================
p = Path("server/core/event_flow.py")
t = p.read_text(encoding="utf-8")

old = '''    # 更新事件
    payload["choice_made"] = choice_id'''

new = '''    # 写印象
    try:
        from server.systems import impression as impr_sys
        roles = payload.get("roles", {})
        for npc_id in event.participants:
            tags = impr_sys.tags_from_event(
                event.template_id, choice_id, roles, npc_id,
            )
            for tag in tags:
                impr_sys.add_impression(session, npc_id, tag, 1)
    except Exception as e:
        import traceback
        print("[event] 印象写入失败：%s" % e)
        traceback.print_exc()

    # 更新事件
    payload["choice_made"] = choice_id'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] event_flow resolve 写印象")
else:
    print("[skip] event_flow 已改过或锚点未匹配")

# ============================================================
# 7. dialogue.py：注入印象
# ============================================================
p = Path("server/generators/dialogue.py")
t = p.read_text(encoding="utf-8")

old2 = '''    prompt = load_prompt("dialogue.md").format(
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

new2 = '''    # 玩家给这个 NPC 留下的印象
    try:
        from server.systems import impression as impr_sys
        impression_text = impr_sys.describe_for_prompt(session, npc.id, limit=4)
    except Exception:
        impression_text = "（你对他还没有特别的印象）"

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
        impression=impression_text,
        memories="\\n".join("- " + m for m in mem_summaries) or "（没有特别的记忆）",
        player_input=player_input,
    )'''

if old2 in t:
    t = t.replace(old2, new2, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] dialogue.py 注入印象")
else:
    print("[skip] dialogue.py 已改过或锚点未匹配")

# ============================================================
# 8. dialogue.md：加 {impression} 占位符
# ============================================================
p = Path("server/prompts/dialogue.md")
t = p.read_text(encoding="utf-8")

if "{impression}" not in t:
    old3 = '''你与玩家的关系：
  {relation_desc}'''
    new3 = '''你与玩家的关系：
  {relation_desc}

你对玩家的印象（基于过去发生的事）：
  {impression}'''
    if old3 in t:
        t = t.replace(old3, new3, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] dialogue.md 加 impression 占位符")
    else:
        print("[fail] dialogue.md 锚点未找到")
else:
    print("[skip] dialogue.md 已有 impression")

# ============================================================
# 9. main.py：/npc 返回 impressions
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

old4 = '''        "family": family_info,
        "schedule": schedule_lines,
    }'''
new4 = '''        "family": family_info,
        "schedule": schedule_lines,
        "impressions": _impressions_for_ui(npc.id, session) if "session" in dir() else [],
    }'''
# 这段比较棘手，因为 _npc_to_display 没有 session 参数。改用更简单的方式。

# 撤回上面的改动（不改 _npc_to_display），改为在 /npc/{id} 里加 impressions
t = p.read_text(encoding="utf-8")
if "_impressions_for_ui" in t:
    # 撤销
    t = t.replace(new4, old4, 1)

# 加一个新的辅助函数
if "def _impressions_for_npc(" not in t:
    anchor = "def _npc_to_display("
    addition = '''def _impressions_for_npc(session, npc_id: str) -> list:
    try:
        from server.systems import impression as impr_sys
        return impr_sys.describe_for_ui(session, npc_id)
    except Exception:
        return []


def _npc_to_display('''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        print("[fix] main.py 加 _impressions_for_npc")

p.write_text(t, encoding="utf-8")

# 修改 get_npc 端点，附加 impressions
t = p.read_text(encoding="utf-8")
old5 = '''@app.get("/npc/{npc_id}")
def get_npc(npc_id: str) -> dict:
    with get_session() as s:
        all_npcs = load_npcs(s)
        names = {n.id: n.name for n in all_npcs}
        npcs = {n.id: n for n in all_npcs}
        if npc_id not in npcs:
            raise HTTPException(404, "npc not found")
        return _npc_to_display(npcs[npc_id], names)'''

new5 = '''@app.get("/npc/{npc_id}")
def get_npc(npc_id: str) -> dict:
    with get_session() as s:
        all_npcs = load_npcs(s)
        names = {n.id: n.name for n in all_npcs}
        npcs = {n.id: n for n in all_npcs}
        if npc_id not in npcs:
            raise HTTPException(404, "npc not found")
        result = _npc_to_display(npcs[npc_id], names)
        result["impressions"] = _impressions_for_npc(s, npc_id)
        return result'''

if old5 in t:
    t = t.replace(old5, new5, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] /npc/{id} 返回 impressions")
else:
    print("[skip] get_npc 已改过或锚点未匹配")

print()
print("A 完成。下一步 fix65b.py（前端）")