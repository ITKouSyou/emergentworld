import random

from sqlmodel import Session, SQLModel, create_engine

from server.systems.relationship import adjust, apply_event_effects, get_or_create


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_get_or_create_and_adjust():
    engine = _engine()
    with Session(engine) as s:
        r = get_or_create(s, "npc_a", "npc_b")
        assert r.trust == 0.0
        r2 = adjust(s, "npc_a", "npc_b", trust=0.3, affection=0.2)
        assert abs(r2.trust - 0.3) < 1e-6
        assert abs(r2.affection - 0.2) < 1e-6


def test_apply_event_effects_conflict_lowers_trust():
    engine = _engine()
    with Session(engine) as s:
        rng = random.Random(42)
        apply_event_effects(s, ["a", "b", "c"], ["conflict"], rng)
        r = get_or_create(s, "a", "b")
        assert r.trust < 0
