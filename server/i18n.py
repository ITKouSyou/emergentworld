"""中文本地化字典。"""

from __future__ import annotations

TRAIT_LABELS: dict[str, str] = {
    "openness": "开放性",
    "conscientiousness": "尽责性",
    "extraversion": "外向性",
    "agreeableness": "宜人性",
    "neuroticism": "神经质",
}

NEED_LABELS: dict[str, str] = {
    "hunger": "饥饿", "safety": "安全",
    "social": "社交", "wealth": "财富", "curiosity": "好奇",
}

GENDER_LABELS: dict[str, str] = {
    "male": "男", "female": "女", "unknown": "未知",
}

SEASON_LABELS: dict[str, str] = {
    "spring": "春", "summer": "夏", "autumn": "秋", "winter": "冬",
}

WEATHER_LABELS: dict[str, str] = {
    "clear": "晴", "rain": "雨", "fog": "雾",
    "snow": "雪", "storm": "暴风雨",
}

TEMPLATE_LABELS: dict[str, str] = {
    "missing_person": "失踪事件", "merchant_arrives": "行商到访",
    "bandit_raid": "强盗袭击", "lovers_quarrel": "恋人争吵",
    "harvest_festival": "丰收庆典", "mysterious_stranger": "神秘陌生人",
    "illness_outbreak": "疫病爆发", "treasure_rumor": "宝藏传闻",
    "political_intrigue": "权力斗争", "natural_disaster": "自然灾害",
    "traveling_bard": "流浪诗人", "lost_child": "走失的孩子",
    "wedding": "村中婚礼", "funeral": "送葬", "drought": "久旱",
    "plague_rats": "鼠患", "stolen_harvest": "收成失窃",
    "romance_blooms": "情愫暗生", "broken_promise": "背弃承诺",
    "old_letter": "旧信", "apprentice_seeks_master": "学徒求师",
    "strange_dream": "怪梦", "wolves_at_night": "狼群夜袭",
    "market_dispute": "市场争执", "found_treasure_map": "发现藏宝图",
    "poisoning_suspected": "疑似下毒", "village_election": "村长选举",
    "wandering_merchant_caravan": "商队途经", "birth_of_child": "添丁之喜",
    "execution": "公开处刑",
    "explore": "外出探索",
    "gather": "采集",
    "travel": "前往",
    "hunt": "打猎",
    "train": "修炼",
    "socialize": "社交",
}

LOCATION_LABELS: dict[str, str] = {
    "village_square": "村庄广场", "market": "市场", "tavern": "酒馆",
    "home": "住处", "forest": "森林", "village_edge": "村庄边缘",
    "village_hall": "村公所",
    "deep_forest": "深山老林",
    "old_mine": "废弃矿洞",
    "river_bend": "河湾",
    "old_shrine": "古庙遗址",
    "abandoned_farm": "荒废农舍",
    "mountain_pass": "山道",
}

REWARD_KIND_LABELS: dict[str, str] = {
    "item": "物品", "relationship": "关系", "info": "情报",
    "reputation": "声望", "skill": "技能", "story": "剧情",
}

STATE_LABELS: dict[str, str] = {
    "pending": "待触发", "active": "进行中", "awaiting_player": "等待你",
    "resolved": "已完成", "expired": "已错过", "rejected": "已拒绝",
}


def trait_label(k: str) -> str: return TRAIT_LABELS.get(k, k)
def need_label(k: str) -> str: return NEED_LABELS.get(k, k)
def gender_label(k: str) -> str: return GENDER_LABELS.get(k, k)
def season_label(k: str) -> str: return SEASON_LABELS.get(k, k)
def weather_label(k: str) -> str: return WEATHER_LABELS.get(k, k)
def template_label(k: str) -> str: return TEMPLATE_LABELS.get(k, k)
def location_label(k: str) -> str: return LOCATION_LABELS.get(k, k)
def reward_kind_label(k: str) -> str: return REWARD_KIND_LABELS.get(k, k)
def state_label(k: str) -> str: return STATE_LABELS.get(k, k)


def all_labels() -> dict[str, dict[str, str]]:
    return {
        "traits": TRAIT_LABELS, "needs": NEED_LABELS,
        "genders": GENDER_LABELS, "seasons": SEASON_LABELS,
        "weathers": WEATHER_LABELS, "templates": TEMPLATE_LABELS,
        "locations": LOCATION_LABELS, "reward_kinds": REWARD_KIND_LABELS,
        "states": STATE_LABELS,
    }
