r"""EmergentWorld scaffold - Part 3/3: templates, tools, tests.

运行：
    python scaffold_3_content.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

FILES["content/templates/events/missing_person.yaml"] = r'''id: missing_person
tags: [conflict, investigation]
cooldown: 5
weight: 1.0
conditions:
  - location.has_people >= 5
  - director.tension < 0.7
params:
  participant_count: 3
  location: village_square
prompt: |
  生成一个失踪事件。受害者与嫌疑人有隐藏关系。
  事件必须符合世界当前势力、地点、NPC 记忆。
evaluator:
  require: [victim, suspect, location]
  max_reward: 0.3
'''

FILES["content/templates/events/merchant_arrives.yaml"] = r'''id: merchant_arrives
tags: [trade, daily]
cooldown: 4
weight: 1.2
conditions:
  - director.tension < 0.5
params:
  participant_count: 2
  location: market
prompt: |
  一名行商抵达村庄，带来稀有物品与外来消息。
  消息应与某个 NPC 的目标或记忆相关。
evaluator:
  require: [merchant, item, rumor]
  max_reward: 0.2
'''

FILES["content/templates/events/bandit_raid.yaml"] = r'''id: bandit_raid
tags: [conflict, combat]
cooldown: 8
weight: 1.0
conditions:
  - director.tension > 0.4
params:
  participant_count: 4
  location: village_edge
prompt: |
  强盗袭击村庄边缘。至少一名 NPC 受伤或失去财物。
  事件应提升整体紧张度。
evaluator:
  require: [bandits, defenders, outcome]
  max_reward: 0.5
'''

FILES["content/templates/events/lovers_quarrel.yaml"] = r'''id: lovers_quarrel
tags: [social, daily]
cooldown: 3
weight: 1.1
conditions:
  - director.tension < 0.6
params:
  participant_count: 2
  location: tavern
prompt: |
  两名有亲密关系的 NPC 发生争吵，起因与第三方有关。
  争吵应暴露隐藏关系或目标冲突。
evaluator:
  require: [lover_a, lover_b, cause]
  max_reward: 0.15
'''

FILES["content/templates/events/harvest_festival.yaml"] = r'''id: harvest_festival
tags: [social, daily, celebration]
cooldown: 20
weight: 1.3
conditions:
  - director.tension < 0.4
params:
  participant_count: 5
  location: village_square
prompt: |
  丰收节庆典。多个 NPC 参与，展示各自的性格与关系。
  事件应降低整体紧张度。
evaluator:
  require: [activities, participants, mood]
  max_reward: 0.25
'''

FILES["content/templates/events/mysterious_stranger.yaml"] = r'''id: mysterious_stranger
tags: [mystery, plot]
cooldown: 12
weight: 0.9
conditions:
  - director.tension > 0.3
params:
  participant_count: 2
  location: forest
prompt: |
  一个神秘陌生人出现在村庄附近。其身份与世界某段历史相关。
  不要直接揭示身份，留下线索。
evaluator:
  require: [stranger, clue, hook]
  max_reward: 0.35
'''

FILES["content/templates/events/illness_outbreak.yaml"] = r'''id: illness_outbreak
tags: [conflict, survival]
cooldown: 15
weight: 0.9
conditions:
  - director.tension > 0.5
params:
  participant_count: 3
  location: home
prompt: |
  村庄爆发疾病。至少一名 NPC 病倒。
  事件应引发资源紧张与关系变化。
evaluator:
  require: [patients, cause, response]
  max_reward: 0.4
'''

FILES["content/templates/events/treasure_rumor.yaml"] = r'''id: treasure_rumor
tags: [mystery, adventure]
cooldown: 10
weight: 1.0
conditions:
  - director.tension < 0.7
params:
  participant_count: 2
  location: tavern
prompt: |
  酒馆里流传一个宝藏传闻。传闻应指向某个已知地点或 NPC。
  真假由世界状态决定，不直接揭示。
evaluator:
  require: [rumor, source, location]
  max_reward: 0.3
'''

FILES["content/templates/events/political_intrigue.yaml"] = r'''id: political_intrigue
tags: [conflict, plot]
cooldown: 12
weight: 0.9
conditions:
  - director.tension > 0.4
params:
  participant_count: 3
  location: village_hall
prompt: |
  村庄内部出现权力斗争。至少一名 NPC 试图拉拢玩家。
  事件应改变势力关系。
evaluator:
  require: [factions, scheme, target]
  max_reward: 0.35
'''

FILES["content/templates/events/natural_disaster.yaml"] = r'''id: natural_disaster
tags: [survival, conflict]
cooldown: 25
weight: 0.8
conditions:
  - director.tension > 0.6
params:
  participant_count: 5
  location: village_square
prompt: |
  自然灾害袭击村庄。多个 NPC 受影响。
  事件应显著提升紧张度并改变地形或资源。
evaluator:
  require: [disaster_type, affected, aftermath]
  max_reward: 0.6
'''

FILES["tools/seed_world.py"] = r'''"""初始化世界：生成 NPC、加载模板、写入数据库。"""

from __future__ import annotations

import argparse
import asyncio
import random

from sqlmodel import Session, SQLModel, create_engine

from server.config import settings
from server.core.director import load_templates
from server.core.world import create_world, save_npc, save_world
from server.generators.npc import generate_npc

FIRST_NAMES = [
    "Alden", "Bryn", "Cora", "Dain", "Eira", "Fen", "Gale", "Hale",
    "Ira", "Joss", "Kira", "Lior", "Mira", "Nox", "Orin", "Pia",
    "Quin", "Rhea", "Sil", "Tov",
]


async def seed(n: int, seed_value: int) -> None:
    rng = random.Random(seed_value)
    engine = create_engine(f"sqlite:///{settings.db_path}")
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        world = create_world("default", seed=seed_value)
        save_world(session, world)
        names = rng.sample(FIRST_NAMES, min(n, len(FIRST_NAMES)))
        for name in names:
            npc = await generate_npc(name, context="一个偏远村庄")
            save_npc(session, npc)
            print(f"created npc {npc.id} {npc.name}")

    templates = load_templates()
    print(f"loaded {len(templates)} event templates")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--npc", type=int, default=20)
    parser.add_argument("--seed", type=int, default=settings.seed)
    args = parser.parse_args()
    asyncio.run(seed(args.npc, args.seed))


if globals().get('__name__') == '__main__':
    main()
'''

FILES["tools/evolve.py"] = r'''"""离线演化：模拟 N 天，生成编年史。"""

from __future__ import annotations

import argparse

from sqlmodel import Session, create_engine, select

from server.config import settings
from server.core.tick import tick
from server.core.world import load_world, save_world
from server.models.db import EventRow


def summarize_chronicle(session: Session, world_id: str) -> str:
    events = session.exec(select(EventRow).order_by(EventRow.created_at.desc()).limit(50)).all()
    lines = [f"World {world_id} chronicle:"]
    for e in events:
        lines.append(f"- [{e.template_id}] at {e.location_id} ({e.state})")
    return "\n".join(lines)


def evolve(days: int = 30) -> None:
    engine = create_engine(f"sqlite:///{settings.db_path}")
    with Session(engine) as session:
        world = load_world(session)
        for _ in range(days * 24):
            tick(session, world)
        save_world(session, world)
        print(summarize_chronicle(session, world.id))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    evolve(args.days)


if globals().get('__name__') == '__main__':
    main()
'''

FILES["tests/test_world.py"] = r'''from sqlmodel import Session, SQLModel, create_engine

from server.core.world import create_world, load_world, save_world


def test_create_and_save_world():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        w = create_world("test", seed=1)
        save_world(s, w)
        loaded = load_world(s, "test")
        assert loaded.id == "test"
        assert loaded.seed == 1
'''

FILES["tests/test_director.py"] = r'''import random

from server.core.director import fit_tension, pick_template
from server.models.schemas import EventTemplate, World


def _tpl(id_: str, tags: list[str], weight: float = 1.0, cooldown: int = 0) -> EventTemplate:
    return EventTemplate(id=id_, tags=tags, weight=weight, cooldown=cooldown)


def test_fit_tension_prefers_conflict_when_high():
    tpl = _tpl("a", ["conflict"])
    assert fit_tension(tpl, 0.9) > fit_tension(tpl, 0.1)


def test_pick_template_returns_something():
    world = World(id="w", seed=1)
    world.director.last_event_tick = -999
    tpls = [_tpl("a", ["daily"]), _tpl("b", ["conflict"])]
    picked = pick_template(tpls, world, random.Random(1))
    assert picked is not None
'''

FILES["tests/test_evaluator.py"] = r'''from server.core.evaluator import evaluate_event, evaluate_reward
from server.models.schemas import Event, Reward, World


def test_evaluate_event_missing_entity():
    world = World(id="w")
    evt = Event(id="e", template_id="t", participants=["npc_missing"], location_id="loc")
    ok, errors = evaluate_event(evt, world, npc_ids={"npc_1"})
    assert not ok
    assert "missing_entity" in errors


def test_evaluate_reward_over_budget():
    r = Reward(id="r", event_id="e", kind="item", value=10.0, description="x")
    ok, errors = evaluate_reward(r, budget=1.0)
    assert not ok
    assert "reward_over_budget" in errors
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

    print("\nPart 3/3 done.")


if globals().get('__name__') == '__main__':
    main()