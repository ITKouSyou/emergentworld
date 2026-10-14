# Part 96A：可接取任务池
from pathlib import Path

# ============================================================
# 1. quest.py：加"可 offer"机制
# ============================================================
p = Path("server/systems/quest.py")
t = p.read_text(encoding="utf-8")

# 加 OFFERABLE 任务定义
if "OFFERABLE_QUESTS" not in t:
    anchor = "def _npc_name(session: Session, npc_id: str) -> str:"
    addition = '''# 可主动 offer 的任务模板
# 每个任务：条件 → 目标 → 奖励
OFFERABLE_QUESTS = [
    {
        "id": "fetch_herb",
        "title": "采些草药回来",
        "description": "我需要几味草药。去森林或小溪边采些回来。",
        "kind": "fetch",
        "require_location": "forest",
        "reward_exp": 30,
        "reward_money": 8,
        "min_trust": -30,
    },
    {
        "id": "deliver_letter",
        "title": "帮我送封信",
        "description": "这封信请交给市场上的人。别拆开。",
        "kind": "deliver",
        "require_location": "market",
        "reward_exp": 20,
        "reward_money": 5,
        "min_trust": -20,
    },
    {
        "id": "visit_elder",
        "title": "替我问候村公所的人",
        "description": "村公所那位老人最近身体不好，帮我去看看他。",
        "kind": "visit",
        "require_location": "village_hall",
        "reward_exp": 25,
        "reward_money": 6,
        "min_trust": -10,
    },
    {
        "id": "investigate_brook",
        "title": "看看小溪边的动静",
        "description": "我总觉得小溪边最近不对劲。你去看看。",
        "kind": "investigate",
        "require_location": "brook",
        "reward_exp": 35,
        "reward_money": 10,
        "min_trust": -10,
    },
    {
        "id": "gather_firewood",
        "title": "帮我带些柴火",
        "description": "家里柴火快用完了。村边或牧场都能捡到。",
        "kind": "fetch",
        "require_location": "village_edge",
        "reward_exp": 20,
        "reward_money": 4,
        "min_trust": -30,
    },
]


def get_offerable_quests(session: Session, npc_id: str) -> list[dict]:
    """返回这个 NPC 可以 offer 的任务。

    过滤规则：
      - NPC 和玩家关系不是太差
      - 玩家当前没有同 id 的 active 任务
      - NPC 不是 neutral 阵营（避免所有人都在发任务）
    """
    from server.models.db import NPCRow
    from server.systems import relationship as rel_sys

    npc_row = session.get(NPCRow, npc_id)
    if npc_row is None:
        return []

    # 检查 NPC 与玩家的关系
    rel = rel_sys.get_relation_to(session, npc_id, "player")
    rel_score = rel.trust + rel.affection * 0.5

    # 玩家现有任务
    existing_ids = set()
    for q in list_active(session):
        if q.giver_npc_id == npc_id:
            existing_ids.add(q.kind + ":" + q.target_location_id)

    result = []
    for qdef in OFFERABLE_QUESTS:
        # 关系太低不发
        if rel_score < qdef["min_trust"] / 100.0:
            continue
        # 已有同类任务跳过
        key = qdef["kind"] + ":" + qdef["require_location"]
        if key in existing_ids:
            continue
        result.append({
            "id": qdef["id"],
            "title": qdef["title"],
            "description": qdef["description"],
            "kind": qdef["kind"],
            "require_location": qdef["require_location"],
            "require_location_label": "",
            "reward_exp": qdef["reward_exp"],
            "reward_money": qdef["reward_money"],
        })
    return result


def accept_quest(
    session: Session,
    world,
    npc_id: str,
    quest_def_id: str,
) -> dict:
    """接受一个 offer 的任务。"""
    qdef = next((q for q in OFFERABLE_QUESTS if q["id"] == quest_def_id), None)
    if qdef is None:
        return {"ok": False, "error": "quest def not found"}

    # 检查是否重复
    for q in list_active(session):
        if q.giver_npc_id == npc_id and q.target_location_id == qdef["require_location"]:
            return {"ok": False, "error": "already active"}

    import uuid as _uuid
    row = QuestRow(
        id="quest_%s" % _uuid.uuid4().hex[:8],
        title=qdef["title"],
        description=qdef["description"],
        kind=qdef["kind"],
        giver_npc_id=npc_id,
        target_npc_id="",
        target_location_id=qdef["require_location"],
        state="active",
        progress=0,
        progress_target=1,
        reward_exp=qdef["reward_exp"],
        reward_money=qdef["reward_money"],
        source_event_id="",
        created_tick=world.tick,
    )
    session.add(row)
    session.commit()
    return {"ok": True, "quest_id": row.id, "title": row.title}


def _npc_name(session: Session, npc_id: str) -> str:'''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] quest.py 加 OFFERABLE_QUESTS")
    else:
        print("[fail] quest.py 锚点未找到")
else:
    print("[skip] quest.py 已改过")

# ============================================================
# 2. main.py：加 /npc/{id}/quests 和 /quest/accept 端点
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

if "/npc/{npc_id}/quests" not in t:
    anchor = '''@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''
    addition = '''@app.get("/npc/{npc_id}/quests")
def npc_offerable_quests(npc_id: str) -> list[dict]:
    with get_session() as s:
        from server.systems import quest as quest_sys
        items = quest_sys.get_offerable_quests(s, npc_id)
        # 补 location_label
        for it in items:
            it["require_location_label"] = i18n.location_label(it["require_location"])
        return items


class AcceptQuestRequest(BaseModel):
    quest_def_id: str


@app.post("/npc/{npc_id}/quests/accept")
def accept_quest_endpoint(npc_id: str, req: AcceptQuestRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        from server.systems import quest as quest_sys
        result = quest_sys.accept_quest(s, world, npc_id, req.quest_def_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "accept failed"))
        return result


@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] main.py 加任务 offer/accept 端点")

print()
print("A 完成。下一步 fix96b.py")