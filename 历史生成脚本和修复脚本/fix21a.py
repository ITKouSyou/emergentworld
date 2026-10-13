# 让事件返回里包含 tags 字段（用于前端筛选）
from pathlib import Path

# 1. event_flow.py：非交互事件也存 tpl_tags
p = Path("server/core/event_flow.py")
t = p.read_text(encoding="utf-8")

old = '''    if not tpl.interactive:
        event.state = "active"
        save_event(session, event)'''
new = '''    if not tpl.interactive:
        event.payload["tpl_tags"] = list(tpl.tags)
        event.state = "active"
        save_event(session, event)'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] event_flow 非交互分支加 tpl_tags")
else:
    print("[skip] event_flow 已改过")

# 2. main.py 的 _row_to_event 加 tags
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

old = '''        "relevance_score": payload.get("relevance_score", 0.0),
        "created_at": r.created_at, "resolved_at": r.resolved_at,'''
new = '''        "relevance_score": payload.get("relevance_score", 0.0),
        "tags": payload.get("tpl_tags", []),
        "created_at": r.created_at, "resolved_at": r.resolved_at,'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] main.py 加 tags")
else:
    print("[skip] main.py 已改过或未匹配")

# 3. 玩家行动/travel 也加 tags（可选）
old2 = '''                    "interactive": False,
                    "as_message": True,
                    "is_player_action": True,
                },'''
new2 = '''                    "interactive": False,
                    "as_message": True,
                    "is_player_action": True,
                    "tpl_tags": ["action"],
                },'''
if old2 in t:
    t = t.replace(old2, new2, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 玩家行动加 tags")
else:
    print("[skip] 玩家行动已改过")