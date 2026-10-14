# 任务系统：由事件生成，玩家完成
from __future__ import annotations

import uuid
from typing import Optional

from sqlmodel import Session, select

from server.models.db import QuestRow
from server.models.schemas import Player, World
from server.systems import player as player_sys


# 模板 → 任务生成规则
# 当这些模板的事件 resolve 时，自动生成一个任务
QUEST_RULES = {
    "lost_child": {
        "title": "寻找{target_npc}的孩子",
        "description": "{giver_npc}的孩子走失了。去森林或村庄边缘找找看。",
        "kind": "rescue",
        "target_location": "forest",
        "exp": 50,
        "money": 15,
    },
    "old_letter": {
        "title": "查明旧信的真相",
        "description": "{giver_npc}在旧物中翻出一封信。去村公所问问看。",
        "kind": "investigate",
        "target_location": "village_hall",
        "exp": 40,
        "money": 10,
    },
    "missing_person": {
        "title": "调查{giver_npc}提到的失踪者",
        "description": "村里有人失踪了。去森林边缘看看。",
        "kind": "investigate",
        "target_location": "village_edge",
        "exp": 45,
        "money": 12,
    },
    "stolen_harvest": {
        "title": "找出失窃的收成",
        "description": "{giver_npc}家的收成被偷了。去市场打听打听。",
        "kind": "investigate",
        "target_location": "market",
        "exp": 35,
        "money": 10,
    },
    "treasure_rumor": {
        "title": "追寻宝藏传闻",
        "description": "{giver_npc}听说某处藏有宝物。去古庙遗址看看。",
        "kind": "adventure",
        "target_location": "old_shrine",
        "exp": 60,
        "money": 20,
    },
}


# 可主动 offer 的任务模板
# 每个任务：条件 → 目标 → 奖励
OFFERABLE_QUESTS = [
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
    # 排除：已接过且未完成的（不管什么状态）
    from sqlmodel import select
    all_q = session.exec(
        select(QuestRow).where(QuestRow.giver_npc_id == npc_id)
    ).all()
    existing_keys = set()
    for q in all_q:
        existing_keys.add(q.kind + ":" + (q.target_location_id or ""))

    result = []
    for qdef in OFFERABLE_QUESTS:
        # 关系太低不发
        if rel_score < qdef["min_trust"] / 100.0:
            continue
        # 已有同类任务跳过
        key = qdef["kind"] + ":" + qdef["require_location"]
        if key in existing_keys:
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
        require_item_kind=qdef.get("require_item_kind", ""),
        require_item_count=qdef.get("require_item_count", 0),
    )
    session.add(row)
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

    return {"ok": True, "quest_id": row.id, "title": row.title}


def _npc_name(session: Session, npc_id: str) -> str:
    if not npc_id:
        return "某人"
    from server.core.world import load_npcs
    for n in load_npcs(session):
        if n.id == npc_id:
            return n.name
    return "某人"


def maybe_create_quest(
    session: Session,
    world: World,
    event,
    template_id: str,
    participants: list[str],
    npc_names: dict,
) -> Optional[QuestRow]:
    """事件 resolve 后，根据模板决定是否生成任务。"""
    rule = QUEST_RULES.get(template_id)
    if not rule:
        return None

    # 检查是否已有同源任务（避免重复）
    existing = session.exec(
        select(QuestRow)
        .where(QuestRow.source_event_id == event.id)
    ).all()
    if existing:
        return None

    # 优先用具体角色
    roles = event.payload.get("roles", {})
    giver = roles.get("mother_or_father") or (participants[0] if participants else "")
    target = roles.get("child") or (participants[1] if len(participants) > 1 else "")
    giver_name = npc_names.get(giver, "某人")
    target_name = npc_names.get(target, "")

    if target_name and "寻找" in rule["title"]:
        title = "寻找%s的孩子（%s）" % (giver_name, target_name)
    else:
        title = rule["title"].format(
            target_npc=target_name or giver_name,
            giver_npc=giver_name,
        )
    description = rule["description"].format(
        giver_npc=giver_name,
        target_npc=target_name or giver_name,
    )

    row = QuestRow(
        id="quest_%s" % uuid.uuid4().hex[:8],
        title=title,
        description=description,
        kind=rule["kind"],
        giver_npc_id=giver,
        target_npc_id=target,
        target_location_id=rule["target_location"],
        state="active",
        progress=0,
        progress_target=1,
        reward_exp=rule["exp"],
        reward_money=rule["money"],
        source_event_id=event.id,
        created_tick=world.tick,
    )
    session.add(row)
    session.commit()
    print("[quest] 生成任务：%s (source=%s)" % (title, event.id))
    return row


def list_active(session: Session) -> list[QuestRow]:
    rows = session.exec(
        select(QuestRow).where(QuestRow.state == "active")
    ).all()
    return list(rows)


def list_all(session: Session, limit: int = 20) -> list[QuestRow]:
    rows = session.exec(
        select(QuestRow).order_by(QuestRow.created_tick.desc()).limit(limit)
    ).all()
    return list(rows)


def check_location_completion(
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

        # 非 fetch 类不需要"提交"动作
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
        })
    return result



def abandon_quest(session: Session, quest_id: str) -> dict:
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
    return {"ok": True, "id": quest_id}


def quests_for_npc(session: Session, npc_id: str) -> list[QuestRow]:
    """某 NPC 相关的任务（作为委托人或目标）。"""
    rows = session.exec(
        select(QuestRow)
        .where(QuestRow.state == "active")
    ).all()
    result = []
    for q in rows:
        if q.giver_npc_id == npc_id or q.target_npc_id == npc_id:
            result.append(q)
    return result


def summarize_for_prompt(session: Session, npc_id: str, limit: int = 3) -> list[str]:
    qs = quests_for_npc(session, npc_id)
    lines = []
    for q in qs[:limit]:
        role = "委托你" if q.giver_npc_id == npc_id else "牵涉到"
        lines.append("- 你%s的事：%s" % (role, q.title))
    return lines
