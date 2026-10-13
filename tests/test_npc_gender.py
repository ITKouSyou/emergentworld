from server.generators.npc import _default_npc, gender_zh
from server.models.schemas import NPC


def test_gender_zh_mapping():
    assert gender_zh("male") == "男"
    assert gender_zh("female") == "女"
    assert gender_zh("unknown") == "未知"
    assert gender_zh("other") == "未知"


def test_default_npc_has_gender_and_varied_traits():
    npc = _default_npc("npc_x", "张铁柱", "male")
    assert npc.gender == "male"
    assert npc.name == "张铁柱"
    values = list(npc.traits.values())
    assert len(set(round(v, 2) for v in values)) > 1


def test_npc_schema_gender_default():
    npc = NPC(id="x", name="y", age=30)
    assert npc.gender == "unknown"
