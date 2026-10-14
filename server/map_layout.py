# 村庄地图的固定布局（30 个地点）
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
