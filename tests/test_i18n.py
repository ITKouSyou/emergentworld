from server import i18n


def test_trait_labels_cover_default_keys():
    from server.generators.npc import TRAIT_KEYS, NEED_KEYS
    for k in TRAIT_KEYS:
        assert k in i18n.TRAIT_LABELS, "missing trait label: " + k
    for k in NEED_KEYS:
        assert k in i18n.NEED_LABELS, "missing need label: " + k


def test_template_labels_cover_templates():
    import yaml
    from pathlib import Path
    for p in Path("content/templates/events").glob("*.yaml"):
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        tid = data.get("id", "")
        assert tid in i18n.TEMPLATE_LABELS, "missing template label: " + tid


def test_all_labels_returns_all_buckets():
    labels = i18n.all_labels()
    for key in ["traits", "needs", "templates", "locations", "reward_kinds", "states"]:
        assert key in labels
