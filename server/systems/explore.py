# 探索系统
from __future__ import annotations

import json
import random
import uuid

from sqlmodel import Session

from server.i18n import location_label
from server.map_layout import LOCATION_LAYOUT, hidden_location_ids
from server.models.db import WorldRow
from server.models.schemas import Player, World
from server.systems import player as player_sys

LOCATION_DIFFICULTY = {
    "deep_forest": "normal",
    "old_mine": "normal",
    "river_bend": "easy",
    "old_shrine": "hard",
    "abandoned_farm": "easy",
    "mountain_pass": "hard",
    "waterfall": "normal",
    "cliff": "hard",
    "stone_forest": "hard",
    "old_road": "normal",
    "ancient_grave": "hard",
    "quarry": "normal",
    "salt_flat": "easy",
    "ferry": "normal",
    "bamboo_grove": "easy",
    "hot_spring": "normal",
}

LOCATION_FLAVORS = {
    "deep_forest": "幽深的林间，你拨开纠缠的藤蔓。",
    "old_mine": "废矿的入口塌了一半，空气里满是铁锈味。",
    "river_bend": "河水在此拐弯，冲积出一片细沙滩。",
    "old_shrine": "残破的神像倒在草丛里，香炉早已冰冷。",
    "abandoned_farm": "农舍的屋顶已经塌了，院里的井还盖着。",
    "mountain_pass": "山风呼啸，一条小径隐没在云雾里。",
    "waterfall": "水声轰鸣，白练从高处跌落深潭。",
    "cliff": "陡峭的岩壁直插云霄，脚下是深渊。",
    "stone_forest": "嶙峋的石柱林立，像是巨人的森林。",
    "old_road": "青苔覆盖的古道通向远方，车辙已模糊。",
    "ancient_grave": "荒草掩映的坟冢错落而立，碑上字迹难辨。",
    "quarry": "采石留下的巨坑里积水成潭，石壁刀削般整齐。",
    "salt_flat": "白色盐壳覆盖大地，远处的空气扭曲着。",
    "ferry": "老渡口只剩半截木桩，江水缓缓拍打。",
    "bamboo_grove": "翠竹成片，风吹过沙沙作响。",
    "hot_spring": "热气从地表涌起，水面泛着硫磺色的光。",
}


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


def pick_undiscovered_location(session, world, rng):
    discovered = get_discovered(session, world.id)
    candidates = [loc for loc in hidden_location_ids() if loc not in discovered]
    if not candidates:
        return None
    return rng.choice(candidates)


async def explore_once(session: Session, world: World, player: Player) -> dict:
    rng = random.Random(world.seed * 77771 + world.tick)
    origin = player.location_id or "village_square"
    target = pick_undiscovered_location(session, world, rng)
    if target is None:
        return {
            "ok": True,
            "kind": "no_more",
            "message": "附近的地界你已经走遍了。",
            "check": None,
            "found_location": False,
            "found_item": None,
            "exp_gain": 0,
        }

    difficulty = LOCATION_DIFFICULTY.get(target, "normal")
    check = player_sys.roll_check(player, "perception", difficulty, rng)
    result = check["result"]
    flavor = LOCATION_FLAVORS.get(target, "你向前走去。")

    response = {
        "ok": True,
        "kind": "explore",
        "origin": origin,
        "origin_label": location_label(origin),
        "target_id": target,
        "target_label": location_label(target),
        "check": check,
        "flavor": flavor,
        "found_location": False,
        "found_item": None,
        "message": "",
        "exp_gain": 0,
    }

    if result == "critical":
        add_discovered(session, world.id, target)
        # 同步内存对象，避免后面 save_world 覆盖
        if target not in world.location_ids:
            world.location_ids.append(target)
        # 玩家移动到新地点
        player.location_id = target
        player_sys.save_player(session, player)
        response["found_location"] = True
        response["found_item"] = _generate_find_item(target, rng)
        response["message"] = "你不仅找到了入口，还捡到了一件东西。"
        response["exp_gain"] = 30
    elif result == "success":
        add_discovered(session, world.id, target)
        if target not in world.location_ids:
            world.location_ids.append(target)
        player.location_id = target
        player_sys.save_player(session, player)
        response["found_location"] = True
        response["message"] = "你发现了新的去处。"
        response["exp_gain"] = 20
    elif result == "partial":
        response["message"] = "你察觉到一点踪迹，但没能深入。"
        response["exp_gain"] = 8
    else:
        response["message"] = "你一无所获，还浪费了半天。"
        response["exp_gain"] = 2

    if response["exp_gain"] > 0:
        player_sys.add_exp(session, response["exp_gain"])

    return response


def _generate_find_item(loc_id: str, rng: random.Random) -> dict:
    templates = {
        "deep_forest": [("草编药囊", "草药"), ("鹿角", "杂物"), ("松果油", "药材")],
        "old_mine": [("铁矿石", "矿石"), ("矿灯", "工具"), ("生锈的镐头", "工具")],
        "river_bend": [("光滑的卵石", "饰物"), ("河蚌", "食材"), ("浮木", "杂物")],
        "old_shrine": [("断香", "信物"), ("青铜符", "信物"), ("古钱币", "古物")],
        "abandoned_farm": [("陈年酒坛", "酒"), ("破陶碗", "杂物"), ("锈镰刀", "工具")],
        "mountain_pass": [("山参", "药材"), ("旧罗盘", "工具"), ("风化石", "矿石")],
    }
    pool = templates.get(loc_id, [("无名石", "杂物")])
    name, kind = rng.choice(pool)
    affixes = rng.sample(["古老的", "磨损的", "半掩于土中的", "有点古怪的"], 1)
    return {
        "id": "itm_%s" % uuid.uuid4().hex[:8],
        "name": name,
        "kind": kind,
        "affixes": affixes,
        "story": "从%s带回。" % location_label(loc_id),
        "value": round(rng.uniform(0.1, 0.4), 2),
    }
