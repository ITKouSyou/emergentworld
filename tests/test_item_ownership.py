import random

from server.core.event_flow import _resolve_item_owner
from server.models.schemas import Event


def test_oppose_item_goes_to_player():
    evt = Event(id="e", template_id="t", participants=["npc_a", "npc_b"])
    owner = _resolve_item_owner(evt, "oppose", random.Random(1))
    assert owner == "player"


def test_help_item_goes_to_first_participant():
    evt = Event(id="e", template_id="t", participants=["npc_a", "npc_b"])
    owner = _resolve_item_owner(evt, "help", random.Random(1))
    assert owner == "npc_a"


def test_help_no_participants_returns_empty():
    evt = Event(id="e", template_id="t", participants=[])
    owner = _resolve_item_owner(evt, "help", random.Random(1))
    assert owner == ""
