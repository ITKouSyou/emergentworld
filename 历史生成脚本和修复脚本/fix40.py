# 预扫不可能模板 + 减少重试
from pathlib import Path

# ============================================================
# 1. event_flow.py：加预扫函数
# ============================================================
p = Path("server/core/event_flow.py")
t = p.read_text(encoding="utf-8")

if "def impossible_templates" not in t:
    anchor = "def _participants_valid("
    addition = '''def impossible_templates(templates, npcs) -> set:
    """扫一遍所有 NPC，找出当前环境下不可能满足条件的模板 id。"""
    has_children = any(n.family.children for n in npcs)
    has_spouse = any(n.family.spouse for n in npcs)
    no_spouse = any(not n.family.spouse and n.age >= 18 for n in npcs)
    has_family = any(
        n.family.spouse or n.family.children or n.family.parents
        for n in npcs
    )

    result: set = set()
    for tpl in templates:
        req = TEMPLATE_REQUIRES.get(tpl.id)
        if req == "has_children" and not has_children:
            result.add(tpl.id)
        elif req == "has_spouse" and not has_spouse:
            result.add(tpl.id)
        elif req == "no_spouse" and not no_spouse:
            result.add(tpl.id)
        elif req == "has_family" and not has_family:
            result.add(tpl.id)
    return result


def _participants_valid('''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] event_flow 加 impossible_templates")
    else:
        print("[fail] event_flow 锚点未找到")
else:
    print("[skip] event_flow 已有 impossible_templates")

# ============================================================
# 2. main.py：trigger_event 用预扫
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
    from server.core import event_flow as _ef

    with get_session() as s:
        world = load_world(s)
        templates = director.load_templates()

        # 预扫不可能满足的模板
        all_npcs = load_npcs(s)
        exclude = _ef.impossible_templates(templates, all_npcs)
        if exclude:
            print("[trigger] 预扫排除不可能模板：%s" % sorted(exclude))

        event = None
        tried = 0

        for attempt in range(3):
            remaining = [t for t in templates if t.id not in exclude]
            if not remaining:
                break

            seed_extra = random.randint(0, 10**9)
            tried += 1

            try:
                event = await asyncio.wait_for(
                    run_event_cycle(
                        s, world, remaining,
                        force=True, attempt=seed_extra,
                    ),
                    timeout=25.0,
                )
            except asyncio.TimeoutError:
                print("[trigger] attempt %d 超时（25s）" % attempt)
                continue

            if event is not None:
                break

            rejected = _ef.get_last_rejected_template_id()
            if rejected:
                exclude.add(rejected)
                print("[trigger] attempt %d 被拒：%s" % (attempt, rejected))

        if event is None:
            raise HTTPException(
                400,
                "尝试 %d 次都没能生成合理事件，请换个时间或推进几回合" % tried,
            )

        npc_names = {n.id: n.name for n in load_npcs(s)}
        row = s.get(EventRow, event.id)
        if row is None:
            raise HTTPException(500, "event saved but not found")
        return _row_to_event(row, npc_names)'''

t = t[:start] + new_endpoint + t[end:]
p.write_text(t, encoding="utf-8")
print("[fix] trigger_event 用预扫 + 3 次重试")

print()
print("========== 完成 ==========")
print("重启后端：Ctrl+C 后 uvicorn server.main:app --reload")
print()
print("现在的逻辑：")
print("  1. 启动时扫一遍：哪些模板当前 NPC 环境不可能满足 → 排除")
print("  2. 剩下 3 次重试，每次换种子")
print("  3. 每次最多 25 秒超时")
print("  4. 总时长上限 75 秒，不会卡到 180 秒")