"""玩家系统：创建、加载、升级、属性判定。"""

from __future__ import annotations

import random
from typing import Optional

from sqlmodel import Session

from server.models.db import PlayerRow, dumps, loads
from server.models.schemas import DEFAULT_ATTRIBUTES, Player

PLAYER_ID = "player"

# 升级所需经验公式：100 * level^1.5
def exp_for_level(level: int) -> int:
    return int(100 * (level ** 1.5))


# 每级获得 2 个可分配点
POINTS_PER_LEVEL = 2


def load_player(session: Session) -> Optional[Player]:
    row = session.get(PlayerRow, PLAYER_ID)
    if row is None:
        return None
    attrs = loads(row.attributes_json) or {}
    # 补全所有默认字段
    for k, v in DEFAULT_ATTRIBUTES.items():
        attrs.setdefault(k, v)
    return Player(
        id=row.id,
        name=row.name,
        gender=row.gender or "unknown",
        age=row.age,
        level=row.level,
        exp=row.exp,
        exp_next=row.exp_next,
        unspent_points=row.unspent_points,
        attributes=attrs,
        location_id=row.location_id,
        reputation=row.reputation,
        hp=row.hp,
        max_hp=row.max_hp,
        background=row.background or "",
        known_npcs=loads(row.known_npcs_json) or [],
        created=row.created,
    )


def save_player(session: Session, player: Player) -> None:
    row = session.get(PlayerRow, PLAYER_ID) or PlayerRow(id=PLAYER_ID)
    row.name = player.name
    row.gender = player.gender
    row.age = player.age
    row.level = player.level
    row.exp = player.exp
    row.exp_next = player.exp_next
    row.unspent_points = player.unspent_points
    row.attributes_json = dumps(player.attributes)
    row.location_id = player.location_id
    row.reputation = player.reputation
    row.hp = player.hp
    row.max_hp = player.max_hp
    row.background = player.background
    row.known_npcs_json = dumps(player.known_npcs)
    row.created = player.created
    session.add(row)
    session.commit()


def create_player(
    session: Session,
    name: str,
    gender: str = "unknown",
    background: str = "",
) -> Player:
    # 根据出身给一点初始属性偏移
    attrs = dict(DEFAULT_ATTRIBUTES)
    bonus_map = {
        "游历的行商": {"charisma": 2, "perception": 1},
        "山里来的猎户": {"strength": 1, "agility": 2},
        "读书人": {"intelligence": 2, "perception": 1},
        "流浪艺人": {"charisma": 2, "luck": 1},
        "逃荒的农夫": {"strength": 2, "agility": 1},
        "不明来历": {"luck": 2, "perception": 1},
    }
    for k, v in bonus_map.get(background, {}).items():
        attrs[k] = attrs.get(k, 5) + v

    player = Player(
        id=PLAYER_ID,
        name=name.strip() or "无名者",
        gender=gender,
        age=22,
        level=1,
        exp=0,
        exp_next=exp_for_level(1),
        unspent_points=0,
        attributes=attrs,
        location_id="village_square",
        reputation=0,
        hp=100,
        max_hp=100,
        background=background,
        known_npcs=[],
        created=True,
    )
    save_player(session, player)
    return player


def allocate_point(session: Session, attribute: str, count: int = 1) -> tuple[bool, str, Optional[Player]]:
    player = load_player(session)
    if player is None:
        return False, "player not created", None
    if attribute not in player.attributes:
        return False, "unknown attribute: %s" % attribute, None
    if player.unspent_points < count:
        return False, "not enough points (%d < %d)" % (player.unspent_points, count), None
    if player.attributes[attribute] + count > 20:
        return False, "attribute cap reached (20)", None

    player.attributes[attribute] += count
    player.unspent_points -= count
    save_player(session, player)
    return True, "", player


def add_exp(session: Session, amount: int) -> tuple[Player, bool]:
    """给玩家加经验，返回 (player, leveled_up)。"""
    player = load_player(session)
    if player is None:
        # 未创建时静默返回一个空玩家
        return Player(), False
    player.exp += amount
    leveled = False
    while player.exp >= player.exp_next:
        player.exp -= player.exp_next
        player.level += 1
        player.unspent_points += POINTS_PER_LEVEL
        player.exp_next = exp_for_level(player.level)
        player.max_hp += 10
        player.hp = player.max_hp
        leveled = True
    save_player(session, player)
    return player, leveled


def add_reputation(session: Session, amount: int) -> Player:
    player = load_player(session)
    if player is None:
        return Player()
    player.reputation = max(0, min(999, player.reputation + amount))
    save_player(session, player)
    return player


def learn_about_npc(session: Session, npc_id: str) -> None:
    player = load_player(session)
    if player is None:
        return
    if npc_id not in player.known_npcs:
        player.known_npcs.append(npc_id)
        save_player(session, player)


# ============================================================
# 属性判定
# ============================================================

DIFFICULTY = {
    "easy": 12,
    "normal": 15,
    "hard": 18,
    "heroic": 22,
}


def roll_check(
    player: Player,
    attribute: str,
    difficulty: str = "normal",
    rng: random.Random | None = None,
) -> dict:
    """属性判定：属性 + 1d10 vs 难度。

    返回 {result, roll, base, total, difficulty, margin}
        result: "success" | "partial" | "failure" | "critical"
    """
    rng = rng or random.Random()
    base = int(player.attributes.get(attribute, 5))
    roll = rng.randint(1, 10)
    total = base + roll
    threshold = DIFFICULTY.get(difficulty, 15)
    margin = total - threshold

    if roll == 10 and margin >= 0:
        result = "critical"
    elif margin >= 0:
        result = "success"
    elif margin >= -3:
        result = "partial"
    else:
        result = "failure"

    return {
        "result": result,
        "attribute": attribute,
        "roll": roll,
        "base": base,
        "total": total,
        "difficulty": difficulty,
        "threshold": threshold,
        "margin": margin,
    }
