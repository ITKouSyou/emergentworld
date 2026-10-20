"""玩家对事件的三个选项：出手相助 / 静观其变 / 暗中阻挠。

每个选项关联一个属性判定，用玩家的属性值决定结果质量。
"""

from __future__ import annotations

from server.models.schemas import EventTemplate


# tag → 主要属性
TAG_TO_ATTRIBUTE: dict[str, str] = {
    "conflict": "strength",
    "combat": "strength",
    "survival": "agility",
    "social": "charisma",
    "romance": "charisma",
    "trade": "charisma",
    "mystery": "perception",
    "investigation": "intelligence",
    "plot": "intelligence",
    "political": "intelligence",
    "adventure": "agility",
    "daily": "perception",
    "celebration": "charisma",
    "ritual": "perception",
}


CHOICES: dict[str, dict] = {
    "help": {
        "id": "help",
        "label": "出手相助",
        "attribute": "charisma",       # 会被 tag 覆盖
        "difficulty": "normal",
        "tension_delta": -0.05,
        "relation_delta": {"trust": 0.12, "affection": 0.10},
        "reward_multiplier": 1.0,
        "exp_reward": 20,
    },
    "observe": {
        "id": "observe",
        "label": "静观其变",
        "attribute": "perception",
        "difficulty": "easy",
        "tension_delta": 0.0,
        "relation_delta": {},
        "reward_multiplier": 0.5,
        "exp_reward": 5,
    },
    "oppose": {
        "id": "oppose",
        "label": "暗中阻挠",
        "attribute": "agility",
        "difficulty": "hard",
        "tension_delta": 0.08,
        "relation_delta": {"trust": -0.15, "fear": 0.10, "affection": -0.08},
        "reward_multiplier": 1.2,
        "exp_reward": 25,
    },
}


LABEL_OVERRIDES: dict[str, dict[str, str]] = {
    "conflict":   {"help": "挺身而出", "observe": "作壁上观", "oppose": "站在强势一方"},
    "romance":    {"help": "乐见其成", "observe": "不置可否", "oppose": "从中作梗"},
    "investigation": {"help": "协助查案", "observe": "静观其变", "oppose": "隐瞒线索"},
    "trade":      {"help": "促成交易", "observe": "不插手", "oppose": "从中抬价"},
    "political":  {"help": "支持一方", "observe": "保持中立", "oppose": "暗中捣乱"},
    "survival":   {"help": "伸出援手", "observe": "先顾自己", "oppose": "趁乱取利"},
    "celebration": {"help": "共襄盛举", "observe": "远远看着", "oppose": "扫兴而去"},
    "mystery":    {"help": "追查到底", "observe": "按兵不动", "oppose": "掩盖痕迹"},
    "plot":       {"help": "卷入其中", "observe": "暂不表态", "oppose": "搅乱局势"},
    "adventure":  {"help": "结伴同行", "observe": "婉言谢绝", "oppose": "抢先一步"},
    "social":     {"help": "从中调解", "observe": "旁观不语", "oppose": "推波助澜"},
    "daily":      {"help": "帮一把手", "observe": "不闻不问", "oppose": "从中作梗"},
    "combat":     {"help": "并肩作战", "observe": "退到一旁", "oppose": "背后偷袭"},
}


def pick_attribute(tpl: EventTemplate, base_attr: str, cid: str) -> str:
    """根据不同的选项 ID，合理分配属性判定，避免全变成感知"""
    if cid == "help":
        for tag in ("social", "romance", "trade", "daily", "celebration", "political"):
            if tag in tpl.tags: return TAG_TO_ATTRIBUTE[tag]
    elif cid == "observe":
        for tag in ("mystery", "investigation", "plot", "survival"):
            if tag in tpl.tags: return TAG_TO_ATTRIBUTE[tag]
    elif cid == "oppose":
        for tag in ("combat", "conflict", "adventure"):
            if tag in tpl.tags: return TAG_TO_ATTRIBUTE[tag]
            
    # 如果没匹配上特定的分类，就根据标签池兜底
    for tag in tpl.tags:
        if tag in TAG_TO_ATTRIBUTE:
            return TAG_TO_ATTRIBUTE[tag]
    return base_attr


def build_choices(tpl: EventTemplate) -> list[dict]:
    """生成玩家选项列表，并附带属性与难度。"""
    override: dict[str, str] = {}
    for tag in tpl.tags:
        if tag in LABEL_OVERRIDES:
            override = LABEL_OVERRIDES[tag]
            break

    result: list[dict] = []
    for cid in ("help", "observe", "oppose"):
        base = CHOICES[cid]
        attr = pick_attribute(tpl, base["attribute"], cid)
        result.append({
            "id": cid,
            "label": override.get(cid, base["label"]),
            "attribute": attr,
            "attribute_label": _attr_label(attr),
            "difficulty": base["difficulty"],
        })
    return result


def get_choice_spec(choice_id: str) -> dict | None:
    return CHOICES.get(choice_id)


def _attr_label(key: str) -> str:
    from server.models.schemas import ATTRIBUTE_META
    for m in ATTRIBUTE_META:
        if m["key"] == key:
            return m["label"]
    return key
