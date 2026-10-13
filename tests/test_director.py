import random

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
