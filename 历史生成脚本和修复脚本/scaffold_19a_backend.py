"""EmergentWorld Part 19A：玩家系统（后端）。

运行：
    python scaffold_19a_backend.py --force
"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

# ================================================================
# server/models/schemas.py
# ================================================================

FILES["server/models/schemas.py"] = r'''"""所有 Pydantic 数据模型。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


DEFAULT_ATTRIBUTES: dict[str, int] = {
    "strength": 5,
    "agility": 5,
    "intelligence": 5,
    "perception": 5,
    "charisma": 5,
    "luck": 5,
}

ATTRIBUTE_META: list[dict[str, str]] = [
    {"key": "strength", "label": "力量", "desc": "肉体对抗、搬运、战斗"},
    {"key": "agility", "label": "敏捷", "desc": "躲避、逃脱、潜行"},
    {"key": "intelligence", "label": "智慧", "desc": "推理、查证、计谋"},
    {"key": "perception", "label": "感知", "desc": "观察、听风、发现线索"},
    {"key": "charisma", "label": "魅力", "desc": "说服、社交、调解"},
    {"key": "luck", "label": "运气", "desc": "巧合、意外之财、逃过一劫"},
]


class Player(BaseModel):
    id: str = "player"
    name: str = "无名者"
    gender: str = "unknown"
    age: int = 22
    level: int = 1
    exp: int = 0
    exp_next: int = 100
    unspent_points: int = 0
    attributes: dict[str, int] = Field(default_factory=lambda: dict(DEFAULT_ATTRIBUTES))
    location_id: str = "village_square"
    reputation: int = 0
    hp: int = 100
    max_hp: int = 100
    background: str = ""
    known_npcs: list[str] = Field(default_factory=list)
    created: bool = False


class NPC(BaseModel):
    id: str
    name: str
    age: int = Field(ge=0, le=200)
    gender: str = "unknown"
    traits: dict[str, float] = Field(default_factory=dict)
    needs: dict[str, float] = Field(default_factory=dict)
    goals: list[str] = Field(default_factory=list)
    behavior_profile: dict[str, float] = Field(default_factory=dict)
    asset_params: dict[str, Any] = Field(default_factory=dict)
    memory_ids: list[str] = Field(default_factory=list)
    location_id: str = "village_square"
    alive: bool = True


class Memory(BaseModel):
    id: str
    npc_id: str
    event_id: str
    summary: str
    emotion: dict[str, float] = Field(default_factory=dict)
    timestamp: int
    embedding_id: str | None = None


class Relationship(BaseModel):
    id: str
    from_npc: str
    to_npc: str
    trust: float = 0.0
    affection: float = 0.0
    fear: float = 0.0
    debt: float = 0.0


EventState = Literal[
    "pending", "active", "awaiting_player",
    "resolved", "expired", "rejected",
]


class Event(BaseModel):
    id: str
    template_id: str
    participants: list[str] = Field(default_factory=list)
    location_id: str = "village_square"
    state: EventState = "pending"
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: int = 0
    resolved_at: int | None = None


class EventTemplate(BaseModel):
    id: str
    tags: list[str] = Field(default_factory=list)
    cooldown: int = 3
    weight: float = 1.0
    conditions: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    prompt: str = ""
    evaluator: dict[str, Any] = Field(default_factory=dict)
    interactive: bool = True


class Reward(BaseModel):
    id: str
    event_id: str
    kind: Literal["item", "relationship", "info", "reputation", "skill", "story"]
    value: float = Field(ge=0.0)
    description: str
    payload: dict[str, Any] = Field(default_factory=dict)


class Item(BaseModel):
    id: str
    name: str
    kind: str
    affixes: list[str] = Field(default_factory=list)
    story: str = ""
    value: float = 0.0


class Evaluation(BaseModel):
    id: str
    target_type: Literal["event", "npc", "reward", "template"]
    target_id: str
    passed: bool
    score: float | None = None
    errors: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class Chronicle(BaseModel):
    id: str
    title: str
    body: str
    from_tick: int = 0
    to_tick: int = 0
    created_at: int = 0


class DirectorState(BaseModel):
    tension: float = 0.2
    last_event_tick: int = -999
    event_history: list[str] = Field(default_factory=list)


class EconomyState(BaseModel):
    total_currency: float = 1000.0
    inflation: float = 1.0
    reward_budget_multiplier: float = 1.0


class World(BaseModel):
    id: str
    tick: int = 0
    day: int = 0
    hour: int = 0
    seed: int = 42
    season: str = "spring"
    weather: str = "clear"
    weather_changed_tick: int = 0
    last_social_tick: int = -999
    social_count_today: int = 0
    director: DirectorState = Field(default_factory=DirectorState)
    economy: EconomyState = Field(default_factory=EconomyState)
    location_ids: list[str] = Field(default_factory=lambda: ["village_square"])


class Action(BaseModel):
    id: str
    need: str
    location_id: str | None = None
    target_npc: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
'''

# ================================================================
# server/models/db.py
# ================================================================

FILES["server/models/db.py"] = r'''"""SQLModel 表定义。"""

from __future__ import annotations

import json
from typing import Any

from sqlmodel import Field, SQLModel


class WorldRow(SQLModel, table=True):
    __tablename__ = "world"
    id: str = Field(primary_key=True)
    tick: int = 0
    day: int = 0
    hour: int = 0
    seed: int = 42
    director_json: str = "{}"
    economy_json: str = "{}"
    location_ids_json: str = "[]"
    season: str = "spring"
    weather: str = "clear"
    weather_changed_tick: int = 0
    last_social_tick: int = -999
    social_count_today: int = 0


class PlayerRow(SQLModel, table=True):
    __tablename__ = "player"
    id: str = Field(primary_key=True)
    name: str = "无名者"
    gender: str = "unknown"
    age: int = 22
    level: int = 1
    exp: int = 0
    exp_next: int = 100
    unspent_points: int = 0
    attributes_json: str = "{}"
    location_id: str = "village_square"
    reputation: int = 0
    hp: int = 100
    max_hp: int = 100
    background: str = ""
    known_npcs_json: str = "[]"
    created: bool = False


class NPCRow(SQLModel, table=True):
    __tablename__ = "npc"
    id: str = Field(primary_key=True)
    name: str
    age: int = 0
    gender: str = "unknown"
    traits_json: str = "{}"
    needs_json: str = "{}"
    goals_json: str = "[]"
    behavior_json: str = "{}"
    asset_json: str = "{}"
    memory_ids_json: str = "[]"
    location_id: str = "village_square"
    alive: bool = True


class MemoryRow(SQLModel, table=True):
    __tablename__ = "memory"
    id: str = Field(primary_key=True)
    npc_id: str = Field(index=True)
    event_id: str = Field(index=True)
    summary: str = ""
    emotion_json: str = "{}"
    timestamp: int = 0
    embedding_id: str | None = None
    embedding_json: str = "[]"


class RelationshipRow(SQLModel, table=True):
    __tablename__ = "relationship"
    id: str = Field(primary_key=True)
    from_npc: str = Field(index=True)
    to_npc: str = Field(index=True)
    trust: float = 0.0
    affection: float = 0.0
    fear: float = 0.0
    debt: float = 0.0


class EventRow(SQLModel, table=True):
    __tablename__ = "event"
    id: str = Field(primary_key=True)
    template_id: str = Field(index=True)
    participants_json: str = "[]"
    location_id: str = "village_square"
    state: str = "pending"
    payload_json: str = "{}"
    created_at: int = 0
    resolved_at: int | None = None


class RewardRow(SQLModel, table=True):
    __tablename__ = "reward"
    id: str = Field(primary_key=True)
    event_id: str = Field(index=True)
    kind: str
    value: float = 0.0
    description: str = ""
    payload_json: str = "{}"


class ItemRow(SQLModel, table=True):
    __tablename__ = "item"
    id: str = Field(primary_key=True)
    reward_id: str = Field(index=True)
    event_id: str = Field(index=True)
    name: str = ""
    kind: str = ""
    affixes_json: str = "[]"
    story: str = ""
    value: float = 0.0
    owner_id: str = Field(default="", index=True)
    consumed: bool = False


class ItemUseRow(SQLModel, table=True):
    __tablename__ = "item_use"
    id: str = Field(primary_key=True)
    item_id: str = Field(index=True)
    user_id: str = ""
    target_npc_id: str = ""
    effect: str = ""
    consumed: bool = False
    timestamp: int = 0


class ChronicleRow(SQLModel, table=True):
    __tablename__ = "chronicle"
    id: str = Field(primary_key=True)
    title: str = ""
    body: str = ""
    from_tick: int = 0
    to_tick: int = 0
    created_at: int = 0


class EvaluationRow(SQLModel, table=True):
    __tablename__ = "evaluation"
    id: str = Field(primary_key=True)
    target_type: str = Field(index=True)
    target_id: str = Field(index=True)
    passed: bool = False
    score: float | None = None
    errors_json: str = "[]"
    raw_json: str = "{}"


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def loads(s: str) -> Any:
    return json.loads(s) if s else None
'''

# ================================================================
# server/systems/player.py
# ================================================================

FILES["server/systems/player.py"] = r'''"""玩家系统：创建、加载、升级、属性判定。"""

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
'''

# ================================================================
# server/systems/relevance.py
# ================================================================

FILES["server/systems/relevance.py"] = r'''"""事件与玩家的相关性判定。

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
'''

# ================================================================
# server/core/choices.py
# ================================================================

FILES["server/core/choices.py"] = r'''"""玩家对事件的三个选项：出手相助 / 静观其变 / 暗中阻挠。

每个选项关联一个属性判定，用玩家的属性值决定结果质量。
"""

from __future__ import annotations

from server.models.schemas import EventTemplate


# tag → 主要属性
TAG_TO_ATTRIBUTE: dict[str, str] = {
    "conflict": "strength",
    "combat": "strength",
    "survival": "agility",
    "social": "charisma",
    "romance": "charisma",
    "trade": "charisma",
    "mystery": "perception",
    "investigation": "intelligence",
    "plot": "intelligence",
    "political": "intelligence",
    "adventure": "agility",
    "daily": "perception",
    "celebration": "charisma",
    "ritual": "perception",
}


CHOICES: dict[str, dict] = {
    "help": {
        "id": "help",
        "label": "出手相助",
        "attribute": "charisma",       # 会被 tag 覆盖
        "difficulty": "normal",
        "tension_delta": -0.05,
        "relation_delta": {"trust": 0.12, "affection": 0.10},
        "reward_multiplier": 1.0,
        "exp_reward": 20,
    },
    "observe": {
        "id": "observe",
        "label": "静观其变",
        "attribute": "perception",
        "difficulty": "easy",
        "tension_delta": 0.0,
        "relation_delta": {},
        "reward_multiplier": 0.5,
        "exp_reward": 5,
    },
    "oppose": {
        "id": "oppose",
        "label": "暗中阻挠",
        "attribute": "agility",
        "difficulty": "hard",
        "tension_delta": 0.08,
        "relation_delta": {"trust": -0.15, "fear": 0.10, "affection": -0.08},
        "reward_multiplier": 1.2,
        "exp_reward": 25,
    },
}


LABEL_OVERRIDES: dict[str, dict[str, str]] = {
    "conflict":   {"help": "挺身而出", "observe": "作壁上观", "oppose": "站在强势一方"},
    "romance":    {"help": "乐见其成", "observe": "不置可否", "oppose": "从中作梗"},
    "investigation": {"help": "协助查案", "observe": "静观其变", "oppose": "隐瞒线索"},
    "trade":      {"help": "促成交易", "observe": "不插手", "oppose": "从中抬价"},
    "political":  {"help": "支持一方", "observe": "保持中立", "oppose": "暗中捣乱"},
    "survival":   {"help": "伸出援手", "observe": "先顾自己", "oppose": "趁乱取利"},
    "celebration": {"help": "共襄盛举", "observe": "远远看着", "oppose": "扫兴而去"},
    "mystery":    {"help": "追查到底", "observe": "按兵不动", "oppose": "掩盖痕迹"},
    "plot":       {"help": "卷入其中", "observe": "暂不表态", "oppose": "搅乱局势"},
    "adventure":  {"help": "结伴同行", "observe": "婉言谢绝", "oppose": "抢先一步"},
    "social":     {"help": "从中调解", "observe": "旁观不语", "oppose": "推波助澜"},
    "daily":      {"help": "帮一把手", "observe": "不闻不问", "oppose": "从中作梗"},
    "combat":     {"help": "并肩作战", "observe": "退到一旁", "oppose": "背后偷袭"},
}


def pick_attribute(tpl: EventTemplate, default: str) -> str:
    """根据模板的 tags 选择最合适的属性。"""
    for tag in tpl.tags:
        if tag in TAG_TO_ATTRIBUTE:
            return TAG_TO_ATTRIBUTE[tag]
    return default


def build_choices(tpl: EventTemplate) -> list[dict]:
    """生成玩家选项列表，并附带属性与难度。"""
    override: dict[str, str] = {}
    for tag in tpl.tags:
        if tag in LABEL_OVERRIDES:
            override = LABEL_OVERRIDES[tag]
            break

    result: list[dict] = []
    for cid in ("help", "observe", "oppose"):
        base = CHOICES[cid]
        attr = pick_attribute(tpl, base["attribute"])
        result.append({
            "id": cid,
            "label": override.get(cid, base["label"]),
            "attribute": attr,
            "attribute_label": _attr_label(attr),
            "difficulty": base["difficulty"],
        })
    return result


def get_choice_spec(choice_id: str) -> dict | None:
    return CHOICES.get(choice_id)


def _attr_label(key: str) -> str:
    from server.models.schemas import ATTRIBUTE_META
    for m in ATTRIBUTE_META:
        if m["key"] == key:
            return m["label"]
    return key
'''

# ================================================================
# server/prompts/event_resolve.md
# ================================================================

FILES["server/prompts/event_resolve.md"] = r'''你是游戏事件结算器。玩家对事件做出了选择，请生成结算文本。

**重要：所有输出必须使用简体中文。**

规则：
- 输出必须是合法 JSON：{{"outcome": "结算描述（1-2 句，不超过 60 字）", "epilogue": "后续影响暗示（可选，1 句）"}}
- 根据玩家的判定结果，语气要匹配：
  - 大成功（critical）：表现出色，众人赞服
  - 成功（success）：顺利解决
  - 勉强（partial）：有得有失，略有波折
  - 失败（failure）：搞砸了，有负面后果
- 不要输出 markdown，不要输出解释

原事件：{summary}
事件叙述：{narrative}
玩家名字：{player_name}
玩家选择：{choice_label}（{choice_id}）
判定属性：{attribute_label}（玩家 {attribute_value} + 骰子 {roll} = {total}，难度 {threshold}）
判定结果：{result}

请基于以上判定结果生成结算文本。
'''

# ================================================================
# server/prompts/event_fill.md
# ================================================================

FILES["server/prompts/event_fill.md"] = r'''你是游戏事件填充器。给定一个事件模板与世界上下文，生成事件细节。

**重要：所有输出必须使用简体中文，不要用英文。**

规则：
- 输出必须是合法 JSON
- 顶层键为 payload，payload 内含 summary 与 narrative
- summary：一句话概述，**必须提到所有参与者名字**，不超过 45 字
- narrative：2-4 句细节描述，写到**关键时刻停住**，制造悬念
- 如果玩家名字是"（未创建）"，narrative 里用"你"指代玩家，暗示玩家在场或即将卷入
- 如果玩家已有名字（如 {player_name}），可以自然地把玩家代入场景
- **必须使用参与者真实名字**（不要写"某人"、"一名 NPC"）
- 不要改变参与者与地点
- 不要输出 markdown

模板 ID：{template_id}
模板名称：{template_label}
模板提示：{prompt}
参与者（**请使用这些名字**）：{participants}
地点：{location}（{location_label}）
玩家：{player_name}（当前位置：{player_location}）
当前天数：{day}
'''

# ================================================================
# server/generators/event.py
# ================================================================

FILES["server/generators/event.py"] = r'''"""事件生成器：模板 + LLM 填充 + 规则兜底。"""

from __future__ import annotations

import random
import uuid

from server.generators.base import get_llm, load_prompt
from server.i18n import location_label, template_label
from server.models.schemas import Event, EventTemplate, NPC, Player, World


def _pick_participants(tpl: EventTemplate, npcs: list[NPC], rng: random.Random) -> list[str]:
    n = int(tpl.params.get("participant_count", 2))
    n = min(n, len(npcs))
    if n <= 0:
        return []
    return [npc.id for npc in rng.sample(npcs, n)]


def _fallback_payload(tpl: EventTemplate, location: str, participants: list[NPC]) -> dict:
    names = "、".join(p.name for p in participants) or "无人"
    loc_zh = location_label(location)
    tpl_zh = template_label(tpl.id)
    return {
        "summary": "在%s发生了%s，涉及%s。" % (loc_zh, tpl_zh, names),
        "narrative": "（LLM 未返回，使用模板兜底。）",
    }


async def fill_event(
    tpl: EventTemplate,
    world: World,
    npcs: list[NPC],
    rng: random.Random,
    player: Player | None = None,
) -> Event:
    participants_ids = _pick_participants(tpl, npcs, rng)
    participants = [n for n in npcs if n.id in participants_ids]
    location = tpl.params.get("location", "village_square")

    player_name = "（未创建）"
    player_loc = "（未知）"
    if player is not None and player.created:
        player_name = player.name
        player_loc = location_label(player.location_id)

    prompt = load_prompt("event_fill.md").format(
        template_id=tpl.id,
        template_label=template_label(tpl.id),
        prompt=tpl.prompt,
        participants=", ".join("%s(%s)" % (p.name, p.id) for p in participants) or "无",
        location=location,
        location_label=location_label(location),
        player_name=player_name,
        player_location=player_loc,
        day=world.day,
    )
    fallback = _fallback_payload(tpl, location, participants)

    payload = fallback
    try:
        raw = await get_llm().text_json(prompt)
        if isinstance(raw, dict):
            candidate = raw.get("payload") if "payload" in raw else raw
            if isinstance(candidate, dict) and candidate.get("summary"):
                payload = {
                    "summary": str(candidate.get("summary", ""))[:300],
                    "narrative": str(candidate.get("narrative", ""))[:800],
                }
    except Exception:
        payload = fallback

    return Event(
        id="evt_%s" % uuid.uuid4().hex[:8],
        template_id=tpl.id,
        participants=participants_ids,
        location_id=location,
        state="pending",
        payload=payload,
        created_at=world.tick,
    )
'''

# ================================================================
# server/core/event_flow.py
# ================================================================

FILES["server/core/event_flow.py"] = r'''"""事件流程：包含相关性判定 + 属性判定 + 玩家参与。

流程：
    1. Director 选模板
    2. Generator 生成事件
    3. 相关性判定：
        相关 → awaiting_player，等玩家抉择
        不相关 → 立即 resolved，作为"消息"
    4. 玩家选择后：
        属性判定 → 结果 quality
        LLM 根据 quality 生成结算文本
        应用奖励、经验、关系变化
"""

from __future__ import annotations

import random
from typing import Optional

from sqlmodel import Session, select

from server.core import director
from server.core.choices import build_choices, get_choice_spec
from server.core.evaluator import evaluate_event, evaluate_reward, log_evaluation
from server.core.world import load_npcs, save_event, save_world
from server.generators.base import get_llm, load_prompt
from server.generators.event import fill_event
from server.generators.reward import compute_budget, generate_reward
from server.models.db import EventRow, ItemRow, RewardRow, dumps
from server.models.schemas import Event, EventTemplate, Reward, World
from server.systems import player as player_sys
from server.systems import relationship
from server.systems.relevance import check_relevance

PLAYER_TIMEOUT_TICKS = 8
MAX_PENDING = 3


def _save_reward(session: Session, reward: Reward) -> None:
    row = RewardRow(
        id=reward.id,
        event_id=reward.event_id,
        kind=reward.kind,
        value=reward.value,
        description=reward.description,
        payload_json=dumps({k: v for k, v in reward.payload.items() if k != "item"}),
    )
    session.add(row)
    session.commit()


def _save_item(
    session: Session,
    reward_id: str,
    event_id: str,
    item_data: dict,
    owner_id: str,
) -> None:
    row = ItemRow(
        id=item_data["id"],
        reward_id=reward_id,
        event_id=event_id,
        name=item_data.get("name", ""),
        kind=item_data.get("kind", ""),
        affixes_json=dumps(item_data.get("affixes", [])),
        story=item_data.get("story", ""),
        value=float(item_data.get("value", 0.0)),
        owner_id=owner_id,
        consumed=False,
    )
    session.add(row)
    session.commit()


def _apply_initial_effects(
    session: Session,
    world: World,
    event: Event,
    tpl: EventTemplate,
    rng: random.Random,
) -> None:
    summary = event.payload.get("summary", "") or ("发生了 %s" % tpl.id)
    relationship.npc_effects_from_event(
        session=session,
        participants=event.participants,
        event_id=event.id,
        summary=summary,
        timestamp=world.tick,
        rng=rng,
    )
    relationship.apply_event_effects(
        session=session,
        participants=event.participants,
        tags=tpl.tags,
        rng=rng,
    )


def _pending_rows(session: Session) -> list[EventRow]:
    return list(session.exec(
        select(EventRow).where(EventRow.state == "awaiting_player")
    ).all())


def _resolve_item_owner(event: Event, choice_id: str, rng: random.Random) -> str:
    if choice_id == "oppose":
        return "player"
    if choice_id == "help":
        if event.participants:
            return event.participants[0]
        return ""
    if event.participants and rng.random() < 0.8:
        return rng.choice(event.participants)
    return "player"


async def _emit_reward_and_item(
    session: Session,
    world: World,
    event: Event,
    rng: random.Random,
    value_multiplier: float = 1.0,
    owner_hint: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    budget = compute_budget(event, world) * value_multiplier
    reward = await generate_reward(event, world)
    reward.value = min(reward.value * value_multiplier, 1.0)

    reward_ok, reward_errors = evaluate_reward(reward, budget)
    log_evaluation(session, "reward", reward.id, reward_ok, reward_errors)
    if not reward_ok:
        return None, None, None

    _save_reward(session, reward)
    reward_id = reward.id
    item_id = None
    item_owner = None

    item_data = reward.payload.get("item")
    if isinstance(item_data, dict) and item_data.get("id"):
        if owner_hint is None:
            item_owner = _resolve_item_owner(event, "observe", rng)
        else:
            item_owner = owner_hint
        _save_item(session, reward.id, event.id, item_data, item_owner)
        item_id = item_data["id"]

    return reward_id, item_id, item_owner


async def run_event_cycle(
    session: Session,
    world: World,
    templates: list[EventTemplate],
    force: bool = False,
) -> Optional[Event]:
    rng = random.Random(world.seed * 1000003 + world.tick)

    pending = _pending_rows(session)
    if len(pending) >= MAX_PENDING:
        return None

    if not force and not director.should_trigger(world, rng):
        return None

    npcs = load_npcs(session)
    if len(npcs) < 1:
        return None

    player = player_sys.load_player(session)
    pending_template_ids = {r.template_id for r in pending}

    tpl = director.pick_template(
        templates, world, npcs, rng,
        ignore_cooldown=force,
        pending_template_ids=pending_template_ids,
    )
    if tpl is None:
        if pending_template_ids:
            tpl = director.pick_template(
                templates, world, npcs, rng,
                ignore_cooldown=False,
                pending_template_ids=pending_template_ids,
                want_interactive=False,
            )
        if tpl is None:
            return None

    event = await fill_event(tpl, world, npcs, rng, player=player)
    event.payload["interactive"] = bool(tpl.interactive)

    npc_ids = {n.id for n in npcs}
    max_reward = float(tpl.evaluator.get("max_reward", 1.0)) if tpl.evaluator else 1.0
    ok, errors = evaluate_event(event, world, npc_ids, budget=max_reward)
    log_evaluation(session, "event", event.id, ok, errors)

    if not ok:
        event.state = "rejected"
        save_event(session, event)
        director.update_tension_after_event(world, event, tpl)
        save_world(session, world)
        return None

    # 相关性判定
    relevance_ok = False
    relevance_score = 0.0
    relevance_detail: dict = {}
    if tpl.interactive and player is not None:
        relevance_ok, relevance_score, relevance_detail = check_relevance(
            session, event, tpl, world, player, npcs,
        )

    event.payload["relevance_score"] = round(relevance_score, 3)
    event.payload["relevance_detail"] = relevance_detail

    # ============================================================
    # 分支 A：非交互 或 与玩家无关 → 消息，直接结算
    # ============================================================
    if (not tpl.interactive) or (not relevance_ok):
        event.state = "active"
        save_event(session, event)

        _apply_initial_effects(session, world, event, tpl, rng)

        reward_id, item_id, item_owner = await _emit_reward_and_item(
            session, world, event, rng, value_multiplier=1.0,
        )
        event.payload["reward_id"] = reward_id
        event.payload["item_id"] = item_id
        event.payload["item_owner"] = item_owner
        event.payload["as_message"] = True

        event.state = "resolved"
        event.resolved_at = world.tick
        save_event(session, event)

        director.update_tension_after_event(world, event, tpl)
        save_world(session, world)
        return event

    # ============================================================
    # 分支 B：与玩家相关 → 等待玩家抉择
    # ============================================================
    event.payload["choices"] = build_choices(tpl)
    event.payload["choice_made"] = None
    event.payload["tpl_tags"] = list(tpl.tags)
    event.payload["max_reward"] = max_reward
    event.payload["difficulty"] = 0.5
    event.payload["as_message"] = False

    event.state = "awaiting_player"
    save_event(session, event)

    _apply_initial_effects(session, world, event, tpl, rng)

    # 认识参与者
    if player is not None:
        for pid in event.participants:
            player_sys.learn_about_npc(session, pid)

    save_world(session, world)
    return event


async def _generate_outcome_text(
    event: Event,
    choice_id: str,
    choice_label: str,
    player,
    check: dict,
    attribute_label: str,
) -> str:
    prompt = load_prompt("event_resolve.md").format(
        summary=event.payload.get("summary", ""),
        narrative=event.payload.get("narrative", ""),
        player_name=player.name if player else "无名者",
        choice_id=choice_id,
        choice_label=choice_label,
        attribute_label=attribute_label,
        attribute_value=check["base"],
        roll=check["roll"],
        total=check["total"],
        threshold=check["threshold"],
        result=check["result"],
    )
    try:
        raw = await get_llm().text_json(prompt)
        if isinstance(raw, dict):
            outcome = str(raw.get("outcome", "")).strip()
            epilogue = str(raw.get("epilogue", "")).strip()
            if outcome:
                return (outcome + " " + epilogue).strip() if epilogue else outcome
    except Exception:
        pass
    # fallback
    result_zh = {
        "critical": "你出色地处理了此事。",
        "success": "你顺利处理了此事。",
        "partial": "此事勉强有了着落。",
        "failure": "你没能处理好此事。",
    }.get(check["result"], "")
    return "%s——%s%s" % (
        event.payload.get("summary", ""),
        choice_label,
        result_zh,
    )


async def resolve_event(
    session: Session,
    world: World,
    event_id: str,
    choice_id: str,
) -> dict:
    row = session.get(EventRow, event_id)
    if row is None:
        return {"ok": False, "error": "event not found"}
    if row.state != "awaiting_player":
        return {"ok": False, "error": "event not awaiting player (state=%s)" % row.state}

    spec = get_choice_spec(choice_id)
    if spec is None:
        return {"ok": False, "error": "unknown choice: %s" % choice_id}

    from server.models.db import loads as _loads

    payload = _loads(row.payload_json) or {}
    event = Event(
        id=row.id,
        template_id=row.template_id,
        participants=_loads(row.participants_json) or [],
        location_id=row.location_id,
        state="awaiting_player",  # type: ignore[arg-type]
        payload=payload,
        created_at=row.created_at,
        resolved_at=None,
    )

    rng = random.Random(world.seed * 100003 + world.tick)

    # 找 choice 的实际属性（可能被 tag 覆盖）
    choice_attribute = spec["attribute"]
    for c in payload.get("choices", []):
        if isinstance(c, dict) and c.get("id") == choice_id:
            choice_attribute = str(c.get("attribute", choice_attribute))
            break

    player = player_sys.load_player(session)
    if player is None:
        return {"ok": False, "error": "player not created"}

    # 属性判定
    check = player_sys.roll_check(player, choice_attribute, spec["difficulty"], rng)

    # 判定结果影响 relation delta 与 reward multiplier 的修正
    quality_mult = {
        "critical": 1.5,
        "success": 1.0,
        "partial": 0.6,
        "failure": -0.5,
    }.get(check["result"], 1.0)

    # 显示用的中文标签
    from server.core.choices import _attr_label
    attribute_label = _attr_label(choice_attribute)

    # 生成结算文本
    choice_label = spec["label"]
    for c in payload.get("choices", []):
        if isinstance(c, dict) and c.get("id") == choice_id:
            choice_label = str(c.get("label", choice_label))
            break

    outcome_text = await _generate_outcome_text(
        event, choice_id, choice_label, player, check, attribute_label,
    )

    # 关系变化
    for npc_id in event.participants:
        delta = spec["relation_delta"]
        mult = 1.0 if quality_mult > 0 else 0.5
        relationship.adjust(
            session,
            from_npc=npc_id,
            to_npc="player",
            trust=float(delta.get("trust", 0.0)) * mult,
            affection=float(delta.get("affection", 0.0)) * mult,
            fear=float(delta.get("fear", 0.0)) * mult,
            debt=float(delta.get("debt", 0.0)) * mult,
        )

    # 张力
    world.director.tension = max(
        0.0,
        min(1.0, world.director.tension + float(spec["tension_delta"])),
    )

    # 奖励（除 observe 外，即使失败也可能有部分收获）
    reward_id = None
    item_id = None
    item_owner = None
    if choice_id != "observe":
        value_mult = float(spec["reward_multiplier"]) * max(0.2, quality_mult)
        owner_hint = _resolve_item_owner(event, choice_id, rng)
        reward_id, item_id, item_owner = await _emit_reward_and_item(
            session, world, event, rng,
            value_multiplier=value_mult,
            owner_hint=owner_hint,
        )

    # 经验与声望
    exp_gain = int(spec["exp_reward"] * max(0.2, quality_mult))
    if exp_gain > 0:
        player_after, leveled = player_sys.add_exp(session, exp_gain)
    else:
        player_after, leveled = player, False

    rep_gain = 0
    if check["result"] in ("critical", "success"):
        rep_gain = 3 if check["result"] == "success" else 6
        player_sys.add_reputation(session, rep_gain)
    elif check["result"] == "failure":
        player_sys.add_reputation(session, -1)

    # 更新事件
    payload["choice_made"] = choice_id
    payload["choice_label"] = choice_label
    payload["outcome"] = outcome_text
    payload["reward_id"] = reward_id
    payload["item_id"] = item_id
    payload["item_owner"] = item_owner
    payload["check"] = check
    payload["exp_gain"] = exp_gain
    payload["rep_gain"] = rep_gain

    row.state = "resolved"
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
        "check": check,
        "exp_gain": exp_gain,
        "rep_gain": rep_gain,
        "leveled_up": leveled,
        "new_level": player_after.level,
        "reward_id": reward_id,
        "item_id": item_id,
        "item_owner": item_owner,
    }


async def check_timeouts(session: Session, world: World) -> int:
    from server.models.db import loads as _loads

    rows = session.exec(
        select(EventRow).where(EventRow.state == "awaiting_player")
    ).all()

    count = 0
    for row in rows:
        if world.tick - row.created_at < PLAYER_TIMEOUT_TICKS:
            continue
        try:
            payload = _loads(row.payload_json) or {}
            payload["choice_made"] = "observe"
            payload["choice_label"] = "静观其变（超时）"
            payload["outcome"] = "%s——你没有介入，事件自行落幕。" % (
                payload.get("summary", "事件")
            )
            payload["timeout"] = True
            row.state = "expired"
            row.resolved_at = world.tick
            row.payload_json = dumps(payload)
            session.add(row)
            count += 1
        except Exception:
            continue

    if count:
        session.commit()
    return count
'''

# ================================================================
# server/main.py
# ================================================================

FILES["server/main.py"] = r'''"""FastAPI 入口。"""

from __future__ import annotations

import random
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, select

from server import i18n
from server.api import routes_dialogue, routes_review
from server.config import settings
from server.core import director
from server.core.event_flow import check_timeouts, resolve_event, run_event_cycle
from server.core.map_view import build_map_data
from server.core.tick import tick
from server.core.world import load_npcs, load_world, save_world
from server.db.session import engine, ensure_schema
from server.models.db import EventRow, ItemRow, MemoryRow, RewardRow, dumps, loads
from server.models.schemas import (
    ATTRIBUTE_META, DEFAULT_ATTRIBUTES, Event, NPC, Player, Reward, World,
)
from server.systems import inventory, item_use, relationship
from server.systems import player as player_sys
from server.systems.chronicle import generate_chronicle, list_chronicles
from server.systems.embedding import get_embedding, serialize
from server.systems.social import maybe_social_dialogue


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    ensure_schema()
    with Session(engine) as session:
        load_world(session)
    yield


app = FastAPI(title="EmergentWorld", lifespan=lifespan)
app.include_router(routes_dialogue.router)
app.include_router(routes_review.router)


def get_session() -> Session:
    return Session(engine)


@app.get("/")
def root() -> dict:
    return {
        "name": "EmergentWorld",
        "version": "1.1.0",
        "docs": "/docs",
        "embedding_enabled": settings.embedding_enabled,
    }


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/i18n")
def i18n_endpoint() -> dict:
    return i18n.all_labels()


# ---------- Player ----------

@app.get("/player/attributes")
def get_attribute_defs() -> dict:
    return {"attributes": ATTRIBUTE_META, "defaults": DEFAULT_ATTRIBUTES}


@app.get("/player")
def get_player() -> dict:
    with get_session() as s:
        p = player_sys.load_player(s)
        if p is None:
            return {"created": False}
        return p.model_dump()


class CreatePlayerRequest(BaseModel):
    name: str
    gender: str = "unknown"
    background: str = ""


@app.post("/player")
def create_player_endpoint(req: CreatePlayerRequest) -> dict:
    with get_session() as s:
        existing = player_sys.load_player(s)
        if existing is not None and existing.created:
            raise HTTPException(400, "player already created")
        p = player_sys.create_player(
            s, name=req.name, gender=req.gender, background=req.background,
        )
        return p.model_dump()


class AllocateRequest(BaseModel):
    attribute: str
    count: int = 1


@app.post("/player/allocate")
def allocate(req: AllocateRequest) -> dict:
    with get_session() as s:
        ok, err, p = player_sys.allocate_point(s, req.attribute, req.count)
        if not ok or p is None:
            raise HTTPException(400, err or "allocate failed")
        return p.model_dump()


# ---------- World ----------

@app.get("/map")
def map_view() -> dict:
    with get_session() as s:
        world = load_world(s)
        return build_map_data(s, world)


@app.post("/memory/backfill")
async def memory_backfill(limit: int = 200) -> dict:
    if not settings.embedding_enabled:
        raise HTTPException(400, "embedding not enabled")
    client = get_embedding()
    count = 0
    with get_session() as s:
        rows = s.exec(select(MemoryRow).limit(limit)).all()
        for r in rows:
            if r.embedding_json and r.embedding_json != "[]":
                continue
            vec = await client.embed(r.summary)
            r.embedding_json = serialize(vec)
            s.add(r)
            count += 1
        s.commit()
    return {"updated": count, "checked": len(rows)}


@app.get("/world/state")
def world_state() -> dict:
    with get_session() as s:
        world = load_world(s)
        return {
            "id": world.id, "tick": world.tick,
            "day": world.day, "hour": world.hour, "seed": world.seed,
            "season": world.season,
            "season_label": i18n.season_label(world.season),
            "weather": world.weather,
            "weather_label": i18n.weather_label(world.weather),
            "tension": world.director.tension,
            "last_event_tick": world.director.last_event_tick,
            "total_currency": world.economy.total_currency,
        }


@app.post("/world/tick")
def world_tick() -> dict:
    with get_session() as s:
        world = load_world(s)
        tick(s, world)
        save_world(s, world)
        return {
            "tick": world.tick, "day": world.day, "hour": world.hour,
            "season": world.season, "weather": world.weather,
            "tension": world.director.tension,
        }


@app.post("/world/step")
async def world_step() -> dict:
    with get_session() as s:
        world = load_world(s)
        tick(s, world)
        await check_timeouts(s, world)

        npcs = load_npcs(s)
        rng = random.Random(world.seed * 1000003 + world.tick * 7)
        social = await maybe_social_dialogue(s, world, npcs, rng)

        templates = director.load_templates()
        event = await run_event_cycle(s, world, templates, force=False)
        save_world(s, world)

        return {
            "tick": world.tick, "day": world.day, "hour": world.hour,
            "tension": world.director.tension,
            "season": world.season,
            "season_label": i18n.season_label(world.season),
            "weather": world.weather,
            "weather_label": i18n.weather_label(world.weather),
            "event": event.id if event else None,
            "event_summary": event.payload.get("summary") if event else None,
            "event_template": event.template_id if event else None,
            "template_label": i18n.template_label(event.template_id) if event else None,
            "awaiting_player": event.state == "awaiting_player" if event else False,
            "social_dialogue": social,
        }


def _npc_to_display(npc: NPC) -> dict:
    return {
        "id": npc.id, "name": npc.name, "age": npc.age,
        "gender": npc.gender,
        "gender_label": i18n.gender_label(npc.gender),
        "location_id": npc.location_id,
        "location_label": i18n.location_label(npc.location_id),
        "goals": npc.goals,
        "traits": [
            {"key": k, "label": i18n.trait_label(k), "value": float(v)}
            for k, v in npc.traits.items()
        ],
        "needs": [
            {"key": k, "label": i18n.need_label(k), "value": float(v)}
            for k, v in npc.needs.items()
        ],
    }


@app.get("/npc")
def list_npcs() -> list[dict]:
    with get_session() as s:
        return [_npc_to_display(n) for n in load_npcs(s)]


@app.get("/npc/{npc_id}")
def get_npc(npc_id: str) -> dict:
    with get_session() as s:
        npcs = {n.id: n for n in load_npcs(s)}
        if npc_id not in npcs:
            raise HTTPException(404, "npc not found")
        return _npc_to_display(npcs[npc_id])


@app.get("/npc/{npc_id}/relationships")
def npc_relationships(npc_id: str) -> list[dict]:
    with get_session() as s:
        npcs = {n.id: n.name for n in load_npcs(s)}
        result = []
        for r in relationship.list_relationships(s, npc_id):
            other_id = r.to_npc if r.from_npc == npc_id else r.from_npc
            result.append({
                "from_npc": r.from_npc, "to_npc": r.to_npc,
                "other_id": other_id,
                "other_name": npcs.get(other_id, other_id),
                "trust": r.trust, "affection": r.affection,
                "fear": r.fear, "debt": r.debt,
            })
        return result


@app.get("/npc/{npc_id}/items")
def npc_items(npc_id: str) -> list[dict]:
    with get_session() as s:
        rows = inventory.list_items_by_owner(s, npc_id)
        return [inventory.row_to_dict(r) for r in rows]


@app.get("/npc/{npc_id}/memories")
def npc_memories(npc_id: str, limit: int = 20) -> list[dict]:
    with get_session() as s:
        rows = s.exec(
            select(MemoryRow).where(MemoryRow.npc_id == npc_id)
            .order_by(MemoryRow.timestamp.desc()).limit(limit)
        ).all()
        return [
            {
                "id": r.id, "event_id": r.event_id,
                "summary": r.summary,
                "emotion": loads(r.emotion_json) or {},
                "timestamp": r.timestamp,
                "has_embedding": bool(r.embedding_json and r.embedding_json != "[]"),
            }
            for r in rows
        ]


def _row_to_event(r: EventRow, npc_names: dict[str, str]) -> dict:
    payload = loads(r.payload_json) or {}
    participants = loads(r.participants_json) or []
    participant_names = [npc_names.get(pid, pid) for pid in participants]
    choices = payload.get("choices") or []
    interactive = bool(payload.get("interactive", True))
    as_message = bool(payload.get("as_message", False))

    return {
        "id": r.id, "template_id": r.template_id,
        "template_label": i18n.template_label(r.template_id),
        "participants": participants, "participant_names": participant_names,
        "location_id": r.location_id,
        "location_label": i18n.location_label(r.location_id),
        "state": r.state, "state_label": i18n.state_label(r.state),
        "awaiting_player": r.state == "awaiting_player",
        "interactive": interactive, "payload": payload,
        "as_message": as_message,
        "summary": payload.get("summary") or "",
        "narrative": payload.get("narrative") or "",
        "choices": choices,
        "choice_made": payload.get("choice_made") or "",
        "choice_label": payload.get("choice_label") or "",
        "outcome": payload.get("outcome") or "",
        "check": payload.get("check") or {},
        "exp_gain": payload.get("exp_gain", 0),
        "rep_gain": payload.get("rep_gain", 0),
        "item_id": payload.get("item_id") or "",
        "item_owner": payload.get("item_owner") or "",
        "relevance_score": payload.get("relevance_score", 0.0),
        "created_at": r.created_at, "resolved_at": r.resolved_at,
    }


@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:
    with get_session() as s:
        npc_names = {n.id: n.name for n in load_npcs(s)}
        rows = s.exec(
            select(EventRow).order_by(EventRow.created_at.desc()).limit(limit)
        ).all()
        return [_row_to_event(r, npc_names) for r in rows]


@app.get("/event/pending")
def list_pending_events() -> list[dict]:
    with get_session() as s:
        npc_names = {n.id: n.name for n in load_npcs(s)}
        rows = s.exec(
            select(EventRow).where(EventRow.state == "awaiting_player")
            .order_by(EventRow.created_at.desc())
        ).all()
        return [_row_to_event(r, npc_names) for r in rows]


@app.post("/event/trigger")
async def trigger_event() -> dict:
    with get_session() as s:
        world = load_world(s)
        templates = director.load_templates()
        event = await run_event_cycle(s, world, templates, force=True)
        if event is None:
            raise HTTPException(400, "no event triggered")
        npc_names = {n.id: n.name for n in load_npcs(s)}
        row = s.get(EventRow, event.id)
        return _row_to_event(row, npc_names)


class ResolveRequest(BaseModel):
    choice_id: str


@app.post("/event/{event_id}/resolve")
async def resolve_event_endpoint(event_id: str, req: ResolveRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        result = await resolve_event(s, world, event_id, req.choice_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "resolve failed"))
        return result


# ---------- Chronicle ----------

@app.get("/chronicle")
def get_chronicles(limit: int = 20) -> list[dict]:
    with get_session() as s:
        return list_chronicles(s, limit=limit)


class ChronicleRequest(BaseModel):
    title_hint: str = ""


@app.post("/chronicle/generate")
async def make_chronicle(req: ChronicleRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        result = await generate_chronicle(
            s, from_tick=max(0, world.tick - 200),
            to_tick=world.tick, title_hint=req.title_hint,
        )
        if result is None:
            raise HTTPException(500, "chronicle generation failed")
        return result


# ---------- Reward ----------

@app.get("/reward")
def list_rewards(limit: int = 20) -> list[dict]:
    with get_session() as s:
        rows = s.exec(
            select(RewardRow).order_by(RewardRow.id.desc()).limit(limit)
        ).all()
        return [
            {
                "id": r.id, "event_id": r.event_id,
                "kind": r.kind,
                "kind_label": i18n.reward_kind_label(r.kind),
                "value": r.value,
                "description": r.description,
                "payload": loads(r.payload_json) or {},
            }
            for r in rows
        ]


# ---------- Item ----------

class GiveRequest(BaseModel):
    owner_id: str


class UseRequest(BaseModel):
    target_npc_id: str = ""


def _row_to_item(r: ItemRow, npc_names: dict[str, str]) -> dict:
    owner_id = r.owner_id or ""
    if owner_id == "player":
        owner_label = "你"
    elif owner_id in npc_names:
        owner_label = npc_names[owner_id]
    elif owner_id:
        owner_label = owner_id
    else:
        owner_label = "无主"
    return {
        "id": r.id, "reward_id": r.reward_id, "event_id": r.event_id,
        "name": r.name, "kind": r.kind,
        "affixes": loads(r.affixes_json) or [],
        "story": r.story, "value": r.value,
        "owner_id": owner_id, "owner_label": owner_label,
        "consumed": r.consumed,
    }


@app.get("/item")
def list_items(limit: int = 100, owner_id: str | None = None) -> list[dict]:
    with get_session() as s:
        npc_names = {n.id: n.name for n in load_npcs(s)}
        if owner_id is None:
            rows = inventory.list_all_items(s)
        else:
            rows = inventory.list_items_by_owner(s, owner_id)
        rows = rows[:limit]
        return [_row_to_item(r, npc_names) for r in rows]


@app.get("/item/{item_id}")
def get_item(item_id: str) -> dict:
    with get_session() as s:
        row = inventory.get_item_row(s, item_id)
        if row is None:
            raise HTTPException(404, "item not found")
        npc_names = {n.id: n.name for n in load_npcs(s)}
        return _row_to_item(row, npc_names)


@app.post("/item/{item_id}/give")
def give_item(item_id: str, req: GiveRequest) -> dict:
    with get_session() as s:
        row = inventory.give_item(s, item_id, req.owner_id)
        if row is None:
            raise HTTPException(404, "item not found")
        npc_names = {n.id: n.name for n in load_npcs(s)}
        return _row_to_item(row, npc_names)


@app.post("/item/{item_id}/take")
def take_item(item_id: str) -> dict:
    with get_session() as s:
        row = inventory.give_item(s, item_id, "player")
        if row is None:
            raise HTTPException(404, "item not found")
        npc_names = {n.id: n.name for n in load_npcs(s)}
        return _row_to_item(row, npc_names)


@app.post("/item/{item_id}/drop")
def drop_item(item_id: str) -> dict:
    with get_session() as s:
        row = inventory.drop_item(s, item_id)
        if row is None:
            raise HTTPException(404, "item not found")
        npc_names = {n.id: n.name for n in load_npcs(s)}
        return _row_to_item(row, npc_names)


@app.post("/item/{item_id}/use")
async def use_item_endpoint(item_id: str, req: UseRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        result = await item_use.use_item(
            s, world, item_id=item_id,
            user_id="player", target_npc_id=req.target_npc_id,
        )
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "use failed"))
        return result
'''

# ================================================================
# tests
# ================================================================

FILES["tests/test_player.py"] = r'''import random

from sqlmodel import Session, SQLModel, create_engine

from server.systems import player as player_sys


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_create_player():
    engine = _engine()
    with Session(engine) as s:
        p = player_sys.create_player(s, "张铁柱", "male", "山里来的猎户")
        assert p.name == "张铁柱"
        assert p.gender == "male"
        assert p.created is True
        # 猎户给 strength +1, agility +2
        assert p.attributes["strength"] == 6
        assert p.attributes["agility"] == 7


def test_exp_and_level():
    engine = _engine()
    with Session(engine) as s:
        player_sys.create_player(s, "测试", "female")
        p, leveled = player_sys.add_exp(s, 150)
        assert leveled is True
        assert p.level == 2
        assert p.unspent_points == 2


def test_allocate_point():
    engine = _engine()
    with Session(engine) as s:
        p = player_sys.create_player(s, "测试", "female")
        # 给点经验升级
        player_sys.add_exp(s, 150)
        ok, err, p = player_sys.allocate_point(s, "strength", 1)
        assert ok, err
        assert p.attributes["strength"] == 6
        assert p.unspent_points == 1


def test_roll_check_success_and_failure():
    from server.models.schemas import Player
    p = Player(id="player", name="测试", attributes={
        "strength": 5, "agility": 5, "intelligence": 5,
        "perception": 5, "charisma": 5, "luck": 5,
    })
    # 全成功率：属性 20 + 骰子 10 = 30，远高于阈值
    p_strong = p.model_copy(update={"attributes": {**p.attributes, "strength": 20}})
    r = player_sys.roll_check(p_strong, "strength", "normal", random.Random(1))
    assert r["result"] in ("success", "critical")

    # 全失败率：属性 1，骰子最多 10，总 11 < 15 常见
    p_weak = p.model_copy(update={"attributes": {**p.attributes, "strength": 1}})
    r2 = player_sys.roll_check(p_weak, "strength", "heroic", random.Random(1))
    assert r2["result"] in ("partial", "failure")
'''

FILES["tests/test_relevance.py"] = r'''from sqlmodel import Session, SQLModel, create_engine

from server.core.world import create_world, save_world
from server.models.schemas import Event, EventTemplate, Player
from server.systems import relationship
from server.systems.relevance import check_relevance


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_same_location_increases_relevance():
    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        save_world(s, world)
        player = Player(
            id="player", name="张", location_id="market",
            attributes={"luck": 5, "strength": 5, "agility": 5,
                        "intelligence": 5, "perception": 5, "charisma": 5},
            known_npcs=[],
        )
        evt = Event(
            id="e", template_id="market_dispute",
            participants=["npc_a"], location_id="market",
        )
        tpl = EventTemplate(id="market_dispute", tags=["daily"])
        ok, score, detail = check_relevance(s, evt, tpl, world, player, [])
        # 同地点 +0.25，加上 daily 不加 public 分
        assert "same_location" in detail
        assert score >= 0.25


def test_no_relevance_at_all():
    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        save_world(s, world)
        player = Player(
            id="player", name="张", location_id="home",
            attributes={"luck": 5, "strength": 5, "agility": 5,
                        "intelligence": 5, "perception": 5, "charisma": 5},
        )
        evt = Event(
            id="e", template_id="x",
            participants=["npc_a"], location_id="forest",
        )
        tpl = EventTemplate(id="x", tags=["daily"])
        ok, score, detail = check_relevance(s, evt, tpl, world, player, [])
        assert ok is False
        assert score < 0.35
'''

FILES["tests/test_choices.py"] = r'''from server.core.choices import build_choices, pick_attribute
from server.models.schemas import EventTemplate


def test_choices_have_attribute():
    tpl = EventTemplate(id="bandit_raid", tags=["conflict"])
    choices = build_choices(tpl)
    assert len(choices) == 3
    for c in choices:
        assert "attribute" in c
        assert "attribute_label" in c
    help_c = [c for c in choices if c["id"] == "help"][0]
    # conflict tag → strength
    assert help_c["attribute"] == "strength"


def test_pick_attribute_by_tag():
    assert pick_attribute(EventTemplate(id="x", tags=["romance"]), "charisma") == "charisma"
    assert pick_attribute(EventTemplate(id="x", tags=["conflict"]), "charisma") == "strength"
    assert pick_attribute(EventTemplate(id="x", tags=["investigation"]), "charisma") == "intelligence"
    # 无 tag 时用 default
    assert pick_attribute(EventTemplate(id="x", tags=[]), "luck") == "luck"
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()

    written = 0
    for rel, content in FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and not args.force:
            print("[skip]  " + rel)
            continue
        p.write_text(content, encoding="utf-8", newline="\n")
        print("[write] " + rel)
        written += 1

    print("\nPart 19A done. written=%d" % written)
    print()
    print("下一步：")
    print("  1. pytest -v")
    print("  2. 清库（首次运行需要新表）")
    print("     Remove-Item data\\world.db")
    print("     python tools\\seed_world.py --npc 8")
    print("  3. uvicorn server.main:app --reload")
    print()
    print("然后等 Part 19B 的客户端。")


if __name__ == '__main__':
    main()