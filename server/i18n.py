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
    "wandering_orphan": "流浪孤儿",
    "strange_visitor": "怪客",
    "hidden_treasure": "隐藏宝藏",
    "cursed_item": "被诅咒之物",
    "old_ghost_story": "鬼故事",
    "mysterious_letter": "神秘信件",
    "new_law": "新法",
    "tax_collection": "收税",
    "land_dispute": "土地纠纷",
    "village_meeting": "村民大会",
    "prophecy_dream": "预言梦",
    "wandering_monk": "游方僧人",
    "gossip_mill": "磨坊闲话",
    "old_friends_reunion": "老友重逢",
    "neighbor_dispute": "邻里纠纷",
    "child_play": "孩童玩耍",
    "family_dinner": "家宴",
    "well_gathering": "井边闲谈",
    "night_watch": "守夜",
    "debt_collection": "讨债",
    "stolen_goods": "赃物交易",
    "inheritance": "遗产分配",
    "business_partnership": "合伙生意",
    "rare_item_sale": "珍品拍卖",
    "drunk_brawl": "酒后斗殴",
    "theft_accusation": "偷窃指控",
    "animal_attack": "野兽袭击",
    "fire_outbreak": "火灾",
    "secret_love": "暗恋",
    "jealous_husband": "醋意",
    "married_couple_dispute": "夫妻矛盾",
    "return_of_exile": "归乡者",
    "spring_plowing": "春耕",
    "spring_blossom": "踏春赏花",
    "summer_swim": "结伴游水",
    "summer_night_market": "夜市",
    "autumn_hunt": "秋猎",
    "autumn_harvest_market": "秋集",
    "winter_snowstorm": "暴雪封路",
    "winter_wolves": "雪夜狼群",
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
    "well": "井边",
    "mill": "磨坊",
    "smithy": "铁匠铺",
    "dye_works": "染坊",
    "farm_field": "农田",
    "orchard": "果园",
    "pasture": "牧场",
    "brook": "小溪",
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
def template_label(k: str) -> str:
    if k in TEMPLATE_LABELS:
        return TEMPLATE_LABELS[k]
    try:
        from server.core import director
        for tpl in director.load_templates():
            if tpl.id == k and getattr(tpl, "label", ""):
                return tpl.label
    except Exception:
        pass
    return k

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
