# Part 75B：8 个季节专属事件
from pathlib import Path

# 加 i18n 标签
p = Path("server/i18n.py")
t = p.read_text(encoding="utf-8")

new_labels = {
    "spring_plowing": "春耕",
    "spring_blossom": "踏春赏花",
    "summer_swim": "结伴游水",
    "summer_night_market": "夜市",
    "autumn_hunt": "秋猎",
    "autumn_harvest_market": "秋集",
    "winter_snowstorm": "暴雪封路",
    "winter_wolves": "雪夜狼群",
}

# 找 TEMPLATE_LABELS 的 `}` 结束位置
anchor = '    "explore": "外出探索",\n'
if anchor in t and '"spring_plowing"' not in t:
    # 加到 explore 之后
    addition = ''.join('    "%s": "%s",\n' % (k, v) for k, v in new_labels.items())
    t = t.replace(anchor, anchor + addition, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] i18n 加 8 个季节事件标签")
else:
    print("[skip] i18n 已改过")

# 写事件模板
events_dir = Path("content/templates/events")
events_dir.mkdir(parents=True, exist_ok=True)

def _yaml(id_, tags, cooldown, weight, conditions, params, prompt, evaluator, interactive=True):
    def _list(items, indent=2):
        pad = " " * indent
        return "\n".join("%s- %s" % (pad, x) for x in items) if items else pad + "[]"
    tag_str = "[" + ", ".join(tags) + "]"
    params_str = "\n".join("  %s: %s" % (k, v) for k, v in params.items())
    prompt_str = "\n".join("  " + line for line in prompt.splitlines())
    eval_str = "\n".join("  %s: %s" % (k, v) for k, v in evaluator.items())
    return (
        "id: %s\n" % id_
        + "tags: %s\n" % tag_str
        + "cooldown: %d\n" % cooldown
        + "weight: %s\n" % weight
        + "interactive: %s\n" % ("true" if interactive else "false")
        + "conditions:\n" + _list(conditions) + "\n"
        + "params:\n" + params_str + "\n"
        + "prompt: |\n" + prompt_str + "\n"
        + "evaluator:\n" + eval_str + "\n"
    )

FILES = {}

FILES["spring_plowing.yaml"] = _yaml(
    "spring_plowing", ["daily", "social"], 15, 1.0,
    ['world.season == "spring"'],
    {"participant_count": 3, "location": "market"},
    "春耕开始，村里几家在争牛、争水、争人手。\n有人当众抱怨，也有人出面调解。",
    {"require": "[dispute, mediator, agreement]", "max_reward": 0.2},
)

FILES["spring_blossom.yaml"] = _yaml(
    "spring_blossom", ["romance", "social", "daily"], 12, 1.1,
    ['world.season == "spring"'],
    {"participant_count": 2, "location": "forest"},
    "春暖花开，两名年轻 NPC 不约而同来到林间赏花。\n其中一人心事重重，另一人试图安慰。",
    {"require": "[youth_a, youth_b, mood]", "max_reward": 0.15},
)

FILES["summer_swim.yaml"] = _yaml(
    "summer_swim", ["daily", "social", "adventure"], 10, 1.0,
    ['world.season == "summer"'],
    {"participant_count": 3, "location": "river_bend"},
    "夏日炎热，几个村人相约到河湾戏水。\n有人不慎呛水，众人慌乱。",
    {"require": [1, 2, 3], "max_reward": 0.2},
)

FILES["summer_night_market.yaml"] = _yaml(
    "summer_night_market", ["trade", "social", "celebration"], 18, 1.1,
    ['world.season == "summer"'],
    {"participant_count": 4, "location": "market"},
    "夏夜村庄办起夜市，商贩、说书人、江湖郎中齐聚。\n有陌生人混入其中，带来远方消息。",
    {"require": [1, 2, 3], "max_reward": 0.25},
)

FILES["autumn_hunt.yaml"] = _yaml(
    "autumn_hunt", ["adventure", "social", "celebration"], 20, 1.2,
    ['world.season == "autumn"'],
    {"participant_count": 4, "location": "forest"},
    "秋猎开锣，村里男丁结伴入林。\n有人争功，有人遇险，也有人暗中做手脚。",
    {"require": [1, 2, 3], "max_reward": 0.35},
)

FILES["autumn_harvest_market.yaml"] = _yaml(
    "autumn_harvest_market", ["trade", "daily", "celebration"], 15, 1.3,
    ['world.season == "autumn"'],
    {"participant_count": 3, "location": "market"},
    "秋收大集，外地商贩云集。\n有人趁机哄抬物价，也有人掏出稀奇货物。",
    {"require": [1, 2, 3], "max_reward": 0.3},
)

FILES["winter_snowstorm.yaml"] = _yaml(
    "winter_snowstorm", ["survival", "conflict"], 25, 1.2,
    ['world.season == "winter"'],
    {"participant_count": 4, "location": "village_square"},
    "暴雪封路，村中柴火与粮食告急。\n众人为分粮争论，有人提出极端方案。",
    {"require": [1, 2, 3], "max_reward": 0.5},
)

FILES["winter_wolves.yaml"] = _yaml(
    "winter_wolves", ["survival", "combat"], 22, 1.1,
    ['world.season == "winter"'],
    {"participant_count": 4, "location": "village_edge"},
    "寒冬时节，饿狼成群落进村口。\n众人点起火把驱赶，但狼群不愿离去。",
    {"require": [1, 2, 3], "max_reward": 0.5},
)

for name, content in FILES.items():
    (events_dir / name).write_text(content, encoding="utf-8")
    print("[write] content/templates/events/%s" % name)

print()
print("B 完成。测试：pytest -v")