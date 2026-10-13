"""构造地图视图数据。"""

from __future__ import annotations

import math

from sqlmodel import Session, select

from server import i18n
from server.core.world import load_npcs
from server.map_layout import all_locations, all_paths, get_location
from server.models.db import EventRow, loads
from server.models.schemas import World


def _distribute_in_circle(base_x: float, base_y: float, count: int,
                          ring_radius: float = 0.035) -> list[tuple[float, float]]:
    if count <= 1:
        return [(base_x, base_y)]
    points: list[tuple[float, float]] = []
    for i in range(count):
        angle = -math.pi / 2 + (2 * math.pi * i / count)
        px = base_x + math.cos(angle) * ring_radius
        py = base_y + math.sin(angle) * ring_radius
        points.append((px, py))
    return points


def build_map_data(session: Session, world: World) -> dict:
    # 已发现的地点（world.location_ids）
    discovered = list(world.location_ids or [])
    if "village_square" not in discovered:
        discovered.append("village_square")
    # 初始可见的（hidden=False）
    all_locs = all_locations()

    locations: list[dict] = []
    for loc_id, layout in all_locs.items():
        is_hidden = bool(layout.get("hidden", False))
        is_discovered = loc_id in discovered
        if is_hidden and not is_discovered:
            # 显示为问号点
            locations.append({
                "id": loc_id,
                "label": "？",
                "x": layout["x"], "y": layout["y"],
                "radius": layout["radius"],
                "color": "#555555",
                "unknown": True,
            })
        else:
            locations.append({
                "id": loc_id,
                "label": i18n.location_label(loc_id),
                "x": layout["x"], "y": layout["y"],
                "radius": layout["radius"],
                "color": layout["color"],
                "unknown": False,
            })

    paths: list[dict] = []
    for a, b in all_paths():
        la = get_location(a)
        lb = get_location(b)
        paths.append({
            "from": a, "to": b,
            "from_x": la["x"], "from_y": la["y"],
            "to_x": lb["x"], "to_y": lb["y"],
        })

    npcs = load_npcs(session)
    by_loc: dict[str, list] = {}
    for npc in npcs:
        by_loc.setdefault(npc.location_id, []).append(npc)

    npc_positions: list[dict] = []
    for loc_id, group in by_loc.items():
        layout = get_location(loc_id)
        pts = _distribute_in_circle(layout["x"], layout["y"], len(group))
        for npc, (px, py) in zip(group, pts):
            npc_positions.append({
                "id": npc.id, "name": npc.name,
                "location_id": loc_id,
                "x": round(px, 4), "y": round(py, 4),
            })

    rows = session.exec(
        select(EventRow).where(EventRow.state == "active")
        .order_by(EventRow.created_at.desc()).limit(10)
    ).all()
    active_events = [
        {
            "id": r.id,
            "template_id": r.template_id,
            "template_label": i18n.template_label(r.template_id),
            "location_id": r.location_id,
            "location_label": i18n.location_label(r.location_id),
            "summary": (loads(r.payload_json) or {}).get("summary", ""),
        }
        for r in rows
    ]

    # 玩家位置
    player_pos = None
    try:
        from server.systems import player as player_sys
        player = player_sys.load_player(session)
        if player is not None and player.created:
            play_layout = get_location(player.location_id)
            player_pos = {
                "id": "player",
                "name": player.name,
                "location_id": player.location_id,
                "location_label": i18n.location_label(player.location_id),
                "x": play_layout["x"],
                "y": play_layout["y"],
            }
    except Exception:
        player_pos = None

    return {
        "tick": world.tick,
        "day": world.day,
        "hour": world.hour,
        "tension": world.director.tension,
        "season": world.season,
        "season_label": i18n.season_label(world.season),
        "weather": world.weather,
        "weather_label": i18n.weather_label(world.weather),
        "locations": locations,
        "paths": paths,
        "npcs": npc_positions,
        "active_events": active_events,
        "player": player_pos,
    }
