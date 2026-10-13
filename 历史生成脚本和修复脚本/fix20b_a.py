# Part 20B - A：探索系统后端
from pathlib import Path

FILES = {}

# 1. map_layout.py：加隐藏地点 + 区分初始可见
FILES["server/map_layout.py"] = '''# 村庄地图的固定布局

from __future__ import annotations

# 初始可见地点
LOCATION_LAYOUT = {
    "village_square": {"x": 0.50, "y": 0.55, "radius": 0.055, "color": "#c9a86a", "hidden": False},
    "market":         {"x": 0.28, "y": 0.32, "radius": 0.048, "color": "#d8b46a", "hidden": False},
    "tavern":         {"x": 0.72, "y": 0.64, "radius": 0.048, "color": "#b07a4a", "hidden": False},
    "home":           {"x": 0.20, "y": 0.76, "radius": 0.048, "color": "#8a9bb5", "hidden": False},
    "forest":         {"x": 0.82, "y": 0.22, "radius": 0.065, "color": "#4f7f4f", "hidden": False},
    "village_edge":   {"x": 0.10, "y": 0.42, "radius": 0.048, "color": "#7a7a7a", "hidden": False},
    "village_hall":   {"x": 0.55, "y": 0.26, "radius": 0.048, "color": "#a86a8a", "hidden": False},

    # 隐藏地点（初始未发现）
    "deep_forest":    {"x": 0.90, "y": 0.10, "radius": 0.060, "color": "#3a6a3a", "hidden": True},
    "old_mine":       {"x": 0.08, "y": 0.18, "radius": 0.050, "color": "#6a6a6a", "hidden": True},
    "river_bend":     {"x": 0.62, "y": 0.85, "radius": 0.055, "color": "#5a7aa8", "hidden": True},
    "old_shrine":     {"x": 0.35, "y": 0.05, "radius": 0.050, "color": "#a88a5a", "hidden": True},
    "abandoned_farm": {"x": 0.05, "y": 0.90, "radius": 0.050, "color": "#8a7a5a", "hidden": True},
    "mountain_pass":  {"x": 0.95, "y": 0.50, "radius": 0.055, "color": "#7a6a8a", "hidden": True},
}

PATHS = [
    ("village_square", "market"),
    ("village_square", "tavern"),
    ("village_square", "village_hall"),
    ("village_square", "home"),
    ("village_square", "forest"),
    ("village_square", "village_edge"),
    ("market", "village_hall"),
    ("village_edge", "forest"),
    ("market", "forest"),
    # 通往隐藏地点的路（发现后可见）
    ("forest", "deep_forest"),
    ("village_edge", "old_mine"),
    ("home", "river_bend"),
    ("village_hall", "old_shrine"),
    ("home", "abandoned_farm"),
    ("forest", "mountain_pass"),
]

DEFAULT_LOCATION = "village_square"


def get_location(location_id: str):
    return LOCATION_LAYOUT.get(location_id, LOCATION_LAYOUT[DEFAULT_LOCATION])


def all_locations():
    return LOCATION_LAYOUT


def all_paths():
    return PATHS


def hidden_location_ids():
    return [k for k, v in LOCATION_LAYOUT.items() if v.get("hidden")]


def visible_location_ids(discovered):
    return [k for k in LOCATION_LAYOUT.keys()
            if not LOCATION_LAYOUT[k].get("hidden") or k in discovered]
'''

# 2. i18n 补隐藏地点中文名
p = Path("server/i18n.py")
t = p.read_text(encoding="utf-8")
new_entries = '''    "deep_forest": "深山老林",
    "old_mine": "废弃矿洞",
    "river_bend": "河湾",
    "old_shrine": "古庙遗址",
    "abandoned_farm": "荒废农舍",
    "mountain_pass": "山道",
'''
anchor = '    "village_hall": "村公所",\n'
if '"deep_forest"' not in t and anchor in t:
    t = t.replace(anchor, anchor + new_entries, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] i18n 加隐藏地点中文名")
else:
    print("[skip] i18n 已改过")

# 3. explore 系统
FILES["server/systems/explore.py"] = '''# 探索系统

from __future__ import annotations

import random

from sqlmodel import Session

from server.i18n import location_label
from server.map_layout import LOCATION_LAYOUT, hidden_location_ids
from server.models.db import WorldRow
from server.models.schemas import Player, World
from server.systems import player as player_sys

# 每个隐藏地点的发现难度
LOCATION_DIFFICULTY = {
    "deep_forest": "normal",
    "old_mine": "normal",
    "river_bend": "easy",
    "old_shrine": "hard",
    "abandoned_farm": "easy",
    "mountain_pass": "hard",
}

# 已发现地点里能找到的物品描述
LOCATION_FLAVORS = {
    "deep_forest": "幽深的林间，你拨开纠缠的藤蔓。",
    "old_mine": "废矿的入口塌了一半，空气里满是铁锈味。",
    "river_bend": "河水在此拐弯，冲积出一片细沙滩。",
    "old_shrine": "残破的神像倒在草丛里，香炉早已冰冷。",
    "abandoned_farm": "农舍的屋顶已经塌了，院里的井还盖着。",
    "mountain_pass": "山风呼啸，一条小径隐没在云雾里。",
}


def get_discovered(session: Session, world_id: str) -> list[str]:
    row = session.get(WorldRow, world_id)
    if row is None:
        return []
    import json
    return json.loads(row.location_ids_json or "[]")


def add_discovered(session: Session, world_id: str, loc_id: str) -> None:
    row = session.get(WorldRow, world_id)
    if row is None:
        return
    import json
    cur = json.loads(row.location_ids_json or "[]")
    if loc_id not in cur:
        cur.append(loc_id)
    row.location_ids_json = json.dumps(cur, ensure_ascii=False)
    session.add(row)
    session.commit()


def pick_undiscovered_location(
    session: Session,
    world: World,
    rng: random.Random,
):
    discovered = get_discovered(session, world.id)
    candidates = [loc for loc in hidden_location_ids() if loc not in discovered]
    if not candidates:
        return None
    # 优先 discover 更近的地点（简化：随机）
    return rng.choice(candidates)


async def explore_once(
    session: Session,
    world: World,
    player: Player,
) -> dict:
    """执行一次探索，返回结果 dict。"""
    rng = random.Random(world.seed * 77771 + world.tick)

    # 1. 玩家所在地点作为探索起点（默认村庄广场）
    origin = player.location_id or "village_square"

    # 2. 选一个未发现地点
    target = pick_undiscovered_location(session, world, rng)
    if target is None:
        return {
            "ok": True,
            "kind": "no_more",
            "message": "附近的地界你已经走遍了。",
            "check": None,
            "found_location": None,
            "found_item": None,
        }

    difficulty = LOCATION_DIFFICULTY.get(target, "normal")

    # 3. 属性判定：感知
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
        # 大成功：发现地点 + 物品
        add_discovered(session, world.id, target)
        response["found_location"] = True
        response["found_item"] = _generate_find_item(target, rng)
        response["message"] = "你不仅找到了入口，还捡到了一件东西。"
        response["exp_gain"] = 30
    elif result == "success":
        add_discovered(session, world.id, target)
        response["found_location"] = True
        response["message"] = "你发现了新的去处。"
        response["exp_gain"] = 20
    elif result == "partial":
        response["message"] = "你察觉到一点踪迹，但没能深入。"
        response["exp_gain"] = 8
    else:
        response["message"] = "你一无所获，还浪费了半天。"
        response["exp_gain"] = 2

    # 给经验
    if response["exp_gain"] > 0:
        player_sys.add_exp(session, response["exp_gain"])

    return response


def _generate_find_item(loc_id: str, rng: random.Random) -> dict:
    """简单物品生成。"""
    import uuid
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
'''


def main():
    root = Path.cwd()
    for rel, content in FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        print("[write] " + rel)
    print()
    print("A 部分完成。接下来运行 fix20b_b.py")


if __name__ == "__main__":
    main()