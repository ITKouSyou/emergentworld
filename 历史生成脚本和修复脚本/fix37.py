# 1. run_event_cycle 加 attempt 参数（换种子重试）
# 2. trigger_event 端点重写（重试 + 保护）
from pathlib import Path

# ============================================================
# 1. event_flow.py：加 attempt 参数
# ============================================================
p = Path("server/core/event_flow.py")
t = p.read_text(encoding="utf-8")

old_sig = '''async def run_event_cycle(
    session: Session,
    world: World,
    templates: list[EventTemplate],
    force: bool = False,
) -> Optional[Event]:
    rng = random.Random(world.seed * 1000003 + world.tick)'''

new_sig = '''async def run_event_cycle(
    session: Session,
    world: World,
    templates: list[EventTemplate],
    force: bool = False,
    attempt: int = 0,
) -> Optional[Event]:
    rng = random.Random(world.seed * 1000003 + world.tick + attempt * 7919)'''

if old_sig in t:
    t = t.replace(old_sig, new_sig, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] run_event_cycle 加 attempt 参数")
elif "attempt: int = 0" in t:
    print("[skip] 已有 attempt 参数")
else:
    print("[fail] event_flow.py 签名未匹配")

# ============================================================
# 2. main.py：重写 trigger_event 端点
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

start = t.find('@app.post("/event/trigger")')
if start < 0:
    print("[fail] 找不到 trigger_event 端点")
    raise SystemExit(1)

end = t.find('\n@app.', start + 10)
if end < 0:
    end = len(t)

new_endpoint = '''@app.post("/event/trigger")
async def trigger_event() -> dict:
    with get_session() as s:
        world = load_world(s)
        templates = director.load_templates()

        # 最多重试 5 次，每次换 rng 种子
        event = None
        for attempt in range(5):
            try:
                event = await asyncio.wait_for(
                    run_event_cycle(
                        s, world, templates,
                        force=True, attempt=attempt,
                    ),
                    timeout=30.0,
                )
            except asyncio.TimeoutError:
                print("[trigger] 尝试 %d 超时（30s），继续" % attempt)
                continue

            if event is not None:
                break
            print("[trigger] 尝试 %d 未生成事件，继续" % attempt)

        if event is None:
            raise HTTPException(
                400,
                "5 次尝试都没能生成合理的事件，请稍后再试或推进时间",
            )

        npc_names = {n.id: n.name for n in load_npcs(s)}
        row = s.get(EventRow, event.id)
        if row is None:
            raise HTTPException(500, "event saved but not found")
        return _row_to_event(row, npc_names)'''

t = t[:start] + new_endpoint + t[end:]
p.write_text(t, encoding="utf-8")
print("[fix] trigger_event 端点重写")

# ============================================================
# 3. 检查 asyncio 导入
# ============================================================
t2 = p.read_text(encoding="utf-8")
if "import asyncio" not in t2.split("\n")[0:30]:
    print("[warn] main.py 缺 import asyncio，请手动加")
else:
    print("[ok] asyncio 已导入")

print()
print("重启后端：Ctrl+C 后 uvicorn server.main:app --reload")