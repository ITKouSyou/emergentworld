# 玩家行动：探索、采集、打猎、修炼、社交
from __future__ import annotations

import json
import random
import uuid

from sqlmodel import Session

from server.i18n import location_label
from server.map_layout import hidden_location_ids
from server.models.db import WorldRow
from server.models.schemas import Player, World
from server.systems import player as player_sys


ACTION_META = {
    "explore":   {"label": "外出探索", "attribute": "perception", "difficulty": "normal", "desc": "寻找未知的地方"},
    "gather":    {"label": "采集",     "attribute": "perception", "difficulty": "easy",   "desc": "在当前区域收集材料"},
    "hunt":      {"label": "打猎",     "attribute": "agility",    "difficulty": "normal", "desc": "追捕野生动物"},
    "train":     {"label": "修炼",     "attribute": "strength",   "difficulty": "easy",   "desc": "锻炼身体"},
    "socialize": {"label": "社交",     "attribute": "charisma",   "difficulty": "easy",   "desc": "与附近的人交谈"},
}


EXPLORE_DIFFICULTY = {
    "deep_forest": "normal", "old_mine": "normal", "river_bend": "easy",
    "old_shrine": "hard", "abandoned_farm": "easy", "mountain_pass": "hard",
}

EXPLORE_FLAVORS = {
    "deep_forest": "幽深的林间，你拨开纠缠的藤蔓。",
    "old_mine": "废矿的入口塌了一半，空气里满是铁锈味。",
    "river_bend": "河水在此拐弯，冲积出一片细沙滩。",
    "old_shrine": "残破的神像倒在草丛里，香炉早已冰冷。",
    "abandoned_farm": "农舍的屋顶已经塌了，院里的井还盖着。",
    "mountain_pass": "山风呼啸，一条小径隐没在云雾里。",
}

GATHER_POOL = {
    "village_square": [("野草", "草药"), ("旧铜钱", "古物"), ("小石子", "杂物")],
    "market": [("散落铜钱", "杂物"), ("碎布头", "布料")],
    "tavern": [("空酒壶", "杂物"), ("木屑", "杂物")],
    "home": [("旧布", "布料"), ("柴火", "燃料")],
    "forest": [("松果", "食材"), ("野菌", "食材"), ("草药", "草药")],
    "village_edge": [("柴火", "燃料"), ("鸟蛋", "食材")],
    "village_hall": [("旧纸", "杂物")],
    "deep_forest": [("百年参", "药材"), ("鹿茸", "药材")],
    "old_mine": [("铁矿", "矿石"), ("煤块", "燃料")],
    "river_bend": [("河蚌", "食材"), ("芦苇", "材料")],
    "old_shrine": [("香灰", "信物"), ("古钱", "古物")],
    "abandoned_farm": [("干草", "材料"), ("旧钉", "杂物")],
    "mountain_pass": [("云母石", "矿石"), ("野草", "草药")],
    # 新增
    "well": [("青苔", "草药"), ("水草", "药材")],
    "mill": [("麦糠", "食材"), ("碎麦", "食材")],
    "smithy": [("铁屑", "矿石"), ("废铁片", "矿石")],
    "dye_works": [("染料渣", "材料"), ("靛蓝碎", "材料")],
    "farm_field": [("麦穗", "食材"), ("野菜", "食材"), ("稻草", "材料")],
    "orchard": [("野果", "食材"), ("苹果", "食材"), ("青杏", "食材")],
    "pasture": [("干草", "材料"), ("羊粪", "肥料")],
    "brook": [("小鱼", "食材"), ("河虾", "食材")],
    "waterfall": [("寒石", "矿石"), ("飞瀑草", "药材")],
    "cliff": [("岩盐", "食材"), ("白铁矿", "矿石")],
    "stone_forest": [("玄石", "矿石"), ("黑曜碎石", "矿石")],
    "old_road": [("旅人遗物", "杂物"), ("铜钱", "古物")],
    "ancient_grave": [("陪葬陶片", "古物"), ("锈剑", "古物")],
    "quarry": [("花岗石", "矿石"), ("石灰", "材料")],
    "salt_flat": [("盐晶", "食材"), ("卤水", "药材")],
    "ferry": [("断船木", "材料"), ("渔网残片", "材料")],
    "bamboo_grove": [("竹节", "材料"), ("竹笋", "食材")],
    "hot_spring": [("硫磺块", "药材"), ("温石", "矿石")],
}

HUNT_POOL = {
    "forest": [("野兔", "猎物"), ("山鸡", "猎物")],
    "village_edge": [("野兔", "猎物")],
    "deep_forest": [("野鹿", "猎物"), ("野猪", "猎物")],
    "mountain_pass": [("岩羊", "猎物")],
    "farm_field": [("野兔", "猎物"), ("田鼠", "猎物")],
    "orchard": [("野鸟", "猎物"), ("松鼠", "猎物")],
    "pasture": [("野兔", "猎物")],
    "brook": [("河鱼", "猎物"), ("水鸭", "猎物")],
    "cliff": [("山鹰", "猎物")],
    "stone_forest": [("岩蛇", "猎物"), ("石羊", "猎物")],
    "bamboo_grove": [("竹鼠", "猎物"), ("竹鸡", "猎物")],
    "ferry": [("江鲤", "猎物")],
    "hot_spring": [("温泉蛙", "猎物")],
    "waterfall": [("溪鱼", "猎物")],
    "quarry": [("岩鸽", "猎物")],
    "salt_flat": [("沙狐", "猎物")],
}


def _apply_growth(session, world, player, action_result: dict, rng):
    """行动完成后，根据判定结果尝试属性成长。"""
    check = action_result.get("check")
    if not check or not isinstance(check, dict):
        return

    result = check.get("result")
    attribute = check.get("attribute")
    if not result or not attribute:
        return

    grew = player_sys.try_natural_growth(
        session, player, attribute, result, rng,
    )
    if grew:
        action_result["attribute_growth"] = {
            "attribute": attribute,
            "attribute_label": _attr_label(attribute),
            "new_value": int(player.attributes.get(attribute, 5)),
        }


def _attr_label(key: str) -> str:
    return {
        "strength": "力量",
        "agility": "敏捷",
        "intelligence": "智慧",
        "perception": "感知",
        "charisma": "魅力",
        "luck": "运气",
    }.get(key, key)


def get_discovered(session: Session, world_id: str) -> list[str]:
    row = session.get(WorldRow, world_id)
    if row is None:
        return []
    return json.loads(row.location_ids_json or "[]")


def add_discovered(session: Session, world_id: str, loc_id: str) -> None:
    row = session.get(WorldRow, world_id)
    if row is None:
        return
    cur = json.loads(row.location_ids_json or "[]")
    if loc_id not in cur:
        cur.append(loc_id)
    row.location_ids_json = json.dumps(cur, ensure_ascii=False)
    session.add(row)
    session.commit()


def _make_item(name: str, kind: str, story: str, rng: random.Random) -> dict:
    affixes = rng.sample(["古老的", "磨损的", "新鲜的", "常见的"], 1)
    return {
        "id": "itm_%s" % uuid.uuid4().hex[:8],
        "name": name, "kind": kind, "affixes": affixes,
        "story": story, "value": round(rng.uniform(0.05, 0.4), 2),
    }


def _pick_undiscovered(session, world, rng):
    discovered = get_discovered(session, world.id)
    candidates = [loc for loc in hidden_location_ids() if loc not in discovered]
    if not candidates:
        return None
    return rng.choice(candidates)


async def do_action(session: Session, world: World, player: Player, action: str) -> dict:
    rng = random.Random(world.seed * 77771 + world.tick * 13 + hash(action))
    if action not in ACTION_META:
        return {"ok": False, "error": "unknown action: %s" % action}

    meta = ACTION_META[action]
    origin = player.location_id or "village_square"

    result = {
        "ok": True, "kind": action,
        "action_label": meta["label"],
        "origin": origin,
        "origin_label": location_label(origin),
        "check": None, "found_location": None, "found_item": None,
        "message": "", "exp_gain": 0, "summary": "",
        "target_id": "", "target_label": "", "flavor": "",
    }

    if action == "explore":
        out = await _do_explore(session, world, player, origin, rng, result)
    elif action == "gather":
        out = _do_gather(session, world, player, origin, rng, result)
    elif action == "hunt":
        out = _do_hunt(session, world, player, origin, rng, result)
    elif action == "train":
        out = _do_train(session, world, player, rng, result)
    elif action == "socialize":
        out = _do_socialize(session, world, player, rng, result)
    else:
        out = result

    _apply_growth(session, world, player, out, rng)
    return out


async def _do_explore(session, world, player, origin, rng, result):
    target = _pick_undiscovered(session, world, rng)
    if target is None:
        result["message"] = "附近的地界你已经走遍了。"
        result["summary"] = "你四处走了走，但附近已经没什么新鲜的了。"
        return result

    difficulty = EXPLORE_DIFFICULTY.get(target, "normal")
    check = player_sys.roll_check(player, "perception", difficulty, rng)
    result["check"] = check
    result["target_id"] = target
    result["target_label"] = location_label(target)
    result["flavor"] = EXPLORE_FLAVORS.get(target, "你向前走去。")

    if check["result"] == "critical":
        add_discovered(session, world.id, target)
        if target not in world.location_ids:
            world.location_ids.append(target)
        player.location_id = target
        player_sys.save_player(session, player)
        result["found_location"] = True
        name, kind = rng.choice([("草药", "草药"), ("旧物", "古物")])
        result["found_item"] = _make_item(name, kind, "从%s带回。" % location_label(target), rng)
        result["message"] = "你不仅找到了入口，还捡到了一件东西。"
        result["exp_gain"] = 30
        result["summary"] = "你发现了【%s】" % location_label(target)
    elif check["result"] == "success":
        add_discovered(session, world.id, target)
        if target not in world.location_ids:
            world.location_ids.append(target)
        player.location_id = target
        player_sys.save_player(session, player)
        result["found_location"] = True
        result["message"] = "你发现了新的去处。"
        result["exp_gain"] = 20
        result["summary"] = "你发现了【%s】" % location_label(target)
    elif check["result"] == "partial":
        result["message"] = "你察觉到一点踪迹，但没能深入。"
        result["exp_gain"] = 8
        result["summary"] = "你循着一些痕迹找了找，但没能找到什么"
    else:
        result["message"] = "你一无所获，还浪费了半天。"
        result["exp_gain"] = 2
        result["summary"] = "你在附近转了一圈，没什么发现"

    if result["exp_gain"] > 0:
        player_sys.add_exp(session, result["exp_gain"])
    return result


def _do_gather(session, world, player, origin, rng, result):
    pool = GATHER_POOL.get(origin, [("杂物", "杂物")])
    check = player_sys.roll_check(player, "perception", "easy", rng)
    result["check"] = check

    if check["result"] in ("critical", "success"):
        name, kind = rng.choice(pool)
        result["found_item"] = _make_item(name, kind, "在%s捡到。" % location_label(origin), rng)
        result["message"] = "你在附近捡到了一些东西。"
        result["exp_gain"] = 10 if check["result"] == "success" else 15
        result["summary"] = "你在%s采集到【%s】" % (location_label(origin), name)
    elif check["result"] == "partial":
        result["message"] = "你找了一阵，没找到什么有用的。"
        result["exp_gain"] = 5
        result["summary"] = "你在%s采集了一阵，所获不多" % location_label(origin)
    else:
        result["message"] = "你什么都没找到。"
        result["exp_gain"] = 2
        result["summary"] = "你在%s采集，一无所获" % location_label(origin)

    if result["exp_gain"] > 0:
        player_sys.add_exp(session, result["exp_gain"])
    return result


def _do_hunt(session, world, player, origin, rng, result):
    pool = HUNT_POOL.get(origin)
    if not pool:
        hint_map = {
            "old_mine": "矿洞里没有猎物，得去森林或山道",
            "river_bend": "河湾只有鱼虾，用打猎的方式不顶用",
            "deep_forest": "密林深处可以打猎",
        }
        hint = hint_map.get(origin, "这里没有猎物，去森林或山道这类地方才行。")
        result["message"] = hint
        result["summary"] = "你在%s想打猎，但这里没猎物" % location_label(origin)
        player_sys.add_exp(session, 2)
        result["exp_gain"] = 2
        return result

    # 第一步：潜行（敏捷）
    stealth = player_sys.roll_check(player, "agility", "normal", rng)
    result["check"] = stealth

    if stealth["result"] in ("critical", "success"):
        name, kind = rng.choice(pool)
        result["found_item"] = _make_item(name, kind, "在%s猎得。" % location_label(origin), rng)
        result["exp_gain"] = 25 if stealth["result"] == "critical" else 15
        result["message"] = "你悄无声息地接近了猎物，一击得手。"
        result["summary"] = "你在%s猎得【%s】" % (location_label(origin), name)
        player_sys.add_exp(session, result["exp_gain"])
        return result

    if stealth["result"] == "partial":
        result["message"] = "你追了一阵，猎物跑掉了。"
        result["exp_gain"] = 8
        result["summary"] = "你在%s打猎，追了一阵，猎物跑了" % location_label(origin)
        player_sys.add_exp(session, result["exp_gain"])
        return result

    # 失败：激怒野兽，进入战斗
    beasts_by_loc = {
        "forest": [("野猪", 12, 2), ("野狼", 10, 3)],
        "deep_forest": [("野猪王", 20, 4), ("黑熊", 25, 5), ("猛虎", 30, 6)],
        "village_edge": [("流浪狗", 8, 1)],
        "mountain_pass": [("岩羊", 15, 3), ("山魈", 18, 4)],
    }
    beasts = beasts_by_loc.get(origin, [("野兽", 10, 2)])
    beast_name, beast_hp, beast_atk = rng.choice(beasts)

    # 按等级选难度：1-2 级 normal，3-5 级 hard，6+ heroic
    lv = int(player.level)
    if lv <= 2:
        combat_diff = "normal"
    elif lv <= 5:
        combat_diff = "hard"
    else:
        combat_diff = "heroic"
    combat_check = player_sys.roll_check(player, "strength", combat_diff, rng)
    result["check"] = combat_check
    result["combat"] = {
        "enemy": beast_name,
        "enemy_hp": beast_hp,
        "enemy_attack": beast_atk,
        "result": combat_check["result"],
    }

    beast_damage = max(1, beast_atk + rng.randint(-1, 2))
    hp_before = player.hp

    if combat_check["result"] == "critical":
        name, kind = rng.choice(pool)
        result["found_item"] = _make_item(name, kind, "在%s搏斗中猎得。" % location_label(origin), rng)
        result["exp_gain"] = 40
        result["message"] = "你一拳打倒了%s，干净利落地解决了战斗。" % beast_name
        result["summary"] = "你在%s徒手斗杀【%s】，猎得【%s】" % (
            location_label(origin), beast_name, name)
    elif combat_check["result"] == "success":
        player.hp = max(1, player.hp - beast_damage // 2)
        name, kind = rng.choice(pool)
        result["found_item"] = _make_item(name, kind, "在%s搏斗中猎得。" % location_label(origin), rng)
        result["exp_gain"] = 30
        result["message"] = "你打退了%s，自己也擦破了皮。" % beast_name
        result["summary"] = "你在%s与【%s】搏斗获胜" % (location_label(origin), beast_name)
    elif combat_check["result"] == "partial":
        player.hp = max(1, player.hp - beast_damage)
        result["exp_gain"] = 15
        result["message"] = "你和%s缠斗，受了不轻的伤，它跑了。" % beast_name
        result["summary"] = "你在%s与【%s】缠斗，受伤但活了下来" % (
            location_label(origin), beast_name)
    else:
        player.hp = max(1, player.hp - beast_damage * 2)
        result["exp_gain"] = 5
        result["message"] = "你被%s扑倒，勉强爬起逃回村口。" % beast_name
        result["summary"] = "你在%s被【%s】重伤" % (location_label(origin), beast_name)
        player.location_id = "village_square"

    result["hp_before"] = hp_before
    result["hp_after"] = player.hp
    result["damage"] = hp_before - player.hp

    # 濒死：强制回村并回复一半
    if player.hp <= 1:
        player.hp = max(1, player.max_hp // 2)
        result["message"] += "（你昏睡了许久，醒来时已被人抬回了村里）"
        player.location_id = "village_square"
        result["hp_after"] = player.hp

    player_sys.save_player(session, player)
    player_sys.add_exp(session, result["exp_gain"])
    return result


def _do_train(session, world, player, rng, result):
    check = player_sys.roll_check(player, "strength", "easy", rng)
    result["check"] = check
    if check["result"] == "critical":
        result["message"] = "你感觉自己比昨天更强了一点。"
        result["exp_gain"] = 35
        result["summary"] = "你练了一阵子武，颇有收获"
    elif check["result"] == "success":
        result["message"] = "你练了一阵。"
        result["exp_gain"] = 25
        result["summary"] = "你练了一阵子武"
    elif check["result"] == "partial":
        result["message"] = "你练得有点累。"
        result["exp_gain"] = 12
        result["summary"] = "你练了一会儿"
    else:
        result["message"] = "你心不在焉，没练出什么。"
        result["exp_gain"] = 5
        result["summary"] = "你勉强练了一会儿"
    player_sys.add_exp(session, result["exp_gain"])
    return result


def _do_socialize(session, world, player, rng, result):
    check = player_sys.roll_check(player, "charisma", "easy", rng)
    result["check"] = check
    if check["result"] == "critical":
        result["message"] = "你和几位村人相谈甚欢。"
        result["exp_gain"] = 20
        result["summary"] = "你和村人谈得很愉快"
    elif check["result"] == "success":
        result["message"] = "你和几个人聊了聊。"
        result["exp_gain"] = 12
        result["summary"] = "你和村人闲聊了一阵"
    elif check["result"] == "partial":
        result["message"] = "你和人聊了几句，没什么收获。"
        result["exp_gain"] = 6
        result["summary"] = "你和村人聊了几句"
    else:
        result["message"] = "你说话没什么人接。"
        result["exp_gain"] = 2
        result["summary"] = "你想找人聊天，但大家都忙"
    player_sys.add_exp(session, result["exp_gain"])
    return result
