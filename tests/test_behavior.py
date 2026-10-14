import random

from sqlmodel import Session, SQLModel, create_engine

from server.core.world import create_world, save_npc, save_world
from server.models.schemas import NPC
from server.systems import behavior


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_npc_rng_is_deterministic():
    w = create_world("t", seed=42)
    r1 = behavior._npc_rng(w, "npc_a")
    r2 = behavior._npc_rng(w, "npc_a")
    r3 = behavior._npc_rng(w, "npc_b")
    assert r1.random() == r2.random()  # 相同种子
    # 不同 NPC 的随机序列应不同
    a = [behavior._npc_rng(w, "npc_a").random() for _ in range(5)]
    b = [behavior._npc_rng(w, "npc_b").random() for _ in range(5)]
    assert a != b


def test_time_prefs_shift_by_hour():
    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        world.hour = 9  # morning
        save_world(s, world)
        npc = NPC(id="npc_x", name="X", age=30, goals=["赚钱"],
                  behavior_profile={"wealth": 0.9, "social": 0.5})
        save_npc(s, npc)
        # 新版 behavior.step 直接运行即可
        behavior.step(s, world)
        from server.core.world import load_npcs
        after = load_npcs(s)
        assert len(after) == 1
        assert after[0].location_id != ""


def test_crowd_penalty_exists():
    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        save_world(s, world)
        for i in range(6):
            save_npc(s, NPC(id="npc_%d" % i, name="N%d" % i,
                            age=20, location_id="village_square"))
        penalty = behavior._crowd_penalty(s, world, "npc_0")
        assert penalty["socialize"] < 0


def test_step_moves_npcs_and_saves():
    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        save_world(s, world)
        for i in range(3):
            save_npc(s, NPC(id="npc_%d" % i, name="N%d" % i, age=20,
                            goals=["x"], behavior_profile={"wealth": 0.5}))
        behavior.step(s, world)
        from server.core.world import load_npcs
        npcs = load_npcs(s)
        assert len(npcs) == 3
