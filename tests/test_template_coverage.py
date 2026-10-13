"""校验所有模板都有中文标签，且数量符合预期。"""
import yaml
from pathlib import Path

from server import i18n


def _load_template_ids() -> list[str]:
    ids: list[str] = []
    for p in sorted(Path("content/templates/events").glob("*.yaml")):
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("id"):
            ids.append(str(data["id"]))
    return ids


def test_at_least_30_templates():
    ids = _load_template_ids()
    assert len(ids) >= 30, "expected >= 30 templates, got %d" % len(ids)


def test_all_templates_have_labels():
    ids = _load_template_ids()
    missing = [tid for tid in ids if tid not in i18n.TEMPLATE_LABELS]
    assert not missing, "missing labels: " + ", ".join(missing)


def test_template_ids_are_unique():
    ids = _load_template_ids()
    dupes = [x for x in set(ids) if ids.count(x) > 1]
    assert not dupes, "duplicate ids: " + ", ".join(dupes)


def test_template_required_fields():
    for p in sorted(Path("content/templates/events").glob("*.yaml")):
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        for key in ["id", "tags", "cooldown", "weight", "params", "prompt", "evaluator"]:
            assert key in data, "%s missing field %s" % (p.name, key)
        # tags 至少有一个
        assert isinstance(data["tags"], list) and len(data["tags"]) > 0, \
            "%s has empty tags" % p.name
        # participant_count 合理
        pc = data["params"].get("participant_count", 1)
        assert 1 <= int(pc) <= 8, "%s bad participant_count: %s" % (p.name, pc)
        # max_reward 范围
        mr = float(data["evaluator"].get("max_reward", 0.5))
        assert 0.0 < mr <= 1.0, "%s bad max_reward: %s" % (p.name, mr)


def test_tag_distribution():
    """确保 tags 覆盖多种类型，不至于全是 conflict。"""
    from collections import Counter
    counter: Counter = Counter()
    for p in Path("content/templates/events").glob("*.yaml"):
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        for t in data.get("tags", []):
            counter[t] += 1
    # 至少要有这几种核心类型
    for required in ["conflict", "social", "daily"]:
        assert counter[required] >= 3, "tag %s only appears %d times" % (required, counter[required])
