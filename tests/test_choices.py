from server.core.choices import build_choices, pick_attribute
from server.models.schemas import EventTemplate


def test_choices_have_attribute():
    tpl = EventTemplate(id="bandit_raid", tags=["conflict"])
    choices = build_choices(tpl)
    assert len(choices) == 3
    for c in choices:
        assert "attribute" in c
        assert "attribute_label" in c
    help_c = [c for c in choices if c["id"] == "help"][0]
    # conflict tag → strength
    assert help_c["attribute"] == "strength"


def test_pick_attribute_by_tag():
    assert pick_attribute(EventTemplate(id="x", tags=["romance"]), "charisma") == "charisma"
    assert pick_attribute(EventTemplate(id="x", tags=["conflict"]), "charisma") == "strength"
    assert pick_attribute(EventTemplate(id="x", tags=["investigation"]), "charisma") == "intelligence"
    # 无 tag 时用 default
    assert pick_attribute(EventTemplate(id="x", tags=[]), "luck") == "luck"
