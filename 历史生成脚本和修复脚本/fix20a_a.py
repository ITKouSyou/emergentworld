# Part 20A-A：重建 schemas.py + family.py
from pathlib import Path

FILES = {}

FILES["server/models/schemas.py"] = '''# Pydantic 数据模型

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
'''

FILES["server/systems/family.py"] = '''# 家庭关系：夫妻、子女、兄弟姐妹、父母

from __future__ import annotations

import random

from sqlmodel import Session

from server.models.db import RelationshipRow
from server.models.schemas import NPC
from server.systems import relationship


def _set_kind(session, a: str, b: str, kind: str) -> None:
    rid = relationship._rel_id(a, b)
    row = session.get(RelationshipRow, rid)
    if row is None:
        row = RelationshipRow(id=rid, from_npc=a, to_npc=b)
    row.kind = kind
    session.add(row)
    session.commit()


def _set_family_baseline(session, a: str, b: str, kind: str) -> None:
    if kind == "spouse":
        rel = {"trust": 0.75, "affection": 0.85}
    elif kind == "parent":
        rel = {"trust": 0.7, "affection": 0.75, "debt": 0.3}
    elif kind == "child":
        rel = {"trust": 0.65, "affection": 0.8, "debt": 0.4}
    elif kind == "sibling":
        rel = {"trust": 0.5, "affection": 0.5}
    else:
        rel = {}

    relationship.adjust(session, a, b,
                        trust=rel.get("trust", 0.0),
                        affection=rel.get("affection", 0.0),
                        fear=rel.get("fear", 0.0),
                        debt=rel.get("debt", 0.0))
    relationship.adjust(session, b, a,
                        trust=rel.get("trust", 0.0),
                        affection=rel.get("affection", 0.0),
                        fear=rel.get("fear", 0.0),
                        debt=rel.get("debt", 0.0))
    _set_kind(session, a, b, kind)


def build_families(session, npcs, rng) -> None:
    if len(npcs) < 2:
        return

    adults_male = [n for n in npcs if n.gender == "male" and n.age >= 20]
    adults_female = [n for n in npcs if n.gender == "female" and n.age >= 20]

    rng.shuffle(adults_male)
    rng.shuffle(adults_female)

    couples = []
    for m, f in zip(adults_male, adults_female):
        couples.append((m, f))

    used_ids = set()
    for m, f in couples:
        m.family.spouse = f.id
        f.family.spouse = m.id
        _set_family_baseline(session, m.id, f.id, "spouse")
        used_ids.add(m.id)
        used_ids.add(f.id)

    single_pool = [n for n in npcs if n.id not in used_ids]
    for m, f in couples:
        n_children = rng.choice([0, 0, 1, 1, 2])
        for _ in range(n_children):
            if not single_pool:
                break
            single_pool.sort(key=lambda x: x.age)
            child = single_pool.pop(0)
            if child.age > m.age - 15 or child.age > f.age - 15:
                single_pool.append(child)
                continue
            child.family.parents = [m.id, f.id]
            m.family.children.append(child.id)
            f.family.children.append(child.id)
            _set_family_baseline(session, m.id, child.id, "parent")
            _set_family_baseline(session, f.id, child.id, "parent")

    remaining = [n for n in npcs if not n.family.spouse and not n.family.parents]
    rng.shuffle(remaining)
    while len(remaining) >= 2:
        a = remaining.pop()
        b = remaining.pop()
        if abs(a.age - b.age) > 12:
            remaining.append(b)
            continue
        a.family.siblings.append(b.id)
        b.family.siblings.append(a.id)
        _set_family_baseline(session, a.id, b.id, "sibling")

    from server.core.world import save_npc
    for npc in npcs:
        save_npc(session, npc)
'''


def main():
    root = Path.cwd()
    for rel, content in FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        print("[write] " + rel)
    print()
    print("A 部分完成。接下来运行：python fix20a_b.py")


if __name__ == "__main__":
    main()