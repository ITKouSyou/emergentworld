# Part 98A：任务两阶段（进行中 / 待提交 / 已完成）
from pathlib import Path

# ============================================================
# 1. db.py：QuestRow 加字段
# ============================================================
p = Path("server/models/db.py")
t = p.read_text(encoding="utf-8")

if "require_item_kind" not in t:
    old = '''    created_tick: int = 0
    deadline_tick: int = 0
    completed_tick: int = 0'''
    new = '''    created_tick: int = 0
    deadline_tick: int = 0
    completed_tick: int = 0
    require_item_kind: str = ""
    require_item_count: int = 0'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] db.py QuestRow 加 require_item 字段")

# ============================================================
# 2. session.py：迁移
# ============================================================
p = Path("server/db/session.py")
t = p.read_text(encoding="utf-8")

if "require_item_kind" not in t:
    anchor = '        _add_col(conn, "item", "attributes_json", "attributes_json TEXT NOT NULL DEFAULT \'{}\'")\n'
    if anchor in t:
        add = (
            '        _add_col(conn, "quest", "require_item_kind", "require_item_kind TEXT NOT NULL DEFAULT \'\'")\n'
            + '        _add_col(conn, "quest", "require_item_count", "require_item_count INTEGER NOT NULL DEFAULT 0")\n'
        )
        t = t.replace(anchor, anchor + add, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] session.py 加 quest 字段迁移")

# ============================================================
# 3. quest.py：重写 OFFERABLE_QUESTS + 逻辑
# ============================================================
p = Path("server/systems/quest.py")
t = p.read_text(encoding="utf-8")

# 替换 OFFERABLE_QUESTS
old = '''OFFERABLE_QUESTS = [
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
]'''

new = '''OFFERABLE_QUESTS = [
    {
        "id": "fetch_herb",
        "title": "采些草药回来",
        "description": "我需要几味草药。去森林或小溪边采些回来。",
        "kind": "fetch",
        "require_location": "forest",
        "require_item_kind": "草药",
        "require_item_count": 1,
        "reward_exp": 30,
        "reward_money": 8,
        "min_trust": -30,
    },
    {
        "id": "gather_firewood",
        "title": "帮我带些柴火",
        "description": "家里柴火快用完了。村边或牧场都能捡到。",
        "kind": "fetch",
        "require_location": "village_edge",
        "require_item_kind": "燃料",
        "require_item_count": 1,
        "reward_exp": 20,
        "reward_money": 4,
        "min_trust": -30,
    },
    {
        "id": "fetch_ore",
        "title": "采两块矿石来",
        "description": "铁匠铺要打件东西，缺矿石。矿洞和采石场都能采到。",
        "kind": "fetch",
        "require_location": "old_mine",
        "require_item_kind": "矿石",
        "require_item_count": 2,
        "reward_exp": 40,
        "reward_money": 12,
        "min_trust": -10,
    },
    {
        "id": "deliver_letter",
        "title": "帮我送封信",
        "description": "这封信请交给市场上的人。别拆开。",
        "kind": "deliver",
        "require_location": "market",
        "require_item_kind": "",
        "require_item_count": 0,
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
        "require_item_kind": "",
        "require_item_count": 0,
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
        "require_item_kind": "",
        "require_item_count": 0,
        "reward_exp": 35,
        "reward_money": 10,
        "min_trust": -10,
    },
]'''
if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] quest.py OFFERABLE_QUESTS 加物品要求")

# accept_quest 加 require_item 字段
t = p.read_text(encoding="utf-8")
old2 = '''    row = QuestRow(
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
    )'''
new2 = '''    row = QuestRow(
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
        require_item_kind=qdef.get("require_item_kind", ""),
        require_item_count=qdef.get("require_item_count", 0),
    )'''
if old2 in t:
    t = t.replace(old2, new2, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] accept_quest 存 require_item")

# 重写 check_location_completion：fetch 类只标记 ready，不完成
t = p.read_text(encoding="utf-8")
start = t.find("def check_location_completion(")
if start >= 0:
    end = t.find("\n\ndef ", start + 1)
    if end < 0:
        end = len(t)

    new_func = '''def check_location_completion(
    session: Session,
    world: World,
    player: Player,
) -> list[dict]:
    """玩家到达某地时检查。

    - fetch 类：只是标记 "已到地点"，不完成
    - 其它：到达即完成
    """
    completed: list[dict] = []
    active = list_active(session)
    for q in active:
        if not q.target_location_id:
            continue
        if q.target_location_id != player.location_id:
            continue

        if q.kind == "fetch" and q.require_item_kind:
            # 采集类：只是提示"到达目的地"，不完成
            # 玩家需要拿到物品后回到委托人处提交
            continue

        # 其它类：到达即完成
        q.state = "completed"
        q.completed_tick = world.tick
        q.progress = q.progress_target
        session.add(q)
        session.commit()

        _grant_reward(session, q)
        completed.append({
            "id": q.id,
            "title": q.title,
            "reward_exp": q.reward_exp,
            "reward_money": q.reward_money,
        })
    return completed


def _grant_reward(session: Session, q: QuestRow) -> None:
    """发放任务奖励。"""
    from server.models.db import PlayerRow, RewardRow, dumps
    import uuid as _uuid

    pr = session.get(PlayerRow, "player")
    if pr is None:
        return

    if q.reward_exp > 0:
        pr.exp = (pr.exp or 0) + q.reward_exp
        while pr.exp >= pr.exp_next:
            pr.exp -= pr.exp_next
            pr.level += 1
            pr.unspent_points = (pr.unspent_points or 0) + 2
            pr.exp_next = player_sys.exp_for_level(pr.level)
            pr.max_hp = (pr.max_hp or 100) + 10
            pr.hp = pr.max_hp
    if q.reward_money > 0:
        pr.money = (pr.money or 0) + q.reward_money
    session.add(pr)
    session.commit()

    # reward 记录
    try:
        rr = RewardRow(
            id="rwd_quest_%s" % _uuid.uuid4().hex[:8],
            event_id="",
            kind="story",
            value=float(q.reward_money or q.reward_exp),
            description="完成任务：%s（经验 +%d，铜钱 +%d）" % (
                q.title, q.reward_exp, q.reward_money),
            payload_json=dumps({"quest_id": q.id, "source": "quest"}),
        )
        session.add(rr)
        session.commit()
    except Exception as e:
        print("[quest] reward 记录失败：%s" % e)


def check_ready_to_turn_in(session: Session, player: Player) -> None:
    """检查 fetch 类任务是否已集齐物品 → 变 ready_to_turn_in。"""
    from server.models.db import ItemRow
    from sqlmodel import select

    active = list_active(session)
    for q in active:
        if q.kind != "fetch" or not q.require_item_kind:
            continue

        # 检查玩家背包
        rows = session.exec(
            select(ItemRow)
            .where(ItemRow.owner_id == "player")
            .where(ItemRow.kind == q.require_item_kind)
        ).all()
        have = sum(1 for r in rows if not r.consumed)

        if have >= q.require_item_count:
            # 变 ready 状态
            # 但 QuestRow 没有 ready 字段，用 progress
            if q.progress < 1:
                q.progress = 1
                session.add(q)
                session.commit()


def turn_in_quest(session: Session, world: World, quest_id: str) -> dict:
    """提交任务：扣物品 → 给奖励 → 完成。"""
    from server.models.db import ItemRow
    from sqlmodel import select

    q = session.get(QuestRow, quest_id)
    if q is None:
        return {"ok": False, "error": "quest not found"}
    if q.state not in ("active", "ready"):
        return {"ok": False, "error": "quest not active"}

    # fetch 类需要物品
    if q.kind == "fetch" and q.require_item_kind:
        rows = session.exec(
            select(ItemRow)
            .where(ItemRow.owner_id == "player")
            .where(ItemRow.kind == q.require_item_kind)
        ).all()
        avail = [r for r in rows if not r.consumed]
        if len(avail) < q.require_item_count:
            return {"ok": False, "error": "物品不足（需要 %d 个%s）" % (
                q.require_item_count, q.require_item_kind)}

        # 扣除
        for i in range(q.require_item_count):
            avail[i].consumed = True
            session.add(avail[i])
        session.commit()

    # 完成 + 发奖励
    q.state = "completed"
    q.completed_tick = world.tick
    session.add(q)
    session.commit()

    _grant_reward(session, q)
    return {
        "ok": True,
        "quest_id": q.id,
        "title": q.title,
        "reward_exp": q.reward_exp,
        "reward_money": q.reward_money,
    }


def list_npc_active_quests(session: Session, npc_id: str) -> list[dict]:
    """该 NPC 名下正在进行中的任务（用于前端显示"提交"按钮）。"""
    from sqlmodel import select
    rows = session.exec(
        select(QuestRow)
        .where(QuestRow.giver_npc_id == npc_id)
        .where(QuestRow.state.in_(["active", "ready"]))
    ).all()

    result = []
    for q in rows:
        # 检查是否 ready
        ready = False
        if q.kind == "fetch" and q.require_item_kind:
            from server.models.db import ItemRow
            items = session.exec(
                select(ItemRow)
                .where(ItemRow.owner_id == "player")
                .where(ItemRow.kind == q.require_item_kind)
            ).all()
            have = sum(1 for r in items if not r.consumed)
            ready = have >= q.require_item_count

        result.append({
            "id": q.id,
            "title": q.title,
            "kind": q.kind,
            "require_item_kind": q.require_item_kind or "",
            "require_item_count": q.require_item_count,
            "reward_exp": q.reward_exp,
            "reward_money": q.reward_money,
            "ready": ready,
        })
    return result

'''
    t = t[:start] + new_func + t[end:]
    p.write_text(t, encoding="utf-8")
    print("[fix] quest.py check_location_completion + turn_in_quest")

# 修改 get_offerable_quests：排除已完成
t = p.read_text(encoding="utf-8")
old3 = '''    existing_ids = set()
    for q in list_active(session):
        if q.giver_npc_id == npc_id:
            existing_ids.add(q.kind + ":" + q.target_location_id)'''
new3 = '''    # 排除：已接过且未完成的（不管什么状态）
    from sqlmodel import select
    all_q = session.exec(
        select(QuestRow).where(QuestRow.giver_npc_id == npc_id)
    ).all()
    existing_keys = set()
    for q in all_q:
        existing_keys.add(q.kind + ":" + (q.target_location_id or ""))'''
if old3 in t:
    t = t.replace(old3, new3, 1)
    print("[fix] get_offerable_quests 排除已接")

old4 = '''        # 已有同类任务跳过
        key = qdef["kind"] + ":" + qdef["require_location"]
        if key in existing_ids:
            continue'''
new4 = '''        # 已有同类任务跳过
        key = qdef["kind"] + ":" + qdef["require_location"]
        if key in existing_keys:
            continue'''
if old4 in t:
    t = t.replace(old4, new4, 1)
    print("[fix] get_offerable_quests 用 existing_keys")

p.write_text(t, encoding="utf-8")

# ============================================================
# 4. main.py：加 /quest/{id}/turn_in 端点 + /npc/{id}/active_quests
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

if "/turn_in" not in t:
    anchor = '''@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''
    addition = '''@app.post("/quest/{quest_id}/turn_in")
def quest_turn_in(quest_id: str) -> dict:
    with get_session() as s:
        world = load_world(s)
        from server.systems import quest as quest_sys
        result = quest_sys.turn_in_quest(s, world, quest_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "turn in failed"))
        # 返回更新后的 player
        p2 = player_sys.load_player(s)
        result["player"] = _player_to_response(s, p2) if p2 else {}
        return result


@app.get("/npc/{npc_id}/active_quests")
def npc_active_quests(npc_id: str) -> list[dict]:
    with get_session() as s:
        from server.systems import quest as quest_sys
        return quest_sys.list_npc_active_quests(s, npc_id)


@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] main.py 加 turn_in 端点")

# /travel 到达地点后也检查 ready
t = p.read_text(encoding="utf-8")
old5 = '''        # 检查任务完成
        completed_quests = []
        try:
            from server.systems import quest as quest_sys
            p_for_check = player_sys.load_player(s)
            if p_for_check is not None:
                completed_quests = quest_sys.check_location_completion(s, world, p_for_check)
        except Exception as e:
            import traceback
            print("[travel] 任务完成检查失败：%s" % e)
            traceback.print_exc()'''

new5 = '''        # 检查任务完成
        completed_quests = []
        try:
            from server.systems import quest as quest_sys
            p_for_check = player_sys.load_player(s)
            if p_for_check is not None:
                completed_quests = quest_sys.check_location_completion(s, world, p_for_check)
                quest_sys.check_ready_to_turn_in(s, p_for_check)
        except Exception as e:
            import traceback
            print("[travel] 任务完成检查失败：%s" % e)
            traceback.print_exc()'''
if old5 in t:
    t = t.replace(old5, new5, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] /travel 后检查 ready")

# /quest 返回加 ready / require_item
t = p.read_text(encoding="utf-8")
old6 = '''                "reward_exp": q.reward_exp,
                "reward_money": q.reward_money,
                "created_tick": q.created_tick,
                "completed_tick": q.completed_tick,'''
new6 = '''                "reward_exp": q.reward_exp,
                "reward_money": q.reward_money,
                "created_tick": q.created_tick,
                "completed_tick": q.completed_tick,
                "require_item_kind": getattr(q, "require_item_kind", "") or "",
                "require_item_count": getattr(q, "require_item_count", 0),'''
if old6 in t:
    t = t.replace(old6, new6, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] /quest 返回 require_item")

print()
print("A 完成。下一步 fix98b.py")