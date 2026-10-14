# 修：探索目标 + 里程碑计算 + goal 表重建
from pathlib import Path

# ============================================================
# 1. main.py：探索无论有无发现都记录
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

old = '''            if action_name == "hunt" and found_item:
                record_action = "hunt_success"
            elif action_name == "gather":
                record_action = "gather"
            elif action_name == "train":
                record_action = "train"
            elif action_name == "socialize":
                record_action = "socialize"
            elif action_name == "explore" and action_result.get("found_location"):
                record_action = "explore"'''

new = '''            if action_name == "hunt" and found_item:
                record_action = "hunt_success"
            elif action_name == "gather":
                record_action = "gather"
            elif action_name == "train":
                record_action = "train"
            elif action_name == "socialize":
                record_action = "socialize"
            elif action_name == "explore":
                record_action = "explore"'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] main.py 探索无论如何都记录")
else:
    print("[skip] main.py 已改过或锚点未匹配")

# ============================================================
# 2. goal.py：里程碑 total_locations 用真实数据
# ============================================================
p = Path("server/systems/goal.py")
t = p.read_text(encoding="utf-8")

old_ml = '''def _milestone_matches(session: Session, key: str, player: Player) -> int:
    """长期里程碑的进度直接从玩家状态算。"""
    if key == "total_money":
        return player.money
    if key == "total_level":
        return player.level
    if key == "total_locations":
        # 从 world.location_ids 算
        from server.models.db import WorldRow
        import json
        # 暂用当前已知地点数
        return len(player.known_npcs)  # 简化：用 known_npcs 代替
    if key == "total_items":
        from server.systems import inventory
        return len(inventory.list_items_by_owner(session, "player"))
    return 0'''

new_ml = '''def _milestone_matches(session: Session, key: str, player: Player) -> int:
    """长期里程碑的进度直接从玩家状态算。"""
    if key == "total_money":
        return player.money
    if key == "total_level":
        return player.level
    if key == "total_locations":
        from server.models.db import WorldRow
        from server.map_layout import LOCATION_LAYOUT
        import json
        row = session.get(WorldRow, "default")
        if row is None:
            return 0
        discovered = json.loads(row.location_ids_json or "[]")
        count = 0
        for loc in discovered:
            if loc in LOCATION_LAYOUT and LOCATION_LAYOUT[loc].get("hidden", False):
                count += 1
        return count
    if key == "total_items":
        from server.systems import inventory
        return len(inventory.list_items_by_owner(session, "player"))
    return 0'''

if old_ml in t:
    t = t.replace(old_ml, new_ml, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] goal.py 里程碑 total_locations 用真实数据")
else:
    print("[skip] goal.py 已改过或锚点未匹配")

# ============================================================
# 3. main.py：加 /goal/reset 端点
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

if "/goal/reset" not in t:
    anchor = '''@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''
    addition = '''@app.post("/goal/reset")
def goal_reset() -> dict:
    """清空所有目标并重建（用于调试或老数据修复）。"""
    from sqlmodel import delete
    from server.models.db import GoalRow
    with get_session() as s:
        s.exec(delete(GoalRow))
        s.commit()
        world = load_world(s)
        from server.systems import goal as goal_sys
        import random as _r
        rng = _r.Random(world.seed + world.day)
        goal_sys.ensure_daily_goals(s, world, rng)
        goal_sys.ensure_milestones(s, world)
        return {"ok": True, "reset": True}


@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] main.py 加 /goal/reset")
    else:
        print("[fail] main.py 锚点未找到")
else:
    print("[skip] main.py 已有 /goal/reset")

print()
print("重启后端 → 调 /goal/reset → 刷新 Godot")