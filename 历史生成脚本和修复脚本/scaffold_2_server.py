r"""EmergentWorld scaffold - Part 2/3: server 代码。

运行：
    python scaffold_2_server.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

FILES["server/config.py"] = r'''from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_api_key: str = "sk-test"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    db_path: Path = Path("data/world.db")
    cache_dir: Path = Path(".cache/llm")
    seed: int = 42
    log_level: str = "INFO"

    content_dir: Path = Path("content")


settings = Settings()
'''

FILES["server/main.py"] = r'''"""FastAPI 入口。MVP 阶段所有路由集中在此。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlmodel import Session, SQLModel, create_engine

from server.config import settings
from server.core.tick import tick
from server.core.world import load_npcs, load_world, save_world
from server.models.schemas import NPC, World

engine = create_engine(f"sqlite:///{settings.db_path}", echo=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        load_world(session)
    yield


app = FastAPI(title="EmergentWorld", lifespan=lifespan)


def get_session() -> Session:
    return Session(engine)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/world/state", response_model=World)
def world_state() -> World:
    with get_session() as s:
        return load_world(s)


@app.post("/world/tick", response_model=World)
def world_tick() -> World:
    with get_session() as s:
        world = load_world(s)
        tick(s, world)
        save_world(s, world)
        return world


@app.get("/npc", response_model=list[NPC])
def list_npcs() -> list[NPC]:
    with get_session() as s:
        return load_npcs(s)


@app.get("/npc/{npc_id}", response_model=NPC)
def get_npc(npc_id: str) -> NPC:
    with get_session() as s:
        npcs = {n.id: n for n in load_npcs(s)}
        if npc_id not in npcs:
            raise HTTPException(404, "npc not found")
        return npcs[npc_id]
'''

FILES["server/models/schemas.py"] = r'''"""所有 Pydantic 数据模型。生成物必须经此 Schema 校验。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class NPC(BaseModel):
    id: str
    name: str
    age: int = Field(ge=0, le=200)
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


EventState = Literal["pending", "active", "resolved", "rejected"]


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

FILES["server/models/db.py"] = r'''"""SQLModel 表定义。与 schemas.py 保持字段一致。"""

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


class NPCRow(SQLModel, table=True):
    __tablename__ = "npc"
    id: str = Field(primary_key=True)
    name: str
    age: int = 0
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

FILES["server/core/world.py"] = r'''"""世界状态管理。内存 + DB 双写。"""

from __future__ import annotations

from sqlmodel import Session, select

from server.models.db import EventRow, NPCRow, WorldRow, dumps, loads
from server.models.schemas import DirectorState, EconomyState, Event, NPC, World


def create_world(world_id: str = "default", seed: int = 42) -> World:
    return World(id=world_id, seed=seed)


def save_world(session: Session, world: World) -> None:
    row = session.get(WorldRow, world.id) or WorldRow(id=world.id)
    row.tick = world.tick
    row.day = world.day
    row.hour = world.hour
    row.seed = world.seed
    row.director_json = dumps(world.director.model_dump())
    row.economy_json = dumps(world.economy.model_dump())
    row.location_ids_json = dumps(world.location_ids)
    session.add(row)
    session.commit()


def load_world(session: Session, world_id: str = "default") -> World:
    row = session.get(WorldRow, world_id)
    if row is None:
        w = create_world(world_id)
        save_world(session, w)
        return w
    return World(
        id=row.id,
        tick=row.tick,
        day=row.day,
        hour=row.hour,
        seed=row.seed,
        director=DirectorState(**loads(row.director_json)),
        economy=EconomyState(**loads(row.economy_json)),
        location_ids=loads(row.location_ids_json) or ["village_square"],
    )


def save_npc(session: Session, npc: NPC) -> None:
    row = session.get(NPCRow, npc.id) or NPCRow(id=npc.id, name=npc.name)
    row.name = npc.name
    row.age = npc.age
    row.traits_json = dumps(npc.traits)
    row.needs_json = dumps(npc.needs)
    row.goals_json = dumps(npc.goals)
    row.behavior_json = dumps(npc.behavior_profile)
    row.asset_json = dumps(npc.asset_params)
    row.memory_ids_json = dumps(npc.memory_ids)
    row.location_id = npc.location_id
    row.alive = npc.alive
    session.add(row)
    session.commit()


def load_npcs(session: Session) -> list[NPC]:
    rows = session.exec(select(NPCRow).where(NPCRow.alive == True)).all()  # noqa: E712
    return [
        NPC(
            id=r.id,
            name=r.name,
            age=r.age,
            traits=loads(r.traits_json) or {},
            needs=loads(r.needs_json) or {},
            goals=loads(r.goals_json) or [],
            behavior_profile=loads(r.behavior_json) or {},
            asset_params=loads(r.asset_json) or {},
            memory_ids=loads(r.memory_ids_json) or [],
            location_id=r.location_id,
            alive=r.alive,
        )
        for r in rows
    ]


def save_event(session: Session, event: Event) -> None:
    row = session.get(EventRow, event.id) or EventRow(id=event.id, template_id=event.template_id)
    row.template_id = event.template_id
    row.participants_json = dumps(event.participants)
    row.location_id = event.location_id
    row.state = event.state
    row.payload_json = dumps(event.payload)
    row.created_at = event.created_at
    row.resolved_at = event.resolved_at
    session.add(row)
    session.commit()
'''

FILES["server/core/tick.py"] = r'''"""时间推进。所有实时逻辑必须同步、无 LLM 调用。"""

from __future__ import annotations

from sqlmodel import Session

from server.core.world import save_world
from server.models.schemas import World
from server.systems import behavior, economy


def tick(session: Session, world: World) -> None:
    behavior.step(session, world)
    economy.settle(session, world)

    world.hour += 1
    if world.hour >= 24:
        world.hour = 0
        world.day += 1
    world.tick += 1

    save_world(session, world)
'''

FILES["server/core/director.py"] = r'''"""事件导演：决定何时触发何事件。不调用 LLM。"""

from __future__ import annotations

import random
from pathlib import Path

import yaml

from server.models.schemas import EventTemplate, World


def load_templates(template_dir: str = "content/templates/events") -> list[EventTemplate]:
    tpls: list[EventTemplate] = []
    for path in Path(template_dir).glob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        tpls.append(EventTemplate(**data))
    return tpls


def fit_tension(tpl: EventTemplate, tension: float) -> float:
    conflict = "conflict" in tpl.tags
    if conflict:
        return 0.3 + tension
    return 1.2 - tension * 0.5


def cooldown_ok(tpl: EventTemplate, world: World) -> bool:
    last = world.director.last_event_tick
    return (world.tick - last) >= tpl.cooldown


def pick_template(
    templates: list[EventTemplate],
    world: World,
    rng: random.Random,
) -> EventTemplate | None:
    candidates: list[tuple[float, EventTemplate]] = []
    for tpl in templates:
        if not cooldown_ok(tpl, world):
            continue
        score = tpl.weight * fit_tension(tpl, world.director.tension)
        candidates.append((score, tpl))
    if not candidates:
        return None
    total = sum(s for s, _ in candidates)
    r = rng.random() * total
    acc = 0.0
    for score, tpl in candidates:
        acc += score
        if r <= acc:
            return tpl
    return candidates[-1][1]
'''

FILES["server/core/evaluator.py"] = r'''"""评估器：生成系统的核心。规则层 + LLM 抽样层 + 日志层。"""

from __future__ import annotations

import uuid

from sqlmodel import Session

from server.models.db import EvaluationRow, dumps
from server.models.schemas import Event, NPC, Reward, World


def entities_exist(event: Event, world: World, npc_ids: set[str]) -> bool:
    return all(p in npc_ids for p in event.participants)


def reward_over_budget(reward: Reward, budget: float) -> bool:
    return reward.value > budget * 1.2


def contradicts_memory(event: Event, world: World) -> bool:
    return False


def evaluate_event(
    event: Event,
    world: World,
    npc_ids: set[str],
    budget: float = 1.0,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not entities_exist(event, world, npc_ids):
        errors.append("missing_entity")
    if not event.location_id:
        errors.append("missing_location")
    if event.created_at < 0:
        errors.append("invalid_time")
    if contradicts_memory(event, world):
        errors.append("contradiction")
    return (len(errors) == 0), errors


def log_evaluation(
    session: Session,
    target_type: str,
    target_id: str,
    passed: bool,
    errors: list[str],
    score: float | None = None,
    raw: dict | None = None,
) -> None:
    row = EvaluationRow(
        id=str(uuid.uuid4()),
        target_type=target_type,
        target_id=target_id,
        passed=passed,
        score=score,
        errors_json=dumps(errors),
        raw_json=dumps(raw or {}),
    )
    session.add(row)
    session.commit()


def evaluate_npc(npc: NPC) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not npc.name:
        errors.append("missing_name")
    if not (0 <= npc.age <= 200):
        errors.append("invalid_age")
    if not npc.goals:
        errors.append("missing_goals")
    return (len(errors) == 0), errors


def evaluate_reward(reward: Reward, budget: float) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if reward.value < 0:
        errors.append("negative_value")
    if reward_over_budget(reward, budget):
        errors.append("reward_over_budget")
    if not reward.description:
        errors.append("missing_description")
    return (len(errors) == 0), errors
'''

FILES["server/generators/base.py"] = r'''"""LLM 客户端封装。异步、可缓存、强制 JSON Schema。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from server.config import settings

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
        self.model = settings.llm_model
        self.cache_dir = settings.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, prompt: str, schema_name: str) -> str:
        h = hashlib.sha256(f"{self.model}|{schema_name}|{prompt}".encode())
        return h.hexdigest()

    def _cache_get(self, key: str) -> dict | None:
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    def _cache_set(self, key: str, data: dict) -> None:
        path = self.cache_dir / f"{key}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _call_raw(self, prompt: str, schema_json: dict) -> str:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a game content generator. "
                        "Always answer with valid JSON matching the given schema. "
                        "No prose, no markdown fences."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.9,
        )
        return resp.choices[0].message.content or "{}"

    async def json(
        self,
        prompt: str,
        schema: type[T],
        *,
        fallback: T | None = None,
    ) -> T:
        key = self._cache_key(prompt, schema.__name__)
        cached = self._cache_get(key)
        if cached is not None:
            try:
                return schema.model_validate(cached)
            except Exception:
                pass
        try:
            raw = await self._call_raw(prompt, schema.model_json_schema())
            data = json.loads(raw)
            obj = schema.model_validate(data)
            self._cache_set(key, obj.model_dump())
            return obj
        except Exception:
            if fallback is not None:
                return fallback
            raise

    async def text(self, prompt: str) -> str:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
        )
        return resp.choices[0].message.content or ""


_llm: LLMClient | None = None


def get_llm() -> LLMClient:
    global _llm
    if _llm is None:
        _llm = LLMClient()
    return _llm


def load_prompt(name: str) -> str:
    path = Path("server/prompts") / name
    return path.read_text(encoding="utf-8")
'''

FILES["server/generators/npc.py"] = r'''"""NPC 生成器：LLM 生成属性，规则补齐，评估器校验。"""

from __future__ import annotations

import uuid

from server.core.evaluator import evaluate_npc
from server.generators.base import get_llm, load_prompt
from server.models.schemas import NPC

TRAIT_KEYS = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
NEED_KEYS = ["hunger", "safety", "social", "wealth", "curiosity"]


def _default_npc(npc_id: str, seed_name: str) -> NPC:
    return NPC(
        id=npc_id,
        name=seed_name,
        age=30,
        traits={k: 0.5 for k in TRAIT_KEYS},
        needs={k: 0.5 for k in NEED_KEYS},
        goals=["survive"],
        behavior_profile={k: 0.5 for k in NEED_KEYS},
        asset_params={"hair": "short", "outfit": "plain", "palette": "neutral"},
    )


async def generate_npc(seed_name: str, context: str = "") -> NPC:
    npc_id = f"npc_{uuid.uuid4().hex[:8]}"
    fallback = _default_npc(npc_id, seed_name)
    prompt = load_prompt("npc_gen.md").format(name=seed_name, context=context)
    npc = await get_llm().json(prompt, NPC, fallback=fallback)
    npc.id = npc_id
    npc.name = npc.name or seed_name
    ok, _ = evaluate_npc(npc)
    if not ok:
        return fallback
    return npc
'''

FILES["server/generators/event.py"] = r'''"""事件生成器：模板 + LLM 填充。"""

from __future__ import annotations

import random
import uuid

from server.generators.base import get_llm, load_prompt
from server.models.schemas import Event, EventTemplate, NPC, World


def _pick_participants(tpl: EventTemplate, npcs: list[NPC], rng: random.Random) -> list[str]:
    n = int(tpl.params.get("participant_count", 2))
    n = min(n, len(npcs))
    return [npc.id for npc in rng.sample(npcs, n)] if n > 0 else []


async def fill_event(
    tpl: EventTemplate,
    world: World,
    npcs: list[NPC],
    rng: random.Random,
) -> Event:
    participants = _pick_participants(tpl, npcs, rng)
    location = tpl.params.get("location", "village_square")

    prompt = load_prompt("event_fill.md").format(
        template_id=tpl.id,
        prompt=tpl.prompt,
        participants=", ".join(participants) or "none",
        location=location,
        day=world.day,
    )
    fallback_payload = {"summary": f"{tpl.id} at {location}", "narrative": ""}

    try:
        payload_obj = await get_llm().json(prompt, Event, fallback=None)
        payload = payload_obj.payload
    except Exception:
        payload = fallback_payload

    return Event(
        id=f"evt_{uuid.uuid4().hex[:8]}",
        template_id=tpl.id,
        participants=participants,
        location_id=location,
        state="pending",
        payload=payload,
        created_at=world.tick,
    )
'''

FILES["server/generators/reward.py"] = r'''"""奖励生成器：预算约束下的模板 + LLM 描述。"""

from __future__ import annotations

import uuid

from server.models.schemas import Event, Reward, World


def compute_budget(event: Event, world: World, difficulty: float = 0.5) -> float:
    base = 0.3 + difficulty * 0.5
    return base * world.economy.reward_budget_multiplier


async def generate_reward(event: Event, world: World) -> Reward:
    budget = compute_budget(event, world)
    value = min(budget, 1.0)
    return Reward(
        id=f"rwd_{uuid.uuid4().hex[:8]}",
        event_id=event.id,
        kind="item",
        value=value,
        description=f"Reward for {event.template_id}",
        payload={},
    )
'''

FILES["server/generators/dialogue.py"] = r'''"""NPC 对话生成：检索记忆 + 生成回复。"""

from __future__ import annotations

from server.generators.base import get_llm, load_prompt
from server.models.schemas import NPC, World


async def npc_dialogue(npc: NPC, player_input: str, world: World, memories: list[str]) -> str:
    prompt = load_prompt("dialogue.md").format(
        name=npc.name,
        traits=npc.traits,
        goals=npc.goals,
        memories="\n".join(f"- {m}" for m in memories) or "（无）",
        player_input=player_input,
    )
    try:
        return await get_llm().text(prompt)
    except Exception:
        return f"{npc.name}沉默了一会儿，没有回答。"
'''

FILES["server/systems/behavior.py"] = r'''"""效用 AI：无 LLM，实时决策。"""

from __future__ import annotations

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


def score_action(npc: NPC, action: Action) -> float:
    need_val = npc.needs.get(action.need, 0.5)
    weight = npc.behavior_profile.get(action.need, 0.5)
    return need_val * weight


def decide(npc: NPC, rng: random.Random) -> Action:
    scored = [(score_action(npc, a), a) for a in DEFAULT_ACTIONS]
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:2]
    return rng.choice(top)[1]


def step(session: Session, world: World) -> None:
    rng = random.Random(world.seed + world.tick)
    npcs = load_npcs(session)
    for npc in npcs:
        action = decide(npc, rng)
        if action.location_id:
            npc.location_id = action.location_id
        for k in npc.needs:
            npc.needs[k] = max(0.0, min(1.0, npc.needs.get(k, 0.5) + 0.02))
'''

FILES["server/systems/economy.py"] = r'''"""经济系统：货币总量、通胀、奖励预算。"""

from __future__ import annotations

from sqlmodel import Session

from server.models.schemas import World


def settle(session: Session, world: World) -> None:
    world.economy.total_currency *= 1.0005
    world.economy.inflation = max(1.0, world.economy.total_currency / 1000.0)
'''

FILES["server/prompts/npc_gen.md"] = r'''你是游戏 NPC 生成器。根据给定的名字与上下文，生成一个 NPC。

规则：
- 输出必须是合法 JSON，符合 NPC Schema
- traits 使用大五人格：openness, conscientiousness, extraversion, agreeableness, neuroticism
- needs 使用：hunger, safety, social, wealth, curiosity
- goals 至少 2 条，一条短期，一条长期
- behavior_profile 与 needs 同键，值 0-1
- asset_params 包含 hair, outfit, palette 三个键
- 所有值域 0-1，除非另有说明
- 不要输出 markdown，不要输出解释

名字：{name}
上下文：{context}
'''

FILES["server/prompts/event_fill.md"] = r'''你是游戏事件填充器。给定一个事件模板与世界上下文，生成事件细节。

规则：
- 输出必须是合法 JSON
- 顶层键为 payload，payload 内含 summary 与 narrative
- narrative 长度 2-4 句，符合世界氛围
- 不要改变参与者与地点
- 不要输出 markdown

模板 ID：{template_id}
模板提示：{prompt}
参与者：{participants}
地点：{location}
当前天数：{day}
'''

FILES["server/prompts/dialogue.md"] = r'''你在扮演一个游戏 NPC。根据人设与记忆，对玩家的话做出回应。

规则：
- 保持角色口吻
- 不超过 3 句
- 不要提及你是 AI
- 不要输出 markdown

名字：{name}
性格：{traits}
目标：{goals}
相关记忆：
{memories}

玩家说：{player_input}
'''

FILES["server/prompts/review.md"] = r'''你是游戏内容评审。对给定生成物打分 1-5，并指出问题。

规则：
- 输出必须是合法 JSON，形如 {{"score": 3.5, "errors": []}}
- 分数低于 3.5 表示建议拒绝
- errors 使用简短英文标签

生成物：{payload}
世界上下文：{context}
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    for rel, content in FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and not args.force:
            print(f"[skip]  {rel}")
            continue
        p.write_text(content, encoding="utf-8", newline="\n")
        print(f"[write] {rel}")

    print("\nPart 2/3 done.")


if globals().get('__name__') == '__main__':
    main()