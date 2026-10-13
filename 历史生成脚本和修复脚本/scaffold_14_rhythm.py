r"""EmergentWorld scaffold - Part 14: 事件节奏感。

- 条件求值：模板的 conditions 字段真正生效
- 张力曲线：每个 tag 有理想张力中心，用高斯匹配
- 权重衰减：同一模板短期内重复出现则权重降低
- 节奏因子：长时间无事件会放宽，刚发生过会收紧

运行：
    python scaffold_14_rhythm.py --force
"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

# ================================================================ director 覆盖

FILES["server/core/director.py"] = r'''"""事件导演：条件求值 + 张力曲线 + 权重衰减 + 节奏因子。

职责：
    1. 决定何时触发事件（should_trigger）
    2. 从模板池里挑一个（pick_template）
    3. 事件后更新张力（update_tension_after_event）

设计原则：
    - 模板的 conditions 会被真正执行，不再只是文档
    - 每个 tag 有理想张力中心，用高斯曲线匹配当前张力
    - 同一模板短期内重复出现会降低权重
    - 长时间无事件会鼓励触发
"""

from __future__ import annotations

import math
import random
import re
from functools import lru_cache
from pathlib import Path

import yaml

from server.models.schemas import Event, EventTemplate, NPC, World


# ============================================================
# 张力曲线参数
# ============================================================

# 每个 tag 在什么张力下最合适
TAG_TENSION_CENTER: dict[str, float] = {
    "conflict":     0.75,
    "combat":       0.80,
    "survival":     0.65,
    "mystery":      0.50,
    "investigation": 0.50,
    "plot":         0.55,
    "political":    0.55,
    "adventure":    0.50,
    "social":       0.35,
    "daily":        0.30,
    "romance":      0.35,
    "celebration":  0.25,
    "ritual":       0.40,
    "trade":        0.35,
}

TAG_SIGMA = 0.28  # 高斯曲线宽度


# ============================================================
# 条件求值
# ============================================================

_COND_RE = re.compile(r"^\s*([\w\.]+)\s*(>=|<=|==|!=|>|<)\s*(.+?)\s*$")


def _resolve_path(ctx: dict, path: str):
    parts = path.split(".")
    cur = ctx
    for p in parts:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def _parse_rhs(s: str):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _eval_condition(expr: str, ctx: dict) -> bool:
    """求值单个条件。

    无法解析或未知路径时返回 True（宽松通过），
    避免因拼错而永久屏蔽某个模板。
    """
    m = _COND_RE.match(expr)
    if not m:
        return True
    path, op, rhs_raw = m.groups()
    lhs = _resolve_path(ctx, path)
    if lhs is None:
        return True
    rhs = _parse_rhs(rhs_raw)
    try:
        if op == ">":  return bool(lhs > rhs)
        if op == "<":  return bool(lhs < rhs)
        if op == ">=": return bool(lhs >= rhs)
        if op == "<=": return bool(lhs <= rhs)
        if op == "==": return bool(lhs == rhs)
        if op == "!=": return bool(lhs != rhs)
    except TypeError:
        return True
    return True


def conditions_ok(tpl: EventTemplate, ctx: dict) -> bool:
    for cond in tpl.conditions:
        if not _eval_condition(cond, ctx):
            return False
    return True


# ============================================================
# 上下文
# ============================================================

def build_context(world: World, npcs: list[NPC]) -> dict:
    by_loc: dict[str, int] = {}
    for npc in npcs:
        by_loc[npc.location_id] = by_loc.get(npc.location_id, 0) + 1
    max_people = max(by_loc.values()) if by_loc else 0
    gap = world.tick - world.director.last_event_tick

    return {
        "world": {
            "tick": world.tick,
            "day": world.day,
            "hour": world.hour,
        },
        "director": {
            "tension": world.director.tension,
            "last_event_tick": world.director.last_event_tick,
            "event_count": len(world.director.event_history),
            "ticks_since_last": gap,
        },
        "npc": {
            "count": len(npcs),
        },
        # location.has_people 语义：全村 NPC 数（模板作者意图是"村里有人"）
        # location.max_people 语义：最密集地点的人数
        "location": {
            "has_people": len(npcs),
            "max_people": max_people,
        },
        # 简写，方便写条件
        "tension": world.director.tension,
        "tick": world.tick,
        "hour": world.hour,
        "npc_count": len(npcs),
    }


# ============================================================
# 张力匹配
# ============================================================

def _gauss(x: float, mu: float, sigma: float) -> float:
    d = x - mu
    return math.exp(-(d * d) / (2 * sigma * sigma))


def fit_tension(tpl: EventTemplate, tension: float) -> float:
    """模板与当前张力的匹配度，返回 0-1。"""
    if not tpl.tags:
        return 0.5

    scores: list[float] = []
    for tag in tpl.tags:
        mu = TAG_TENSION_CENTER.get(tag)
        if mu is None:
            scores.append(0.5)
        else:
            scores.append(_gauss(tension, mu, TAG_SIGMA))

    scores.sort(reverse=True)
    top = scores[:2]
    return sum(top) / len(top)


# ============================================================
# 多样性：最近出现的越多，权重越低
# ============================================================

def recent_penalty(tpl_id: str, world: World, window: int = 20) -> float:
    recent = world.director.event_history[-window:]
    count = recent.count(tpl_id)
    return 1.0 / (1.0 + count * 0.6)


# ============================================================
# 节奏因子
# ============================================================

def rhythm_factor(world: World) -> float:
    gap = world.tick - world.director.last_event_tick
    if gap >= 30:
        return 1.5
    if gap <= 1:
        return 0.4
    if gap <= 3:
        return 0.7
    return 1.0


# ============================================================
# 模板加载
# ============================================================

@lru_cache(maxsize=1)
def _load_templates_cached(template_dir: str) -> tuple[EventTemplate, ...]:
    tpls: list[EventTemplate] = []
    for path in sorted(Path(template_dir).glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data:
            tpls.append(EventTemplate(**data))
    return tuple(tpls)


def load_templates(template_dir: str = "content/templates/events") -> list[EventTemplate]:
    return list(_load_templates_cached(str(template_dir)))


# ============================================================
# 冷却
# ============================================================

def cooldown_ok(tpl: EventTemplate, world: World) -> bool:
    last = world.director.last_event_tick
    return (world.tick - last) >= tpl.cooldown


# ============================================================
# 触发判断
# ============================================================

def should_trigger(world: World, rng: random.Random) -> bool:
    """每 tick 判断是否尝试触发。张力高、间隔久时更容易。"""
    gap = world.tick - world.director.last_event_tick
    if gap < 3:
        return False

    base = 0.015 + world.director.tension * 0.05
    if gap < 8:
        base *= 0.5
    elif gap >= 30:
        base *= 1.8

    return rng.random() < base


# ============================================================
# 模板选择
# ============================================================

def pick_template(
    templates: list[EventTemplate],
    world: World,
    npcs: list[NPC],
    rng: random.Random,
    ignore_cooldown: bool = False,
) -> EventTemplate | None:
    ctx = build_context(world, npcs)
    rhythm = rhythm_factor(world)
    tension = world.director.tension

    candidates: list[tuple[float, EventTemplate]] = []
    for tpl in templates:
        if not ignore_cooldown and not cooldown_ok(tpl, world):
            continue
        if not ignore_cooldown and not conditions_ok(tpl, ctx):
            continue

        fit = fit_tension(tpl, tension)
        if fit < 0.05:
            continue

        diversity = recent_penalty(tpl.id, world)
        score = tpl.weight * fit * diversity * rhythm
        if score <= 0:
            continue
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


# ============================================================
# 张力更新
# ============================================================

_TAG_TENSION_DELTA: dict[str, float] = {
    "conflict":     0.12,
    "combat":       0.15,
    "survival":     0.08,
    "mystery":      0.03,
    "investigation": 0.03,
    "plot":         0.02,
    "political":    0.05,
    "adventure":    0.02,
    "social":      -0.08,
    "daily":       -0.08,
    "romance":     -0.06,
    "celebration": -0.10,
    "ritual":      -0.03,
    "trade":       -0.06,
}


def update_tension_after_event(world: World, event: Event, tpl: EventTemplate) -> None:
    if tpl.tags:
        deltas = [_TAG_TENSION_DELTA.get(t, 0.0) for t in tpl.tags]
        avg = sum(deltas) / len(deltas)
    else:
        avg = 0.0

    world.director.tension = max(0.0, min(1.0, world.director.tension + avg))
    world.director.last_event_tick = world.tick
    world.director.event_history.append(event.id)
    if len(world.director.event_history) > 200:
        world.director.event_history = world.director.event_history[-200:]


def decay_tension(world: World) -> None:
    world.director.tension = max(0.0, world.director.tension - 0.003)
'''

# ================================================================ event_flow 覆盖

FILES["server/core/event_flow.py"] = r'''"""事件流程：串起 Director + Generator + Evaluator + 记忆 + 关系 + 物品。"""

from __future__ import annotations

import random
from typing import Optional

from sqlmodel import Session

from server.core import director
from server.core.evaluator import evaluate_event, evaluate_reward, log_evaluation
from server.core.world import load_npcs, save_event, save_world
from server.generators.event import fill_event
from server.generators.reward import compute_budget, generate_reward
from server.models.db import ItemRow, RewardRow, dumps
from server.models.schemas import Event, EventTemplate, Reward, World
from server.systems import relationship


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


def _pick_owner(event: Event, rng: random.Random) -> str:
    if not event.participants:
        return "player"
    if rng.random() < 0.5:
        return "player"
    return rng.choice(event.participants)


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


def _apply_effects(
    session: Session,
    world: World,
    event: Event,
    tpl: EventTemplate,
    rng: random.Random,
) -> None:
    summary = event.payload.get("summary", "") or "发生了 %s" % tpl.id
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


async def run_event_cycle(
    session: Session,
    world: World,
    templates: list[EventTemplate],
    force: bool = False,
) -> Optional[Event]:
    rng = random.Random(world.seed * 1000003 + world.tick)

    if not force and not director.should_trigger(world, rng):
        return None

    # npcs 提前加载，因为 pick_template 需要用于条件求值
    npcs = load_npcs(session)
    if len(npcs) < 1:
        return None

    tpl = director.pick_template(
        templates, world, npcs, rng, ignore_cooldown=force,
    )
    if tpl is None:
        return None

    event = await fill_event(tpl, world, npcs, rng)

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

    event.state = "active"
    save_event(session, event)

    _apply_effects(session, world, event, tpl, rng)

    budget = compute_budget(event, world)
    reward = await generate_reward(event, world)
    reward_ok, reward_errors = evaluate_reward(reward, budget)
    log_evaluation(session, "reward", reward.id, reward_ok, reward_errors)

    if reward_ok:
        _save_reward(session, reward)
        event.payload["reward_id"] = reward.id

        item_data = reward.payload.get("item")
        if isinstance(item_data, dict) and item_data.get("id"):
            owner = _pick_owner(event, rng)
            _save_item(session, reward.id, event.id, item_data, owner)
            event.payload["item_id"] = item_data["id"]
            event.payload["item_owner"] = owner

    event.state = "resolved"
    event.resolved_at = world.tick
    save_event(session, event)

    director.update_tension_after_event(world, event, tpl)
    save_world(session, world)

    return event
'''

# ================================================================ test_director 覆盖

FILES["tests/test_director.py"] = r'''import random

from server.core.director import (
    build_context,
    conditions_ok,
    cooldown_ok,
    fit_tension,
    pick_template,
    recent_penalty,
    rhythm_factor,
    update_tension_after_event,
)
from server.models.schemas import Event, EventTemplate, NPC, World


def _tpl(id_: str, tags: list[str] | None = None, weight: float = 1.0,
         cooldown: int = 0, conditions: list[str] | None = None) -> EventTemplate:
    return EventTemplate(
        id=id_,
        tags=tags or [],
        weight=weight,
        cooldown=cooldown,
        conditions=conditions or [],
    )


def _npcs(n: int) -> list[NPC]:
    return [NPC(id="npc_%d" % i, name="N%d" % i, age=20) for i in range(n)]


# ---------- fit_tension ----------

def test_fit_tension_conflict_prefers_high():
    tpl = _tpl("a", ["conflict"])
    assert fit_tension(tpl, 0.9) > fit_tension(tpl, 0.1)


def test_fit_tension_romance_prefers_low():
    tpl = _tpl("a", ["romance"])
    assert fit_tension(tpl, 0.2) > fit_tension(tpl, 0.9)


def test_fit_tension_returns_0_to_1():
    for t in [0.0, 0.3, 0.5, 0.7, 1.0]:
        v = fit_tension(_tpl("a", ["conflict"]), t)
        assert 0.0 <= v <= 1.0


# ---------- conditions ----------

def test_conditions_simple_numeric():
    tpl = _tpl("a", conditions=["tension > 0.5"])
    assert not conditions_ok(tpl, {"tension": 0.3})
    assert conditions_ok(tpl, {"tension": 0.7})


def test_conditions_nested_path():
    tpl = _tpl("a", conditions=["director.tension < 0.7"])
    assert conditions_ok(tpl, {"director": {"tension": 0.5}})
    assert not conditions_ok(tpl, {"director": {"tension": 0.8}})


def test_conditions_unknown_path_passes():
    """未知路径应宽松通过，避免拼错永久屏蔽模板。"""
    tpl = _tpl("a", conditions=["foo.bar >= 10"])
    assert conditions_ok(tpl, {})


def test_conditions_multiple_all_must_pass():
    tpl = _tpl("a", conditions=["tension > 0.3", "tension < 0.7"])
    assert conditions_ok(tpl, {"tension": 0.5})
    assert not conditions_ok(tpl, {"tension": 0.2})
    assert not conditions_ok(tpl, {"tension": 0.9})


# ---------- diversity ----------

def test_recent_penalty_drops_with_repeats():
    world = World(id="w")
    world.director.event_history = ["a", "a", "a", "b"]
    pa = recent_penalty("a", world)
    pb = recent_penalty("b", world)
    assert pa < pb


def test_rhythm_factor_high_when_gap_large():
    world = World(id="w")
    world.tick = 100
    world.director.last_event_tick = 100  # gap=0
    assert rhythm_factor(world) < 1.0

    world.director.last_event_tick = 40   # gap=60
    assert rhythm_factor(world) > 1.0


# ---------- pick_template ----------

def test_pick_template_respects_conditions():
    world = World(id="w", seed=1)
    world.tick = 10
    world.director.last_event_tick = -999
    world.director.tension = 0.9   # 高张力

    # 只给一个要求低张力的模板，应该选不到
    tpl = _tpl("low_tension", ["romance"], conditions=["tension < 0.3"])
    picked = pick_template([tpl], world, _npcs(5), random.Random(1))
    assert picked is None


def test_pick_template_works_when_conditions_met():
    world = World(id="w", seed=1)
    world.tick = 10
    world.director.last_event_tick = -999
    world.director.tension = 0.2

    tpl = _tpl("romance", ["romance"], conditions=["tension < 0.4"])
    picked = pick_template([tpl], world, _npcs(5), random.Random(1))
    assert picked is not None
    assert picked.id == "romance"


def test_pick_template_ignore_cooldown():
    world = World(id="w", seed=1)
    world.tick = 5
    world.director.last_event_tick = 5  # gap=0，冷却不满足

    tpl = _tpl("a", ["daily"], cooldown=100)
    # 不忽略冷却 → 选不到
    assert pick_template([tpl], world, _npcs(3), random.Random(1)) is None
    # 忽略 → 选得到
    assert pick_template([tpl], world, _npcs(3), random.Random(1),
                         ignore_cooldown=True) is not None


def test_pick_template_prefers_appropriate_tension():
    """高张力下，冲突模板应该比爱情模板更容易被选中。"""
    world = World(id="w", seed=42)
    world.tick = 100
    world.director.last_event_tick = -999
    world.director.tension = 0.9

    conflict = _tpl("conflict_x", ["conflict"], weight=1.0)
    romance = _tpl("romance_x", ["romance"], weight=1.0)

    picked_count = {"conflict": 0, "romance": 0}
    for seed in range(50):
        rng = random.Random(seed)
        # 每轮重置 history，避免多样性衰减干扰
        world.director.event_history = []
        p = pick_template([conflict, romance], world, _npcs(5), rng)
        if p is not None:
            picked_count[p.id.split("_")[0]] += 1

    assert picked_count["conflict"] > picked_count["romance"], picked_count


# ---------- tension update ----------

def test_update_tension_conflict_raises():
    world = World(id="w")
    tpl = _tpl("a", ["conflict"])
    evt = Event(id="e", template_id="a", participants=[], location_id="loc")
    before = world.director.tension
    update_tension_after_event(world, evt, tpl)
    assert world.director.tension > before
    assert evt.id in world.director.event_history


def test_update_tension_social_lowers():
    world = World(id="w")
    world.director.tension = 0.8
    tpl = _tpl("a", ["social"])
    evt = Event(id="e", template_id="a", participants=[], location_id="loc")
    update_tension_after_event(world, evt, tpl)
    assert world.director.tension < 0.8


def test_update_tension_mixed_tags_averages():
    world = World(id="w")
    world.director.tension = 0.5
    # conflict (+0.12) 与 social (-0.08)，平均 +0.02
    tpl = _tpl("a", ["conflict", "social"])
    evt = Event(id="e", template_id="a", participants=[], location_id="loc")
    update_tension_after_event(world, evt, tpl)
    assert 0.5 < world.director.tension < 0.6


# ---------- build_context ----------

def test_build_context_shape():
    world = World(id="w", seed=1)
    world.tick = 50
    world.director.last_event_tick = 40
    world.director.tension = 0.4

    npcs = _npcs(5)
    ctx = build_context(world, npcs)
    assert ctx["tension"] == 0.4
    assert ctx["npc_count"] == 5
    assert ctx["director"]["ticks_since_last"] == 10
    assert ctx["world"]["tick"] == 50
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    written = 0
    skipped = 0
    for rel, content in FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and not args.force:
            print("[skip]  " + rel)
            skipped += 1
            continue
        p.write_text(content, encoding="utf-8", newline="\n")
        print("[write] " + rel)
        written += 1

    print("\nPart 14 done. written=%d skipped=%d" % (written, skipped))
    print()
    print("下一步：")
    print("  1. pytest -v")
    print("  2. 重启后端 uvicorn server.main:app --reload")


if globals().get('__name__') == '__main__':
    main()