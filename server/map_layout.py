# 村庄地图的固定布局

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
