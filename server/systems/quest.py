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

    giver = participants[0] if participants else ""
    target = participants[1] if len(participants) > 1 else ""
    giver_name = npc_names.get(giver, "某人")

    title = rule["title"].format(
        target_npc=giver_name, giver_npc=giver_name
    )
    description = rule["description"].format(
        giver_npc=giver_name, target_npc=giver_name
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
    """玩家到达某地时，检查是否有任务可完成。返回刚完成的任务列表。"""
    completed: list[dict] = []
    active = list_active(session)
    for q in active:
        if not q.target_location_id:
            continue
        if q.target_location_id != player.location_id:
            continue
        # 到达目标地点 → 完成
        q.state = "completed"
        q.completed_tick = world.tick
        q.progress = q.progress_target
        session.add(q)
        session.commit()

        # 奖励
        pr = session.get(__import__("server.models.db", fromlist=["PlayerRow"]).PlayerRow, "player")
        if pr is not None:
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

        completed.append({
            "id": q.id,
            "title": q.title,
            "reward_exp": q.reward_exp,
            "reward_money": q.reward_money,
        })

        # 写 reward 记录
        try:
            from server.models.db import RewardRow, dumps
            rr = RewardRow(
                id="rwd_quest_%s" % uuid.uuid4().hex[:8],
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

    return completed


def abandon_quest(session: Session, quest_id: str) -> dict:
    q = session.get(QuestRow, quest_id)
    if q is None:
        return {"ok": False, "error": "quest not found"}
    if q.state != "active":
        return {"ok": False, "error": "quest not active"}
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
