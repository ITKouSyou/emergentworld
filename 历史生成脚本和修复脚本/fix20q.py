# 统一 /player、/action、/travel 的 player 返回格式（都带 known_locations）
from pathlib import Path

p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

# 1. 抽出 _player_to_response
if "_player_to_response" not in t:
    anchor = '''@app.get("/player")
def get_player() -> dict:'''

    helper = '''def _player_to_response(session, p) -> dict:
    """把 Player 转成带 known_locations 的响应 dict。"""
    from server.map_layout import LOCATION_LAYOUT
    data = p.model_dump()

    world = load_world(session)
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
    return data


@app.get("/player")
def get_player() -> dict:'''

    if anchor in t:
        t = t.replace(anchor, helper, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] 抽出 _player_to_response")
    else:
        print("[fail] _player_to_response 锚点未找到")

# 2. 把 get_player 里的实现改成调用 helper
t = p.read_text(encoding="utf-8")
old_body = '''@app.get("/player")
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

new_body = '''@app.get("/player")
def get_player() -> dict:
    with get_session() as s:
        p = player_sys.load_player(s)
        if p is None:
            return {"created": False}
        return _player_to_response(s, p)'''

if old_body in t:
    t = t.replace(old_body, new_body, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] get_player 用 helper")
else:
    # 可能已经被替换过，无所谓
    print("[skip] get_player 已改过")

# 3. /action 里的 p2 → 用 helper
t = p.read_text(encoding="utf-8")
old_a = '''        p2 = player_sys.load_player(s)
        action_result["player"] = p2.model_dump() if p2 else {}'''
new_a = '''        p2 = player_sys.load_player(s)
        action_result["player"] = _player_to_response(s, p2) if p2 else {}'''
if old_a in t:
    t = t.replace(old_a, new_a, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] /action 用 helper")
else:
    print("[skip] /action 已改过")

# 4. /travel 里的 p2 → 用 helper
t = p.read_text(encoding="utf-8")
old_t = '''        p2 = player_sys.load_player(s)

        return {
            "ok": True,
            "from_id": old_loc,
            "from_label": i18n.location_label(old_loc),
            "to_id": req.location_id,
            "to_label": i18n.location_label(req.location_id),
            "player": p2.model_dump() if p2 else {},'''
new_t = '''        p2 = player_sys.load_player(s)

        return {
            "ok": True,
            "from_id": old_loc,
            "from_label": i18n.location_label(old_loc),
            "to_id": req.location_id,
            "to_label": i18n.location_label(req.location_id),
            "player": _player_to_response(s, p2) if p2 else {},'''
if old_t in t:
    t = t.replace(old_t, new_t, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] /travel 用 helper")
else:
    print("[skip] /travel 已改过")

# 5. /player/allocate 也统一
t = p.read_text(encoding="utf-8")
old_al = '''@app.post("/player/allocate")
def allocate(req: AllocateRequest) -> dict:
    with get_session() as s:
        ok, err, p = player_sys.allocate_point(s, req.attribute, req.count)
        if not ok or p is None:
            raise HTTPException(400, err or "allocate failed")
        return p.model_dump()'''
new_al = '''@app.post("/player/allocate")
def allocate(req: AllocateRequest) -> dict:
    with get_session() as s:
        ok, err, p = player_sys.allocate_point(s, req.attribute, req.count)
        if not ok or p is None:
            raise HTTPException(400, err or "allocate failed")
        return _player_to_response(s, p)'''
if old_al in t:
    t = t.replace(old_al, new_al, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] /player/allocate 用 helper")
else:
    print("[skip] /player/allocate 已改过")

print()
print("重启 uvicorn，Godot 完全关闭重开")