from server.core.evaluator import evaluate_event, evaluate_reward
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
