# Pydantic 数据模型

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


DEFAULT_ATTRIBUTES: dict[str, int] = {
    "strength": 5, "agility": 5, "intelligence": 5,
    "perception": 5, "charisma": 5, "luck": 5,
}

ATTRIBUTE_META: list[dict[str, str]] = [
    {"key": "strength", "label": "力量", "desc": "肉体对抗、搬运、战斗"},
    {"key": "agility", "label": "敏捷", "desc": "躲避、逃脱、潜行"},
    {"key": "intelligence", "label": "智慧", "desc": "推理、查证、计谋"},
    {"key": "perception", "label": "感知", "desc": "观察、听风、发现线索"},
    {"key": "charisma", "label": "魅力", "desc": "说服、社交、调解"},
    {"key": "luck", "label": "运气", "desc": "巧合、意外之财、逃过一劫"},
]


class Family(BaseModel):
    spouse: str = ""
    children: list[str] = Field(default_factory=list)
    parents: list[str] = Field(default_factory=list)
    siblings: list[str] = Field(default_factory=list)


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
    family: Family = Field(default_factory=Family)


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
    kind: str = ""


EventState = Literal["pending", "active", "awaiting_player", "resolved", "expired", "rejected"]


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
