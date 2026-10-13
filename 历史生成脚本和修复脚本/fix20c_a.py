# 给 map_view 加 player 位置信息
from pathlib import Path

p = Path("server/core/map_view.py")
t = p.read_text(encoding="utf-8")

if '"player"' in t and 'player_pos' in t:
    print("[skip] 已改过")
else:
    # 在 return 前加 player 字段
    old = '''    return {
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
    }'''

    new = '''    # 玩家位置
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
    }'''

    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] map_view 加 player 位置")
    else:
        print("[fail] 锚点未找到")