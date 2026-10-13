r"""EmergentWorld scaffold - Part 13: 扩充 20 个事件模板。

运行：
    python scaffold_13_templates.py --force
"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

# ================================================================ 新事件模板

FILES["content/templates/events/traveling_bard.yaml"] = r'''id: traveling_bard
tags: [social, celebration, daily]
cooldown: 7
weight: 1.1
conditions:
  - director.tension < 0.6
params:
  participant_count: 3
  location: tavern
prompt: |
  一位流浪诗人来到酒馆，弹唱关于远方与旧事的歌谣。
  歌词里隐含着某个 NPC 的秘密或渴望，参与者会因此有所触动。
evaluator:
  require: [bard, song_theme, listener]
  max_reward: 0.2
'''

FILES["content/templates/events/lost_child.yaml"] = r'''id: lost_child
tags: [investigation, social]
cooldown: 9
weight: 1.0
conditions:
  - location.has_people >= 4
params:
  participant_count: 3
  location: village_square
prompt: |
  一个孩子走失了，村里人开始寻找。
  线索指向某个隐蔽地点，参与者对其态度各异。
evaluator:
  require: [child, search_party, clue]
  max_reward: 0.3
'''

FILES["content/templates/events/wedding.yaml"] = r'''id: wedding
tags: [celebration, social, romance]
cooldown: 20
weight: 0.7
conditions:
  - director.tension < 0.4
params:
  participant_count: 5
  location: village_square
prompt: |
  两名 NPC 举行婚礼，全村参与。
  仪式中暴露两人之间的往事或未解的心结。
evaluator:
  require: [bride, groom, ceremony_moment]
  max_reward: 0.4
'''

FILES["content/templates/events/funeral.yaml"] = r'''id: funeral
tags: [social, plot, ritual]
cooldown: 18
weight: 0.7
conditions:
  - director.tension > 0.3
params:
  participant_count: 4
  location: village_edge
prompt: |
  一位村民去世，众人送葬。
  吊唁中揭示死者生前未了的愿望，或某位参与者隐藏的愧疚。
evaluator:
  require: [deceased, mourners, unresolved]
  max_reward: 0.3
'''

FILES["content/templates/events/drought.yaml"] = r'''id: drought
tags: [survival, conflict]
cooldown: 25
weight: 0.7
conditions:
  - director.tension > 0.5
params:
  participant_count: 4
  location: village_square
prompt: |
  久旱无雨，井水渐枯，村民开始焦虑。
  至少一名 NPC 提出极端建议，引发争议。
evaluator:
  require: [shortage, proposal, opposition]
  max_reward: 0.5
'''

FILES["content/templates/events/plague_rats.yaml"] = r'''id: plague_rats
tags: [survival, conflict, investigation]
cooldown: 22
weight: 0.75
conditions:
  - director.tension > 0.4
params:
  participant_count: 3
  location: home
prompt: |
  有人在谷仓发现大量死鼠，疑似瘟疫先兆。
  参与者对是否声张产生分歧，怕引发恐慌。
evaluator:
  require: [discovery, response, disagreement]
  max_reward: 0.45
'''

FILES["content/templates/events/stolen_harvest.yaml"] = r'''id: stolen_harvest
tags: [conflict, investigation, daily]
cooldown: 10
weight: 1.0
conditions:
  - director.tension < 0.7
params:
  participant_count: 3
  location: market
prompt: |
  某户人家仓库里的收成被盗，损失惨重。
  现场留下一个指向错误方向的线索，真凶藏在参与者中。
evaluator:
  require: [victim, suspect_pool, false_clue]
  max_reward: 0.35
'''

FILES["content/templates/events/romance_blooms.yaml"] = r'''id: romance_blooms
tags: [romance, social, daily]
cooldown: 6
weight: 1.3
conditions:
  - director.tension < 0.5
params:
  participant_count: 2
  location: forest
prompt: |
  两名 NPC 在僻静处相遇，情愫暗生。
  其中一人已有婚约或牵挂，气氛因此微妙。
evaluator:
  require: [admirer, beloved, obstacle]
  max_reward: 0.2
'''

FILES["content/templates/events/broken_promise.yaml"] = r'''id: broken_promise
tags: [conflict, social, plot]
cooldown: 8
weight: 1.0
conditions:
  - director.tension < 0.8
params:
  participant_count: 3
  location: tavern
prompt: |
  一名 NPC 当众质问另一人为何背弃旧日承诺。
  承诺涉及金钱、婚事或救命之恩，众人围观，气氛紧张。
evaluator:
  require: [accuser, accused, promise_content]
  max_reward: 0.3
'''

FILES["content/templates/events/old_letter.yaml"] = r'''id: old_letter
tags: [mystery, plot, investigation]
cooldown: 5
weight: 1.25
conditions:
  - director.tension < 0.6
params:
  participant_count: 2
  location: home
prompt: |
  一名 NPC 在旧物中发现一封泛黄的信件。
  信的内容指向世界某段被遗忘的历史，或某人刻意隐瞒的过去。
evaluator:
  require: [finder, letter_hint, hidden_truth]
  max_reward: 0.25
'''

FILES["content/templates/events/apprentice_seeks_master.yaml"] = r'''id: apprentice_seeks_master
tags: [social, adventure, daily]
cooldown: 11
weight: 0.9
conditions:
  - director.tension < 0.6
params:
  participant_count: 2
  location: market
prompt: |
  一名年轻 NPC 请求某位老手收自己为徒。
  老手犹豫，原因与一段旧事或未愈的伤有关。
evaluator:
  require: [apprentice, master, hesitation]
  max_reward: 0.25
'''

FILES["content/templates/events/strange_dream.yaml"] = r'''id: strange_dream
tags: [mystery, daily]
cooldown: 4
weight: 1.4
conditions:
  - director.tension < 0.7
params:
  participant_count: 2
  location: home
prompt: |
  一名 NPC 做了怪梦，醒来后心神不宁。
  梦里的场景似乎在预言某件即将发生的事，或与另一位 NPC 相关。
evaluator:
  require: [dreamer, dream_image, omen]
  max_reward: 0.15
'''

FILES["content/templates/events/wolves_at_night.yaml"] = r'''id: wolves_at_night
tags: [survival, conflict, combat]
cooldown: 12
weight: 0.95
conditions:
  - director.tension > 0.4
params:
  participant_count: 4
  location: village_edge
prompt: |
  深夜狼群逼近村口，村民点火驱赶。
  混乱中有人受伤，也有人趁乱做了别的事。
evaluator:
  require: [wolves, defenders, aftermath]
  max_reward: 0.45
'''

FILES["content/templates/events/market_dispute.yaml"] = r'''id: market_dispute
tags: [conflict, daily, trade]
cooldown: 3
weight: 1.5
conditions:
  - director.tension < 0.8
params:
  participant_count: 2
  location: market
prompt: |
  买卖双方因价格或成色争执，引得旁人围观。
  争执背后可能有更深的旧怨，或是有一方在故意挑事。
evaluator:
  require: [buyer, seller, dispute_cause]
  max_reward: 0.15
'''

FILES["content/templates/events/found_treasure_map.yaml"] = r'''id: found_treasure_map
tags: [adventure, mystery, plot]
cooldown: 15
weight: 0.85
conditions:
  - director.tension < 0.7
params:
  participant_count: 3
  location: forest
prompt: |
  有人在森林里发现一张残破的地图，标记着一个隐藏位置。
  地图的真伪无人能辨，参与者对是否结伴寻宝意见不一。
evaluator:
  require: [finder, map_feature, disputed_plan]
  max_reward: 0.35
'''

FILES["content/templates/events/poisoning_suspected.yaml"] = r'''id: poisoning_suspected
tags: [conflict, investigation, plot]
cooldown: 14
weight: 0.85
conditions:
  - director.tension > 0.5
params:
  participant_count: 4
  location: tavern
prompt: |
  一名村民饭后呕吐不止，众人怀疑有人下毒。
  嫌疑集中在几个在场者身上，真凶身份不明。
evaluator:
  require: [victim, suspects, hidden_motive]
  max_reward: 0.4
'''

FILES["content/templates/events/village_election.yaml"] = r'''id: village_election
tags: [political, plot, social]
cooldown: 20
weight: 0.8
conditions:
  - director.tension > 0.4
params:
  participant_count: 5
  location: village_hall
prompt: |
  村庄议会长老换届，几位候选人明争暗斗。
  拉票过程中暴露某人的野心或把柄，玩家会被拉拢。
evaluator:
  require: [candidates, scheme, player_hook]
  max_reward: 0.4
'''

FILES["content/templates/events/wandering_merchant_caravan.yaml"] = r'''id: wandering_merchant_caravan
tags: [trade, daily, social]
cooldown: 8
weight: 1.1
conditions:
  - director.tension < 0.6
params:
  participant_count: 3
  location: market
prompt: |
  一支商队抵达村口，带来稀有货物与远方消息。
  消息中有一条与某位村民或某件旧事直接相关，村民反应不一。
evaluator:
  require: [caravan, exotic_goods, rumor]
  max_reward: 0.25
'''

FILES["content/templates/events/birth_of_child.yaml"] = r'''id: birth_of_child
tags: [celebration, social, ritual]
cooldown: 22
weight: 0.75
conditions:
  - director.tension < 0.5
params:
  participant_count: 4
  location: home
prompt: |
  村里有人添丁，邻居前来道贺。
  新生儿的名字或相貌引发一段旧事被提起，气氛微妙。
evaluator:
  require: [parents, newborn, past_echo]
  max_reward: 0.3
'''

FILES["content/templates/events/execution.yaml"] = r'''id: execution
tags: [conflict, plot, ritual]
cooldown: 30
weight: 0.6
conditions:
  - director.tension > 0.75
params:
  participant_count: 4
  location: village_square
prompt: |
  村庄对一名罪人公开处刑，全村围观。
  罪人的最后陈词揭示一段更深的阴谋或冤屈，有人表情异常。
evaluator:
  require: [condemned, crime, last_words]
  max_reward: 0.6
'''

# ================================================================ i18n 覆盖（含 30 个模板标签）

FILES["server/i18n.py"] = r'''"""中文本地化字典。所有显示层的英文 key → 中文标签映射。

未来加英文支持时，把这里的 value 换成多语言字典即可。
"""

from __future__ import annotations

TRAIT_LABELS: dict[str, str] = {
    "openness": "开放性",
    "conscientiousness": "尽责性",
    "extraversion": "外向性",
    "agreeableness": "宜人性",
    "neuroticism": "神经质",
}

NEED_LABELS: dict[str, str] = {
    "hunger": "饥饿",
    "safety": "安全",
    "social": "社交",
    "wealth": "财富",
    "curiosity": "好奇",
}

TEMPLATE_LABELS: dict[str, str] = {
    # --- 原有 10 个 ---
    "missing_person": "失踪事件",
    "merchant_arrives": "行商到访",
    "bandit_raid": "强盗袭击",
    "lovers_quarrel": "恋人争吵",
    "harvest_festival": "丰收庆典",
    "mysterious_stranger": "神秘陌生人",
    "illness_outbreak": "疫病爆发",
    "treasure_rumor": "宝藏传闻",
    "political_intrigue": "权力斗争",
    "natural_disaster": "自然灾害",
    # --- 新增 20 个 ---
    "traveling_bard": "流浪诗人",
    "lost_child": "走失的孩子",
    "wedding": "村中婚礼",
    "funeral": "送葬",
    "drought": "久旱",
    "plague_rats": "鼠患",
    "stolen_harvest": "收成失窃",
    "romance_blooms": "情愫暗生",
    "broken_promise": "背弃承诺",
    "old_letter": "旧信",
    "apprentice_seeks_master": "学徒求师",
    "strange_dream": "怪梦",
    "wolves_at_night": "狼群夜袭",
    "market_dispute": "市场争执",
    "found_treasure_map": "发现藏宝图",
    "poisoning_suspected": "疑似下毒",
    "village_election": "村长选举",
    "wandering_merchant_caravan": "商队途经",
    "birth_of_child": "添丁之喜",
    "execution": "公开处刑",
}

LOCATION_LABELS: dict[str, str] = {
    "village_square": "村庄广场",
    "market": "市场",
    "tavern": "酒馆",
    "home": "住处",
    "forest": "森林",
    "village_edge": "村庄边缘",
    "village_hall": "村公所",
}

REWARD_KIND_LABELS: dict[str, str] = {
    "item": "物品",
    "relationship": "关系",
    "info": "情报",
    "reputation": "声望",
    "skill": "技能",
    "story": "剧情",
}

STATE_LABELS: dict[str, str] = {
    "pending": "待触发",
    "active": "进行中",
    "resolved": "已完成",
    "rejected": "已拒绝",
}


def trait_label(key: str) -> str:
    return TRAIT_LABELS.get(key, key)


def need_label(key: str) -> str:
    return NEED_LABELS.get(key, key)


def template_label(key: str) -> str:
    return TEMPLATE_LABELS.get(key, key)


def location_label(key: str) -> str:
    return LOCATION_LABELS.get(key, key)


def reward_kind_label(key: str) -> str:
    return REWARD_KIND_LABELS.get(key, key)


def state_label(key: str) -> str:
    return STATE_LABELS.get(key, key)


def all_labels() -> dict[str, dict[str, str]]:
    return {
        "traits": TRAIT_LABELS,
        "needs": NEED_LABELS,
        "templates": TEMPLATE_LABELS,
        "locations": LOCATION_LABELS,
        "reward_kinds": REWARD_KIND_LABELS,
        "states": STATE_LABELS,
    }
'''

# ================================================================ 测试：模板数量 + 覆盖率

FILES["tests/test_template_coverage.py"] = r'''"""校验所有模板都有中文标签，且数量符合预期。"""
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
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    written = 0
    skipped = 0
    for rel, content in FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and not args.force:
            print("[skip]  " + rel)
            skipped += 1
            continue
        p.write_text(content, encoding="utf-8", newline="\n")
        print("[write] " + rel)
        written += 1

    # 统计当前模板数
    events_dir = root / "content/templates/events"
    total = len(list(events_dir.glob("*.yaml")))
    print("\nPart 13 done. written=%d skipped=%d" % (written, skipped))
    print("当前事件模板总数：%d" % total)
    print()
    print("下一步：")
    print("  1. pytest -v")
    print("  2. 重启后端 uvicorn server.main:app --reload")


if globals().get('__name__') == '__main__':
    main()