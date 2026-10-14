# Part 39：过滤 rejected + 重试换种子 + 跳过被拒模板
from pathlib import Path

# ============================================================
# 1. event_flow.py：不写 rejected 到数据库 + 记录被拒模板
# ============================================================
p = Path("server/core/event_flow.py")
t = p.read_text(encoding="utf-8")

# 1.1 加模块级变量
if "_last_rejected_template_id" not in t:
    anchor = "PLAYER_TIMEOUT_TICKS = 8"
    addition = '''PLAYER_TIMEOUT_TICKS = 8

# 最近一次因参与者不合适被拒的模板 id
_last_rejected_template_id: str = ""


def get_last_rejected_template_id() -> str:
    return _last_rejected_template_id

'''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        print("[fix] event_flow 加 _last_rejected_template_id")

# 1.2 修改参与者校验分支
old = '''    # 参与者合理性校验
    npcs_by_id = {n.id: n for n in npcs}
    if not _participants_valid(tpl, event.participants, npcs_by_id):
        print("[event] 参与者不满足 %s 的前置条件，拒绝：%s" % (
            tpl.id, event.participants))
        event.state = "rejected"
        save_event(session, event)
        return None'''

new = '''    # 参与者合理性校验
    global _last_rejected_template_id
    npcs_by_id = {n.id: n for n in npcs}
    if not _participants_valid(tpl, event.participants, npcs_by_id):
        print("[event] 参与者不满足 %s 的前置条件，跳过：%s" % (
            tpl.id, event.participants))
        _last_rejected_template_id = tpl.id
        # 不写数据库
        return None'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] event_flow 不写 rejected")
else:
    print("[skip] event_flow 已改过或锚点未匹配")

# ============================================================
# 2. main.py：trigger_event 重写
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

        exclude: set[str] = set()
        event = None

        for attempt in range(8):
            remaining = [t for t in templates if t.id not in exclude]
            if not remaining:
                break

            # 每次尝试都用不同随机种子
            seed_extra = random.randint(0, 10**9)

            try:
                event = await asyncio.wait_for(
                    run_event_cycle(
                        s, world, remaining,
                        force=True, attempt=seed_extra,
                    ),
                    timeout=30.0,
                )
            except asyncio.TimeoutError:
                print("[trigger] attempt %d 超时" % attempt)
                continue

            if event is not None:
                break

            rejected = _ef.get_last_rejected_template_id()
            if rejected:
                exclude.add(rejected)
                print("[trigger] attempt %d 被拒模板：%s，累计排除 %d 个"
                      % (attempt, rejected, len(exclude)))

        if event is None:
            raise HTTPException(
                400,
                "当前村庄没有适合触发的剧情，换几个 NPC 或推进时间试试",
            )

        npc_names = {n.id: n.name for n in load_npcs(s)}
        row = s.get(EventRow, event.id)
        if row is None:
            raise HTTPException(500, "event saved but not found")
        return _row_to_event(row, npc_names)'''

t = t[:start] + new_endpoint + t[end:]
p.write_text(t, encoding="utf-8")
print("[fix] trigger_event 重写")

# ============================================================
# 3. main.py：/event 列表过滤 rejected
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

old_event = '''@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:
    with get_session() as s:
        npc_names = {n.id: n.name for n in load_npcs(s)}
        rows = s.exec(
            select(EventRow).order_by(EventRow.created_at.desc()).limit(limit)
        ).all()
        return [_row_to_event(r, npc_names) for r in rows]'''

new_event = '''@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:
    with get_session() as s:
        npc_names = {n.id: n.name for n in load_npcs(s)}
        rows = s.exec(
            select(EventRow)
            .where(EventRow.state != "rejected")
            .order_by(EventRow.created_at.desc())
            .limit(limit)
        ).all()
        return [_row_to_event(r, npc_names) for r in rows]'''

if old_event in t:
    t = t.replace(old_event, new_event, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] /event 过滤 rejected")
else:
    print("[skip] /event 已改过")

print()
print("========== 完成 ==========")
print("重启后端：Ctrl+C 后 uvicorn server.main:app --reload")
print()
print("修复后：")
print("  - 被拒事件不写数据库")
print("  - 重试换随机种子")
print("  - 每次尝试排除已拒模板")
print("  - 事件列表隐藏 rejected")
print()
print("注意：")
print("  你现在的 10 个 NPC 都没子女，lost_child 还是无法生成。")
print("  想解锁：清库重 seed（命令见下）")
print()
print("  Remove-Item data\\world.db")
print("  python tools\\seed_world.py --npc 14")
print("  uvicorn server.main:app --reload")