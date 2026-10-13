"""玩家参与事件的测试。"""
import pytest
from sqlmodel import Session, SQLModel, create_engine

from server.core.choices import build_choices, get_choice_spec
from server.core.world import create_world, load_world, save_event, save_npc, save_world
from server.models.db import EventRow
from server.models.schemas import Event, EventTemplate, NPC


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_build_choices_default():
    tpl = EventTemplate(id="x", tags=[])
    choices = build_choices(tpl)
    assert len(choices) == 3
    ids = [c["id"] for c in choices]
    assert ids == ["help", "observe", "oppose"]


def test_build_choices_conflict_labels():
    tpl = EventTemplate(id="x", tags=["conflict"])
    choices = build_choices(tpl)
    labels = {c["id"]: c["label"] for c in choices}
    assert labels["help"] == "挺身而出"
    assert labels["oppose"] == "站在强势一方"


def test_get_choice_spec():
    spec = get_choice_spec("help")
    assert spec is not None
    assert spec["relation_delta"]["trust"] > 0

    spec = get_choice_spec("oppose")
    assert spec["tension_delta"] > 0

    assert get_choice_spec("nonexistent") is None


@pytest.mark.asyncio
async def test_resolve_event_applies_effects(monkeypatch):
    """玩家响应事件后，关系与状态都应更新。"""
    from server.core import event_flow
    from server.systems import player as player_sys

    class FakeLLM:
        async def text_json(self, prompt):
            return {"outcome": "你挺身而出，众人感激。"}
        async def text(self, prompt):
            return "ok"

    monkeypatch.setattr(event_flow, "get_llm", lambda: FakeLLM())

    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        world.tick = 5
        save_world(s, world)

        # 关键：必须先创建玩家，否则 resolve_event 会拒绝
        player_sys.create_player(s, "测试者", "male")

        save_npc(s, NPC(id="npc_a", name="Alden", age=30))
        save_npc(s, NPC(id="npc_b", name="Dain", age=30))

        evt = Event(
            id="evt_1",
            template_id="bandit_raid",
            participants=["npc_a", "npc_b"],
            location_id="village_edge",
            state="awaiting_player",
            payload={
                "summary": "强盗袭击，Alden 与 Dain 奋力抵抗。",
                "narrative": "刀光剑影中，两人背靠背站着。",
                "choices": build_choices(EventTemplate(id="bandit_raid", tags=["conflict"])),
                "max_reward": 0.5,
                "difficulty": 0.5,
                "tpl_tags": ["conflict"],
            },
            created_at=5,
        )
        save_event(s, evt)

        result = await event_flow.resolve_event(s, world, "evt_1", "help")
        assert result["ok"] is True, result
        assert result["choice_id"] == "help"
        # 新流程返回 outcome 和属性判定
        assert "outcome" in result
        assert "check" in result
        assert result["check"]["attribute"] == "strength"  # conflict → strength

        # 状态变成 resolved
        row = s.get(EventRow, "evt_1")
        assert row is not None
        assert row.state == "resolved"

        # 关系提升
        from server.systems.relationship import get_relation_to
        rel = get_relation_to(s, "npc_a", "player")
        # 至少应该有变化（不是初始 0）
        assert rel.trust != 0 or rel.affection != 0


@pytest.mark.asyncio
async def test_timeout_marks_expired(monkeypatch):
    from server.core import event_flow
    from server.systems import player as player_sys

    class FakeLLM:
        async def text_json(self, prompt):
            return {"outcome": "ok"}

    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        world.tick = 100
        save_world(s, world)

        evt = Event(
            id="evt_stale",
            template_id="x",
            participants=[],
            location_id="village_square",
            state="awaiting_player",
            payload={"summary": "一件事"},
            created_at=0,
        )
        save_event(s, evt)

        count = await event_flow.check_timeouts(s, world)
        assert count == 1

        row = s.get(EventRow, "evt_stale")
        assert row is not None
        assert row.state == "expired"


def test_event_response_has_participant_names():
    """事件返回应带 participant_names 字段。"""
    from server.main import _row_to_event
    row = EventRow(
        id="evt_x",
        template_id="bandit_raid",
        participants_json='["npc_a", "npc_b"]',
        location_id="village_edge",
        state="awaiting_player",
        payload_json='{"summary": "x", "choices": []}',
        created_at=1,
    )
    npc_names = {"npc_a": "Alden", "npc_b": "Dain"}
    result = _row_to_event(row, npc_names)
    assert result["participant_names"] == ["Alden", "Dain"]
    assert result["awaiting_player"] is True