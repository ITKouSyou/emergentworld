"""效用 AI：NPC 独立 RNG + 目标驱动 + 时间偏好 + 关系牵引。"""

from __future__ import annotations

import hashlib
import random

from sqlmodel import Session

from server.core.world import load_npcs
from server.models.schemas import Action, NPC, World

DEFAULT_ACTIONS = [
    Action(id="eat", need="hunger", location_id="tavern"),
    Action(id="rest", need="safety", location_id="home"),
    Action(id="socialize", need="social", location_id="village_square"),
    Action(id="work", need="wealth", location_id="market"),
    Action(id="explore", need="curiosity", location_id="forest"),
]

# 每个行为的基座需求
ACTION_NEED = {a.id: a.need for a in DEFAULT_ACTIONS}

# 时间段偏好：hour → {action_id: bonus}
TIME_PREFS: dict[str, dict[str, float]] = {
    "morning":   {"work": 0.35, "explore": 0.1, "eat": 0.05},
    "noon":      {"eat": 0.35, "socialize": 0.15},
    "afternoon": {"work": 0.25, "socialize": 0.2, "explore": 0.15},
    "evening":   {"socialize": 0.3, "eat": 0.25, "explore": 0.1},
    "night":     {"rest": 0.5, "eat": 0.1},
}

# 目标关键词 → 行为
GOAL_KEYWORDS: dict[str, str] = {
    "钱": "work", "wealth": "work", "攒": "work", "生意": "work", "商": "work",
    "朋友": "socialize", "社交": "socialize", "关系": "socialize", "盟友": "socialize",
    "家": "rest", "安": "rest", "睡": "rest", "休息": "rest",
    "吃": "eat", "食": "eat", "饭": "eat",
    "探索": "explore", "寻": "explore", "冒险": "explore", "旅": "explore", "查": "explore",
}

# 地点容量：超过则想去的人会犹豫
LOCATION_CAPACITY: dict[str, int] = {
    "village_square": 6,
    "market": 4,
    "tavern": 4,
    "home": 8,
    "forest": 3,
    "village_edge": 3,
    "village_hall": 3,
}


def _npc_rng(world: World, npc_id: str) -> random.Random:
    h = int(hashlib.md5(npc_id.encode("utf-8")).hexdigest()[:8], 16)
    return random.Random(world.seed * 1000003 + world.tick * 31 + h)


def _time_slot(hour: int) -> str:
    if 6 <= hour < 11:
        return "morning"
    if 11 <= hour < 14:
        return "noon"
    if 14 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 22:
        return "evening"
    return "night"


def _goal_bonus(npc: NPC) -> dict[str, float]:
    """从 goals 文本里挖关键词，给对应行为加权。"""
    bonus: dict[str, float] = {a.id: 0.0 for a in DEFAULT_ACTIONS}
    for g in npc.goals:
        g_low = g.lower()
        for kw, action_id in GOAL_KEYWORDS.items():
            if kw in g or kw in g_low:
                bonus[action_id] = bonus.get(action_id, 0.0) + 0.15
    return bonus


def _crowd_penalty(session: Session, world: World, npc_id: str) -> dict[str, float]:
    """目标地点越挤，越不想去。"""
    npcs = load_npcs(session)
    by_loc: dict[str, int] = {}
    for n in npcs:
        if n.id == npc_id:
            continue
        by_loc[n.location_id] = by_loc.get(n.location_id, 0) + 1

    penalty: dict[str, float] = {}
    for action in DEFAULT_ACTIONS:
        if not action.location_id:
            penalty[action.id] = 0.0
            continue
        cap = LOCATION_CAPACITY.get(action.location_id, 5)
        cur = by_loc.get(action.location_id, 0)
        if cur >= cap:
            penalty[action.id] = -0.25
        elif cur >= cap - 1:
            penalty[action.id] = -0.1
        else:
            penalty[action.id] = 0.0
    return penalty


def _friendship_pull(session: Session, world: World, npc: NPC) -> dict[str, float]:
    """如果关系好的 NPC 在某地，倾向于过去（每个地点最多 +0.15）。"""
    from server.systems.relationship import list_relationships

    rels = list_relationships(session, npc.id)
    friend_ids: list[str] = []
    for r in rels:
        other = r.to_npc if r.from_npc == npc.id else r.from_npc
        score = r.trust + r.affection - r.fear
        if score > 0.25:
            friend_ids.append(other)
    if not friend_ids:
        return {a.id: 0.0 for a in DEFAULT_ACTIONS}

    friend_locs: dict[str, int] = {}
    for n in load_npcs(session):
        if n.id in friend_ids:
            friend_locs[n.location_id] = friend_locs.get(n.location_id, 0) + 1

    pull: dict[str, float] = {}
    for action in DEFAULT_ACTIONS:
        pull[action.id] = min(0.15, 0.06 * friend_locs.get(action.location_id or "", 0))
    return pull


def score_action(
    session: Session,
    world: World,
    npc: NPC,
    action: Action,
    goal_bonus: dict[str, float],
    time_bonus: dict[str, float],
    crowd_penalty: dict[str, float],
    friend_pull: dict[str, float],
) -> float:
    need_val = npc.needs.get(action.need, 0.5)
    weight = npc.behavior_profile.get(action.need, 0.5)

    base = need_val * weight * 1.4
    base += goal_bonus.get(action.id, 0.0)
    base += time_bonus.get(action.id, 0.0)
    base += crowd_penalty.get(action.id, 0.0)
    base += friend_pull.get(action.id, 0.0)

    # 家（休息）与安全需求相关，加一个小偏置
    if action.id == "rest":
        base += (npc.needs.get("safety", 0.5) - 0.5) * 0.2

    return base


def decide(session: Session, world: World, npc: NPC, rng: random.Random) -> Action:
    goal_bonus = _goal_bonus(npc)
    slot = _time_slot(world.hour)
    time_bonus = {a.id: TIME_PREFS.get(slot, {}).get(a.id, 0.0) for a in DEFAULT_ACTIONS}
    crowd_penalty = _crowd_penalty(session, world, npc.id)
    friend_pull = _friendship_pull(session, world, npc)

    scored: list[tuple[float, Action]] = []
    for a in DEFAULT_ACTIONS:
        s = score_action(session, world, npc, a, goal_bonus,
                         time_bonus, crowd_penalty, friend_pull)
        # 少量随机扰动，避免所有 NPC 同步
        s += rng.uniform(-0.05, 0.05)
        scored.append((s, a))

    scored.sort(key=lambda x: x[0], reverse=True)

    # 采样 top-2，避免完全确定
    top = scored[:2]
    return rng.choices([a for _, a in top],
                       weights=[max(s + 1.0, 0.01) for s, _ in top],
                       k=1)[0]


def step(session: Session, world: World) -> None:
    npcs = load_npcs(session)
    for npc in npcs:
        rng = _npc_rng(world, npc.id)
        action = decide(session, world, npc, rng)
        if action.location_id:
            npc.location_id = action.location_id
        # 需求变化：当前行为对应的需求下降，其它缓慢上升
        for k in npc.needs:
            delta = -0.06 if k == action.need else 0.02
            npc.needs[k] = max(0.0, min(1.0, npc.needs.get(k, 0.5) + delta))

    # 保存到数据库
    from server.core.world import save_npc
    for npc in npcs:
        save_npc(session, npc)
