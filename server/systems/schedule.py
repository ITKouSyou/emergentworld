# NPC 日程表：按时段规定去哪
from __future__ import annotations

import random

from server.models.schemas import NPC

# 时段划分（按小时）
SLOTS = {
    "morning": (6, 11),
    "afternoon": (11, 17),
    "evening": (17, 21),
    "night": (21, 6),  # 跨夜
}


def slot_of_hour(hour: int) -> str:
    h = hour % 24
    if 6 <= h < 11:
        return "morning"
    if 11 <= h < 17:
        return "afternoon"
    if 17 <= h < 21:
        return "evening"
    return "night"


def generate_schedule(npc: NPC, rng: random.Random) -> dict[str, str]:
    """根据性格、目标、家庭生成日程。"""
    goals_text = " ".join(npc.goals).lower()
    traits = npc.traits or {}
    extraversion = float(traits.get("extraversion", 0.5))
    openness = float(traits.get("openness", 0.5))

    has_home = bool(npc.family.spouse or npc.family.children or npc.family.parents)
    is_elder = npc.age >= 55
    is_child = npc.age < 16

    schedule: dict[str, str] = {}

    # --- 白天（morning + afternoon）---
    if is_child:
        day_loc = rng.choice(["village_square", "orchard", "brook", "mill", "well"])
    elif is_elder:
        day_loc = rng.choice(["home", "village_square", "market"])
    elif any(kw in goals_text for kw in ["钱", "wealth", "攒", "生意", "商"]):
        day_loc = "market"
    elif any(kw in goals_text for kw in ["探索", "寻", "冒险", "旅", "查", "远"]):
        day_loc = rng.choice(["forest", "village_edge", "market"])
    elif any(kw in goals_text for kw in ["手艺", "徒", "技"]):
        day_loc = "market"
    else:
        if openness > 0.6:
            day_loc = rng.choice([
                "forest", "village_square", "market",
                "brook", "bamboo_grove", "old_road",
            ])
        else:
            day_loc = rng.choice([
                "market", "home", "village_hall",
                "mill", "smithy", "dye_works",
                "farm_field", "pasture", "well",
            ])

    schedule["morning"] = day_loc
    schedule["afternoon"] = day_loc

    # --- 傍晚 ---
    if is_child or is_elder:
        schedule["evening"] = "home"
    elif extraversion > 0.6:
        schedule["evening"] = rng.choice(["tavern", "village_square", "tavern"])
    elif any(kw in goals_text for kw in ["酒", "乐", "朋友", "社交"]):
        schedule["evening"] = "tavern"
    else:
        schedule["evening"] = rng.choice(["tavern", "village_square", "home"])

    # --- 夜里 ---
    # 有家的人基本都回家
    if has_home:
        schedule["night"] = "home"
    elif extraversion > 0.7 and rng.random() < 0.3:
        schedule["night"] = "tavern"  # 夜猫子
    else:
        schedule["night"] = "home"

    return schedule


def target_location(npc: NPC, hour: int) -> str:
    """根据当前小时，返回 NPC 该去的地方。"""
    if not npc.schedule:
        return npc.location_id
    slot = slot_of_hour(hour)
    return npc.schedule.get(slot, npc.location_id)


def describe_schedule(npc: NPC) -> list[str]:
    """给前端显示用。"""
    if not npc.schedule:
        return []
    labels = {
        "morning": "清晨",
        "afternoon": "白天",
        "evening": "傍晚",
        "night": "夜里",
    }
    loc_labels = {
        "village_square": "村庄广场",
        "market": "市场",
        "tavern": "酒馆",
        "home": "住处",
        "forest": "森林",
        "village_edge": "村庄边缘",
        "village_hall": "村公所",
        "well": "井边",
        "mill": "磨坊",
        "smithy": "铁匠铺",
        "dye_works": "染坊",
        "farm_field": "农田",
        "orchard": "果园",
        "pasture": "牧场",
        "brook": "小溪",
        "deep_forest": "深山老林",
        "old_mine": "废弃矿洞",
        "river_bend": "河湾",
        "old_shrine": "古庙遗址",
        "abandoned_farm": "荒废农舍",
        "mountain_pass": "山道",
        "waterfall": "瀑布",
        "cliff": "断崖",
        "stone_forest": "石林",
        "old_road": "古道",
        "ancient_grave": "荒坟",
        "quarry": "采石场",
        "salt_flat": "盐碱地",
        "ferry": "野渡",
        "bamboo_grove": "竹林",
        "hot_spring": "温泉",
    }
    result = []
    for slot in ["morning", "afternoon", "evening", "night"]:
        loc = npc.schedule.get(slot)
        if not loc:
            continue
        label = labels.get(slot, slot)
        loc_zh = loc_labels.get(loc, loc)
        result.append("%s：%s" % (label, loc_zh))
    return result
