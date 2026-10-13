"""事件导演：条件求值 + 张力曲线 + 权重衰减 + 节奏 + 防重复。"""

from __future__ import annotations

import math
import random
import re
from functools import lru_cache
from pathlib import Path

import yaml

from server.models.schemas import Event, EventTemplate, NPC, World


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

TAG_SIGMA = 0.28


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


def build_context(world: World, npcs: list[NPC]) -> dict:
    by_loc: dict[str, int] = {}
    for npc in npcs:
        by_loc[npc.location_id] = by_loc.get(npc.location_id, 0) + 1
    max_people = max(by_loc.values()) if by_loc else 0
    gap = world.tick - world.director.last_event_tick

    return {
        "world": {"tick": world.tick, "day": world.day, "hour": world.hour},
        "director": {
            "tension": world.director.tension,
            "last_event_tick": world.director.last_event_tick,
            "event_count": len(world.director.event_history),
            "ticks_since_last": gap,
        },
        "npc": {"count": len(npcs)},
        "location": {"has_people": len(npcs), "max_people": max_people},
        "tension": world.director.tension,
        "tick": world.tick,
        "hour": world.hour,
        "npc_count": len(npcs),
    }


def _gauss(x: float, mu: float, sigma: float) -> float:
    d = x - mu
    return math.exp(-(d * d) / (2 * sigma * sigma))


def fit_tension(tpl: EventTemplate, tension: float) -> float:
    if not tpl.tags:
        return 0.5
    scores: list[float] = []
    for tag in tpl.tags:
        mu = TAG_TENSION_CENTER.get(tag)
        scores.append(0.5 if mu is None else _gauss(tension, mu, TAG_SIGMA))
    scores.sort(reverse=True)
    top = scores[:2]
    return sum(top) / len(top)


def recent_penalty(tpl_id: str, world: World, window: int = 20) -> float:
    recent = world.director.event_history[-window:]
    count = recent.count(tpl_id)
    return 1.0 / (1.0 + count * 0.6)


def rhythm_factor(world: World) -> float:
    gap = world.tick - world.director.last_event_tick
    if gap >= 30:  return 1.5
    if gap <= 1:   return 0.4
    if gap <= 3:   return 0.7
    return 1.0


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


def cooldown_ok(tpl: EventTemplate, world: World) -> bool:
    last = world.director.last_event_tick
    return (world.tick - last) >= tpl.cooldown


def should_trigger(world: World, rng: random.Random) -> bool:
    gap = world.tick - world.director.last_event_tick
    if gap < 3:
        return False
    if gap >= 20:
        return True
    base = 0.03 + world.director.tension * 0.10
    if gap < 8:
        base *= 0.5
    elif gap >= 12:
        base *= 1.6
    return rng.random() < base


def pick_template(
    templates: list[EventTemplate],
    world: World,
    npcs: list[NPC],
    rng: random.Random,
    ignore_cooldown: bool = False,
    pending_template_ids: set[str] | None = None,
    want_interactive: bool | None = None,
) -> EventTemplate | None:
    """从模板池里挑一个。

    pending_template_ids: 已在 awaiting_player 的模板 id 集合，会被跳过
    want_interactive: 只挑 interactive 值为该值（或 None 表示不限）
    """
    ctx = build_context(world, npcs)
    rhythm = rhythm_factor(world)
    tension = world.director.tension

    candidates: list[tuple[float, EventTemplate]] = []
    for tpl in templates:
        # 防重复：等待中的模板不再挑
        if pending_template_ids and tpl.id in pending_template_ids:
            continue

        if not ignore_cooldown and not cooldown_ok(tpl, world):
            continue
        if not ignore_cooldown and not conditions_ok(tpl, ctx):
            continue

        if want_interactive is not None and tpl.interactive != want_interactive:
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
