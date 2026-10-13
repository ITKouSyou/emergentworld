"""事件与玩家的相关性判定。

只有相关性足够高的事件，才进入"等待玩家抉择"状态；
其余事件自动结算，作为"消息"出现在编年史里。
"""

from __future__ import annotations

from sqlmodel import Session

from server.models.schemas import Event, EventTemplate, NPC, Player, World
from server.systems import relationship


RELEVANCE_THRESHOLD = 0.35

# 玩家与事件参与者的关系权重
REL_TRUST_WEIGHT = 0.20
REL_AFFECTION_WEIGHT = 0.15
REL_FEAR_WEIGHT = 0.10
REL_DEBT_WEIGHT = 0.10

# 玩家声誉阈值
REP_MODERATE = 30
REP_FAMOUS = 80

# 公开型 tag 加成
PUBLIC_TAGS = {"conflict", "combat", "political", "ritual", "plot", "mystery"}


def check_relevance(
    session: Session,
    event: Event,
    tpl: EventTemplate,
    world: World,
    player: Player,
    npcs: list[NPC],
) -> tuple[bool, float, dict]:
    """返回 (是否相关, 分数, 详情)。"""
    score = 0.0
    detail: dict[str, float] = {}

    # 1. 玩家与事件同地点
    if player.location_id == event.location_id:
        score += 0.25
        detail["same_location"] = 0.25

    # 2. 玩家与参与者关系
    rel_bonus = 0.0
    for pid in event.participants:
        rel = relationship.get_relation_to(session, pid, "player")
        if rel.trust > 0.3:
            rel_bonus += REL_TRUST_WEIGHT
        if rel.affection > 0.3:
            rel_bonus += REL_AFFECTION_WEIGHT
        if rel.fear > 0.4:
            rel_bonus += REL_FEAR_WEIGHT
        if rel.debt > 0.3:
            rel_bonus += REL_DEBT_WEIGHT
        # 认识的 NPC
        if pid in player.known_npcs:
            rel_bonus += 0.05
    rel_bonus = min(rel_bonus, 0.5)
    if rel_bonus > 0:
        score += rel_bonus
        detail["relationship"] = rel_bonus

    # 3. 玩家声誉
    if player.reputation >= REP_FAMOUS:
        score += 0.30
        detail["reputation"] = 0.30
    elif player.reputation >= REP_MODERATE:
        score += 0.15
        detail["reputation"] = 0.15

    # 4. 事件类型
    if any(tag in PUBLIC_TAGS for tag in tpl.tags):
        score += 0.10
        detail["public_tag"] = 0.10

    # 5. 玩家运气微调（-0.05 到 +0.05）
    luck_adj = (player.attributes.get("luck", 5) - 5) * 0.01
    if abs(luck_adj) > 0.001:
        score += luck_adj
        detail["luck"] = luck_adj

    # 6. 已知 NPC 是参与者时的加成
    known_in_event = sum(1 for p in event.participants if p in player.known_npcs)
    if known_in_event >= 2:
        score += 0.10
        detail["multiple_known"] = 0.10

    is_relevant = score >= RELEVANCE_THRESHOLD
    return is_relevant, score, detail
