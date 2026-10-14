# Part 80：地点扩到 30 个
from pathlib import Path

# ============================================================
# 1. 重写 map_layout.py
# ============================================================
Path("server/map_layout.py").write_text('''# 村庄地图的固定布局（30 个地点）
from __future__ import annotations

# 初始可见地点（村内 + 村外近处）
# 每项：x, y, radius, color, hidden, kind
#   kind: village / field / wild / ruin
LOCATION_LAYOUT = {
    # ---------- 村内（9）----------
    "village_square": {"x": 0.50, "y": 0.55, "radius": 0.055, "color": "#c9a86a", "hidden": False, "kind": "village"},
    "market":         {"x": 0.28, "y": 0.32, "radius": 0.048, "color": "#d8b46a", "hidden": False, "kind": "village"},
    "tavern":         {"x": 0.72, "y": 0.64, "radius": 0.048, "color": "#b07a4a", "hidden": False, "kind": "village"},
    "home":           {"x": 0.20, "y": 0.76, "radius": 0.048, "color": "#8a9bb5", "hidden": False, "kind": "village"},
    "village_hall":   {"x": 0.55, "y": 0.26, "radius": 0.048, "color": "#a86a8a", "hidden": False, "kind": "village"},
    "well":           {"x": 0.42, "y": 0.62, "radius": 0.035, "color": "#88b8d8", "hidden": False, "kind": "village"},
    "mill":           {"x": 0.65, "y": 0.44, "radius": 0.040, "color": "#c0a080", "hidden": False, "kind": "village"},
    "smithy":         {"x": 0.33, "y": 0.48, "radius": 0.038, "color": "#a06050", "hidden": False, "kind": "village"},
    "dye_works":      {"x": 0.60, "y": 0.74, "radius": 0.038, "color": "#8a70a0", "hidden": False, "kind": "village"},

    # ---------- 村外近处（6）----------
    "forest":         {"x": 0.82, "y": 0.22, "radius": 0.065, "color": "#4f7f4f", "hidden": False, "kind": "wild"},
    "village_edge":   {"x": 0.10, "y": 0.42, "radius": 0.048, "color": "#7a7a7a", "hidden": False, "kind": "wild"},
    "farm_field":     {"x": 0.15, "y": 0.28, "radius": 0.055, "color": "#c8b060", "hidden": False, "kind": "field"},
    "orchard":        {"x": 0.30, "y": 0.62, "radius": 0.045, "color": "#8aa860", "hidden": False, "kind": "field"},
    "pasture":        {"x": 0.18, "y": 0.55, "radius": 0.050, "color": "#9ec47e", "hidden": False, "kind": "field"},
    "brook":          {"x": 0.45, "y": 0.78, "radius": 0.038, "color": "#6aa8d0", "hidden": False, "kind": "wild"},

    # ---------- 隐藏（15）----------
    "deep_forest":    {"x": 0.90, "y": 0.10, "radius": 0.060, "color": "#3a6a3a", "hidden": True, "kind": "wild"},
    "old_mine":       {"x": 0.08, "y": 0.18, "radius": 0.050, "color": "#6a6a6a", "hidden": True, "kind": "ruin"},
    "river_bend":     {"x": 0.62, "y": 0.88, "radius": 0.055, "color": "#5a7aa8", "hidden": True, "kind": "wild"},
    "old_shrine":     {"x": 0.35, "y": 0.05, "radius": 0.050, "color": "#a88a5a", "hidden": True, "kind": "ruin"},
    "abandoned_farm": {"x": 0.05, "y": 0.90, "radius": 0.050, "color": "#8a7a5a", "hidden": True, "kind": "ruin"},
    "mountain_pass":  {"x": 0.95, "y": 0.50, "radius": 0.055, "color": "#7a6a8a", "hidden": True, "kind": "wild"},
    "waterfall":      {"x": 0.88, "y": 0.40, "radius": 0.048, "color": "#68b0e0", "hidden": True, "kind": "wild"},
    "cliff":          {"x": 0.08, "y": 0.06, "radius": 0.050, "color": "#5a5a6a", "hidden": True, "kind": "wild"},
    "stone_forest":   {"x": 0.75, "y": 0.06, "radius": 0.055, "color": "#8a8a9a", "hidden": True, "kind": "wild"},
    "old_road":       {"x": 0.88, "y": 0.78, "radius": 0.048, "color": "#a09070", "hidden": True, "kind": "ruin"},
    "ancient_grave":  {"x": 0.48, "y": 0.05, "radius": 0.050, "color": "#6a5a6a", "hidden": True, "kind": "ruin"},
    "quarry":         {"x": 0.20, "y": 0.06, "radius": 0.052, "color": "#a0a0a0", "hidden": True, "kind": "ruin"},
    "salt_flat":      {"x": 0.02, "y": 0.62, "radius": 0.052, "color": "#d0d0c0", "hidden": True, "kind": "wild"},
    "ferry":          {"x": 0.75, "y": 0.92, "radius": 0.048, "color": "#5070a0", "hidden": True, "kind": "wild"},
    "bamboo_grove":   {"x": 0.96, "y": 0.22, "radius": 0.048, "color": "#a0c080", "hidden": True, "kind": "wild"},
    "hot_spring":     {"x": 0.65, "y": 0.08, "radius": 0.048, "color": "#d0a0b0", "hidden": True, "kind": "wild"},
}

# 道路
PATHS = [
    # 村内
    ("village_square", "market"),
    ("village_square", "tavern"),
    ("village_square", "village_hall"),
    ("village_square", "home"),
    ("village_square", "well"),
    ("village_square", "mill"),
    ("village_square", "smithy"),
    ("village_square", "dye_works"),
    ("market", "village_hall"),
    ("market", "smithy"),
    ("well", "orchard"),
    ("well", "pasture"),
    ("mill", "dye_works"),
    ("tavern", "dye_works"),
    # 村外
    ("village_square", "forest"),
    ("village_square", "village_edge"),
    ("village_edge", "farm_field"),
    ("village_edge", "pasture"),
    ("farm_field", "orchard"),
    ("pasture", "brook"),
    ("home", "brook"),
    ("market", "forest"),
    ("village_edge", "forest"),
    # 隐藏地点
    ("forest", "deep_forest"),
    ("village_edge", "old_mine"),
    ("brook", "river_bend"),
    ("village_hall", "old_shrine"),
    ("home", "abandoned_farm"),
    ("forest", "mountain_pass"),
    ("forest", "waterfall"),
    ("cliff", "stone_forest"),
    ("farm_field", "cliff"),
    ("pasture", "quarry"),
    ("old_mine", "quarry"),
    ("old_shrine", "ancient_grave"),
    ("deep_forest", "stone_forest"),
    ("tavern", "old_road"),
    ("river_bend", "ferry"),
    ("forest", "bamboo_grove"),
    ("waterfall", "hot_spring"),
    ("old_shrine", "hot_spring"),
    ("village_edge", "salt_flat"),
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


def location_kind(location_id: str) -> str:
    return LOCATION_LAYOUT.get(location_id, {}).get("kind", "village")
''', encoding="utf-8")
print("[write] server/map_layout.py（30 个地点）")

# ============================================================
# 2. i18n 加中文标签
# ============================================================
NEW_LOC_LABELS = {
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
}

p = Path("server/i18n.py")
t = p.read_text(encoding="utf-8")
anchor = '    "village_hall": "村公所",\n'
if anchor in t and '"well"' not in t:
    addition = ''.join('    "%s": "%s",\n' % (k, v) for k, v in NEW_LOC_LABELS.items())
    t = t.replace(anchor, anchor + addition, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] i18n 加 18 个地点标签")
else:
    print("[skip] i18n 已改过")

# ============================================================
# 3. explore.py 更新难度 + flavor
# ============================================================
p = Path("server/systems/explore.py")
t = p.read_text(encoding="utf-8")

old_diff = '''LOCATION_DIFFICULTY = {
    "deep_forest": "normal",
    "old_mine": "normal",
    "river_bend": "easy",
    "old_shrine": "hard",
    "abandoned_farm": "easy",
    "mountain_pass": "hard",
}'''

new_diff = '''LOCATION_DIFFICULTY = {
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
}'''
if old_diff in t:
    t = t.replace(old_diff, new_diff, 1)
    print("[fix] explore.py 难度表更新")

old_flavor = '''LOCATION_FLAVORS = {
    "deep_forest": "幽深的林间，你拨开纠缠的藤蔓。",
    "old_mine": "废矿的入口塌了一半，空气里满是铁锈味。",
    "river_bend": "河水在此拐弯，冲积出一片细沙滩。",
    "old_shrine": "残破的神像倒在草丛里，香炉早已冰冷。",
    "abandoned_farm": "农舍的屋顶已经塌了，院里的井还盖着。",
    "mountain_pass": "山风呼啸，一条小径隐没在云雾里。",
}'''

new_flavor = '''LOCATION_FLAVORS = {
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
}'''
if old_flavor in t:
    t = t.replace(old_flavor, new_flavor, 1)
    print("[fix] explore.py flavor 更新")

p.write_text(t, encoding="utf-8")

# ============================================================
# 4. actions.py 扩充 gather/hunt pool
# ============================================================
p = Path("server/systems/actions.py")
t = p.read_text(encoding="utf-8")

old_gather = '''GATHER_POOL = {
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
}'''

new_gather = '''GATHER_POOL = {
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
}'''
if old_gather in t:
    t = t.replace(old_gather, new_gather, 1)
    print("[fix] actions.py GATHER_POOL 扩充")

old_hunt = '''HUNT_POOL = {
    "forest": [("野兔", "猎物"), ("山鸡", "猎物")],
    "village_edge": [("野兔", "猎物")],
    "deep_forest": [("野鹿", "猎物"), ("野猪", "猎物")],
    "mountain_pass": [("岩羊", "猎物")],
}'''

new_hunt = '''HUNT_POOL = {
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
}'''
if old_hunt in t:
    t = t.replace(old_hunt, new_hunt, 1)
    print("[fix] actions.py HUNT_POOL 扩充")

p.write_text(t, encoding="utf-8")

# ============================================================
# 5. schedule.py 加新地点作为可能目标
# ============================================================
p = Path("server/systems/schedule.py")
t = p.read_text(encoding="utf-8")

# 让儿童能去新地点，成人也能去
old = '''    if is_child:
        day_loc = "village_square"'''
new = '''    if is_child:
        day_loc = rng.choice(["village_square", "orchard", "brook", "mill", "well"])'''
if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] schedule.py 儿童日程加新地点")

# 成人工作日加 farm_field/pasture
t = p.read_text(encoding="utf-8")
old2 = '''    else:
        if openness > 0.6:
            day_loc = rng.choice(["forest", "village_square", "market"])
        else:
            day_loc = rng.choice(["market", "home", "village_hall"])'''
new2 = '''    else:
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
            ])'''
if old2 in t:
    t = t.replace(old2, new2, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] schedule.py 成人日程加新地点")

# location_labels 也补
t = p.read_text(encoding="utf-8")
if '"well": "井边"' not in t:
    old3 = '''    loc_labels = {
        "village_square": "村庄广场",
        "market": "市场",
        "tavern": "酒馆",
        "home": "住处",
        "forest": "森林",
        "village_edge": "村庄边缘",
        "village_hall": "村公所",
    }'''
    new3 = '''    loc_labels = {
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
    }'''
    if old3 in t:
        t = t.replace(old3, new3, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] schedule.py loc_labels 补全")

print()
print("===== 完成 =====")
print("测试：pytest -v")
print("重启：uvicorn server.main:app")