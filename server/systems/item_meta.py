# 物品分类推断
from __future__ import annotations

# kind → category
CATEGORY_BY_KIND = {
    # 消耗品
    "食材": "consumable",
    "食物": "consumable",
    "药材": "consumable",
    "药": "consumable",
    "酒": "consumable",
    # 装备
    "工具": "equipment",
    "武器": "equipment",
    "甲": "equipment",
    "甲胄": "equipment",
    "饰物": "equipment",
    # 材料
    "矿石": "material",
    "布料": "material",
    "材料": "material",
    "燃料": "material",
    "杂物": "material",
    "肥料": "material",
    # 特殊
    "信物": "quest",
    "古物": "quest",
    "钥匙": "key",
}

# kind → use_effect（consumable 时）
EFFECT_BY_KIND = {
    "食材": {"hunger": -0.3},
    "食物": {"hunger": -0.4, "hp": 5},
    "药材": {"hp": 15},
    "药": {"hp": 25},
    "酒": {"hp": 5, "hunger": -0.1},
}

# kind → slot（equipment 时）
SLOT_BY_KIND = {
    "工具": "tool",
    "武器": "weapon",
    "甲": "armor",
    "甲胄": "armor",
    "饰物": "accessory",
}


def infer_category(kind: str) -> str:
    return CATEGORY_BY_KIND.get(kind, "material")


def infer_effect(kind: str) -> dict:
    return dict(EFFECT_BY_KIND.get(kind, {}))


def infer_slot(kind: str) -> str:
    return SLOT_BY_KIND.get(kind, "")


def has_durability(kind: str) -> bool:
    """只有 equipment 才有耐久。"""
    return infer_category(kind) == "equipment"
