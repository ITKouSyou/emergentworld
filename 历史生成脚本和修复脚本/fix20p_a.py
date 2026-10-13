# Part 20P-A：打猎提示 + /travel 端点 + /player 返回已知地点
from pathlib import Path

# ---------- 1. actions.py：打猎无猎物时给提示 ----------
p = Path("server/systems/actions.py")
t = p.read_text(encoding="utf-8")

old = '''def _do_hunt(session, world, player, origin, rng, result):
    pool = HUNT_POOL.get(origin)
    if not pool:
        result["message"] = "%s没有可猎的动物。" % location_label(origin)
        result["summary"] = "你在%s想打猎，但这里没有猎物" % location_label(origin)
        player_sys.add_exp(session, 2)
        result["exp_gain"] = 2
        return result'''

new = '''def _do_hunt(session, world, player, origin, rng, result):
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
        return result'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] actions.py 打猎提示更明确")
else:
    print("[skip] actions.py 已改过或未匹配")

# ---------- 2. main.py：加 /travel 端点 ----------
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

if "/travel" not in t:
    anchor = '''@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''

    addition = '''class TravelRequest(BaseModel):
    location_id: str


@app.post("/travel")
async def travel_endpoint(req: TravelRequest) -> dict:
    """玩家移动到已发现的地点，消耗 1 tick。"""
    from server.map_layout import LOCATION_LAYOUT

    with get_session() as s:
        world = load_world(s)
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")

        if req.location_id not in LOCATION_LAYOUT:
            raise HTTPException(400, "unknown location: %s" % req.location_id)

        layout = LOCATION_LAYOUT[req.location_id]
        is_visible = not layout.get("hidden", False)
        discovered = list(world.location_ids or [])
        if not is_visible and req.location_id not in discovered:
            raise HTTPException(400, "location not discovered: %s" % req.location_id)

        old_loc = player.location_id
        if old_loc == req.location_id:
            raise HTTPException(400, "already at that location")

        player.location_id = req.location_id
        player_sys.save_player(s, player)

        tick(s, world)
        await check_timeouts(s, world)

        # 记录到 event
        try:
            from server.models.schemas import Event as EventModel
            evt_id = "evt_go_%s" % _uuid.uuid4().hex[:8]
            evt = EventModel(
                id=evt_id,
                template_id="travel",
                participants=["player"],
                location_id=req.location_id,
                state="resolved",
                payload={
                    "summary": "你从%s前往%s" % (
                        i18n.location_label(old_loc),
                        i18n.location_label(req.location_id),
                    ),
                    "narrative": "",
                    "outcome": "",
                    "interactive": False,
                    "as_message": True,
                    "is_player_action": True,
                },
                created_at=world.tick,
                resolved_at=world.tick,
            )
            save_event(s, evt)
        except Exception as e:
            import traceback
            print("[travel] 事件记录失败：%s" % e)
            traceback.print_exc()

        save_world(s, world)
        p2 = player_sys.load_player(s)

        return {
            "ok": True,
            "from_id": old_loc,
            "from_label": i18n.location_label(old_loc),
            "to_id": req.location_id,
            "to_label": i18n.location_label(req.location_id),
            "player": p2.model_dump() if p2 else {},
            "tick": world.tick,
            "day": world.day,
            "hour": world.hour,
        }


@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''

    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] main.py 加 /travel")
    else:
        print("[fail] main.py 锚点未找到")
else:
    print("[skip] main.py 已有 /travel")

# ---------- 3. main.py：/player 返回 known_locations ----------
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

old_player = '''@app.get("/player")
def get_player() -> dict:
    with get_session() as s:
        p = player_sys.load_player(s)
        if p is None:
            return {"created": False}
        return p.model_dump()'''

new_player = '''@app.get("/player")
def get_player() -> dict:
    from server.map_layout import LOCATION_LAYOUT
    with get_session() as s:
        p = player_sys.load_player(s)
        if p is None:
            return {"created": False}
        data = p.model_dump()

        # 已发现地点列表
        world = load_world(s)
        discovered = list(world.location_ids or [])
        if "village_square" not in discovered:
            discovered.append("village_square")
        known = []
        for loc_id, layout in LOCATION_LAYOUT.items():
            is_hidden = bool(layout.get("hidden", False))
            if (not is_hidden) or loc_id in discovered:
                known.append({
                    "id": loc_id,
                    "label": i18n.location_label(loc_id),
                    "current": loc_id == p.location_id,
                })
        data["known_locations"] = known
        return data'''

if old_player in t:
    t = t.replace(old_player, new_player, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] main.py /player 返回 known_locations")
else:
    print("[skip] /player 已改过或未匹配")

# ---------- 4. i18n 加 travel ----------
p = Path("server/i18n.py")
t = p.read_text(encoding="utf-8")
if '"travel"' not in t:
    anchor = '    "gather": "采集",\n'
    if anchor in t:
        t = t.replace(anchor, anchor + '    "travel": "前往",\n', 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] i18n 加 travel")
    else:
        print("[skip] i18n travel 锚点未找到")

print()
print("A 部分完成")