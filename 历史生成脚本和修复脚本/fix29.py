# 让 /event/{id}/resolve 也记录目标进度
from pathlib import Path

p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

old = '''@app.post("/event/{event_id}/resolve")
async def resolve_event_endpoint(event_id: str, req: ResolveRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        result = await resolve_event(s, world, event_id, req.choice_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "resolve failed"))
        return result'''

new = '''@app.post("/event/{event_id}/resolve")
async def resolve_event_endpoint(event_id: str, req: ResolveRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        result = await resolve_event(s, world, event_id, req.choice_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "resolve failed"))

        # 记录"参与事件"目标
        try:
            from server.systems import goal as goal_sys
            import random as _r
            goal_sys.ensure_daily_goals(s, world, _r.Random(world.seed + world.day))
            goal_sys.ensure_milestones(s, world)
            player = player_sys.load_player(s)
            if player is not None:
                goal_sys.record_action(s, world, player, "event_resolved", 1)
        except Exception as e:
            import traceback
            print("[resolve] 目标记录失败：%s" % e)
            traceback.print_exc()

        return result'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] /event/{id}/resolve 记录目标")
else:
    print("[skip] 已改过或锚点未匹配")

# 顺带：超时/自动结算的事件也算参与（可选）
# 这里跳过，先让手动抉择能算

print()
print("重启后端：Ctrl+C 后 uvicorn server.main:app --reload")