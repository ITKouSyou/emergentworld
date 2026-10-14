"""SQLModel 表定义。"""

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
    money: int = 0
    background: str = ""
    known_npcs_json: str = "[]"
    factions_json: str = "{}"
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
    family_json: str = "{}"
    schedule_json: str = "{}"
    impressions_json: str = "{}"
    faction: str = "neutral"


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
    kind: str = ""
    kind: str = ""


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


class GoalRow(SQLModel, table=True):
    __tablename__ = "goal"
    id: str = Field(primary_key=True)
    kind: str = "daily"           # daily / milestone
    key: str = ""                 # 唯一键
    label: str = ""
    target: int = 1
    progress: int = 0
    done: bool = False
    claimed: bool = False
    exp_reward: int = 0
    money_reward: int = 0
    created_day: int = 0
    created_tick: int = 0


class QuestRow(SQLModel, table=True):
    __tablename__ = "quest"
    id: str = Field(primary_key=True)
    title: str = ""
    description: str = ""
    kind: str = "fetch"
    giver_npc_id: str = ""
    target_npc_id: str = ""
    target_location_id: str = ""
    state: str = "active"
    progress: int = 0
    progress_target: int = 1
    reward_exp: int = 0
    reward_money: int = 0
    reward_item_id: str = ""
    source_event_id: str = ""
    created_tick: int = 0
    deadline_tick: int = 0
    completed_tick: int = 0


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
