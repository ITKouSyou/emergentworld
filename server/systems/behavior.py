# 效用 AI + 日程驱动
from __future__ import annotations

import hashlib
import random

from sqlmodel import Session

from server.core.world import load_npcs
from server.models.schemas import Action, NPC, World
from server.systems import schedule as schedule_sys

DEFAULT_ACTIONS = [
    Action(id="eat", need="hunger", location_id="tavern"),
    Action(id="rest", need="safety", location_id="home"),
    Action(id="socialize", need="social", location_id="village_square"),
    Action(id="work", need="wealth", location_id="market"),
    Action(id="explore", need="curiosity", location_id="forest"),
]

TIME_PREFS: dict[str, dict[str, float]] = {
    "morning":   {"work": 0.35, "explore": 0.1, "eat": 0.05},
    "noon":      {"eat": 0.35, "socialize": 0.15},
    "afternoon": {"work": 0.25, "socialize": 0.2, "explore": 0.15},
    "evening":   {"socialize": 0.3, "eat": 0.25, "explore": 0.1},
    "night":     {"rest": 0.5, "eat": 0.1},
}

GOAL_KEYWORDS: dict[str, str] = {
    "钱": "work", "wealth": "work", "攒": "work", "生意": "work", "商": "work",
    "朋友": "socialize", "社交": "socialize", "关系": "socialize", "盟友": "socialize",
    "家": "rest", "安": "rest", "睡": "rest", "休息": "rest",
    "吃": "eat", "食": "eat", "饭": "eat",
    "探索": "explore", "寻": "explore", "冒险": "explore", "旅": "explore", "查": "explore",
}

LOCATION_CAPACITY: dict[str, int] = {
    "village_square": 6, "market": 4, "tavern": 4,
    "home": 8, "forest": 3, "village_edge": 3, "village_hall": 3,
}

# 偏离日程的概率（去别的地方做别的事）
STRAY_CHANCE = 0.15


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
    bonus: dict[str, float] = {a.id: 0.0 for a in DEFAULT_ACTIONS}
    for g in npc.goals:
        g_low = g.lower()
        for kw, action_id in GOAL_KEYWORDS.items():
            if kw in g or kw in g_low:
                bonus[action_id] = bonus.get(action_id, 0.0) + 0.15
    return bonus


def _crowd_penalty(session: Session, world: World, npc_id: str) -> dict[str, float]:
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


def _decide_by_schedule(
    session: Session,
    world: World,
    npc: NPC,
    rng: random.Random,
) -> str:
    """返回 NPC 该去的地点。日程优先，偶尔偏离。"""
    target = schedule_sys.target_location(npc, world.hour)
    # 偶尔偏离：临时去别的地方
    if rng.random() < STRAY_CHANCE and npc.schedule:
        pool = ["market", "tavern", "village_square", "forest", "home"]
        target = rng.choice(pool)
    return target


def _local_action(session: Session, world: World, npc: NPC, rng: random.Random) -> Action:
    """已到达目的地后，根据需求选个"此地能做的行为"。"""
    loc = npc.location_id
    # 该地点能做的行为
    candidates = [a for a in DEFAULT_ACTIONS if a.location_id == loc]
    if not candidates:
        # 该地点没有匹配行为，做"闲逛"
        return Action(id="idle", need="social", location_id=loc)

    scored: list[tuple[float, Action]] = []
    for a in candidates:
        need_val = npc.needs.get(a.need, 0.5)
        weight = npc.behavior_profile.get(a.need, 0.5)
        s = need_val * weight + rng.uniform(-0.05, 0.05)
        scored.append((s, a))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def step(session: Session, world: World) -> None:
    from server.core.world import save_npc

    npcs = load_npcs(session)
    for npc in npcs:
        rng = _npc_rng(world, npc.id)

        # 1. 先按日程决定该去哪
        target = _decide_by_schedule(session, world, npc, rng)

        # 2. 如果不在目标地点，移动过去（一步走完）
        if npc.location_id != target:
            npc.location_id = target
            # 移动时需求小幅上涨
            for k in npc.needs:
                npc.needs[k] = min(1.0, npc.needs.get(k, 0.5) + 0.01)
        else:
            # 3. 已在目的地，做本地行为
            action = _local_action(session, world, npc, rng)
            for k in npc.needs:
                delta = -0.06 if k == action.need else 0.02
                npc.needs[k] = max(0.0, min(1.0, npc.needs.get(k, 0.5) + delta))

        save_npc(session, npc)
