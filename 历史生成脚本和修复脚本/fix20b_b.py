# Part 20B - B：给 main.py 加 /explore 端点，更新 map_view
from pathlib import Path

# 1. map_view：返回未发现地点的轮廓
p = Path("server/core/map_view.py")
t = p.read_text(encoding="utf-8")

# 用 discovered 过滤地点
old_locs = '''    locations: list[dict] = []
    for loc_id, layout in all_locations().items():
        locations.append({
            "id": loc_id,
            "label": i18n.location_label(loc_id),
            "x": layout["x"], "y": layout["y"],
            "radius": layout["radius"],
            "color": layout["color"],
        })'''

new_locs = '''    # 已发现的地点（world.location_ids）
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
            })'''

if old_locs in t:
    t = t.replace(old_locs, new_locs, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] map_view 加未知地点显示")
else:
    print("[skip] map_view 已改过或锚点未找到")

# 2. main.py：加 explore 端点
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

if "/explore" not in t:
    # 找事件段之前插入
    anchor = '''@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''
    addition = '''@app.post("/explore")
async def explore_endpoint() -> dict:
    """探索一次：尝试发现新地点。"""
    from server.systems import explore as explore_sys

    with get_session() as s:
        world = load_world(s)
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")

        # 推进 1 tick（探索消耗时间）
        tick(s, world)
        await check_timeouts(s, world)

        result = await explore_sys.explore_once(s, world, player)

        # 处理物品入库
        item_data = result.get("found_item")
        if item_data is not None:
            from server.models.db import ItemRow
            row = ItemRow(
                id=item_data["id"],
                reward_id="",
                event_id="",
                name=item_data.get("name", ""),
                kind=item_data.get("kind", ""),
                affixes_json=dumps(item_data.get("affixes", [])),
                story=item_data.get("story", ""),
                value=float(item_data.get("value", 0.0)),
                owner_id="player",
                consumed=False,
            )
            s.add(row)
            s.commit()

        save_world(s, world)
        result["tick"] = world.tick
        result["day"] = world.day
        result["hour"] = world.hour

        # 刷新的 player
        p2 = player_sys.load_player(s)
        if p2 is not None:
            result["player"] = p2.model_dump()

        return result


@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''

    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] main.py 加 /explore 端点")
    else:
        print("[fail] main.py 锚点未找到")
else:
    print("[skip] main.py 已有 /explore")

print()
print("B 部分完成。接下来运行 fix20b_c.py")