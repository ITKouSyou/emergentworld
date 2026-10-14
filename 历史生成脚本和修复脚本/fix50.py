# 重写 resolve 端点，用 Body(embed=True)
from pathlib import Path

p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

# 0. 先诊断
print("=== ResolveRequest 出现位置 ===")
for i, line in enumerate(t.split("\n")):
    if "ResolveRequest" in line:
        print("%4d | %s" % (i+1, line.strip()))
print()

# 1. 找 Body 是否在 fastapi 导入
if "from fastapi import" in t:
    for line in t.split("\n")[:30]:
        if line.strip().startswith("from fastapi import"):
            if "Body" not in line:
                # 把 Body 加进去
                if "(" in line and line.rstrip().endswith(")"):
                    new_line = line.rstrip()[:-1] + ", Body)"
                    t = t.replace(line, new_line, 1)
                else:
                    new_line = line.rstrip() + ", Body"
                    t = t.replace(line, new_line, 1)
                print("[fix] Body 加入 fastapi 导入")
            else:
                print("[ok] Body 已在导入")
            break
else:
    # 加一行
    t = t.replace("from fastapi import FastAPI, HTTPException",
                  "from fastapi import Body, FastAPI, HTTPException", 1)
    print("[fix] 加 Body 到 fastapi 导入")

# 2. 找 resolve 端点
start = t.find('@app.post("/event/{event_id}/resolve")')
if start < 0:
    print("[fail] 找不到 resolve 端点")
    raise SystemExit(1)

end = t.find('\n@app.', start + 10)
if end < 0:
    end = len(t)

new_endpoint = '''@app.post("/event/{event_id}/resolve")
async def resolve_event_endpoint(
    event_id: str,
    choice_id: str = Body(..., embed=True),
) -> dict:
    print("[resolve] event_id=[%s] choice_id=[%s]" % (event_id, choice_id))

    with get_session() as s:
        world = load_world(s)
        result = await resolve_event(s, world, event_id, choice_id)
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

t = t[:start] + new_endpoint + t[end:]
p.write_text(t, encoding="utf-8")
print("[fix] resolve 端点重写")

# 3. 打印新端点
t2 = p.read_text(encoding="utf-8")
start2 = t2.find('@app.post("/event/{event_id}/resolve")')
end2 = t2.find('\n@app.', start2 + 10)
print()
print("--- 新 resolve 端点 ---")
print(t2[start2:end2])

print()
print("重启后端：Ctrl+C → uvicorn server.main:app")