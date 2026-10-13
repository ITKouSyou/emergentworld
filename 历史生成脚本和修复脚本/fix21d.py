# 诊断 + 后端补 tags
from pathlib import Path

# ============================================================
# 1. 诊断：看 _on_chronicle_list 是否真的做了替换
# ============================================================
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")
i = t.find("func _on_chronicle_list")
if i >= 0:
    e = t.find("\n\nfunc ", i + 1)
    print("=== _on_chronicle_list 当前内容 ===")
    print(t[i:e if e > 0 else len(t)])
    print()

# ============================================================
# 2. 后端：_row_to_event 从模板反查 tags
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

old = '''        "relevance_score": payload.get("relevance_score", 0.0),
        "tags": payload.get("tpl_tags", []),
        "created_at": r.created_at, "resolved_at": r.resolved_at,'''

new = '''        "relevance_score": payload.get("relevance_score", 0.0),
        "tags": _event_tags(r.template_id, payload),
        "created_at": r.created_at, "resolved_at": r.resolved_at,'''

if old in t:
    t = t.replace(old, new, 1)
    print("[fix] main.py tags 改用 _event_tags")
elif '"tags": _event_tags' in t:
    print("[skip] main.py 已用 _event_tags")
else:
    print("[fail] main.py tags 行未匹配")

# 加辅助函数
if "def _event_tags" not in t:
    anchor = "def _row_to_event("
    addition = '''def _event_tags(template_id: str, payload: dict) -> list:
    """从 payload 或模板缓存里取 tags。"""
    payload_tags = payload.get("tpl_tags")
    if isinstance(payload_tags, list) and payload_tags:
        return list(payload_tags)

    # 从 director 的模板缓存里查
    try:
        from server.core import director
        for tpl in director.load_templates():
            if tpl.id == template_id:
                return list(tpl.tags)
    except Exception:
        pass

    # 玩家行动
    if template_id in ("explore", "gather", "hunt", "train", "socialize", "travel"):
        return ["action"]

    return []


def _row_to_event('''

    if anchor in t and "def _event_tags" not in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] 加 _event_tags 辅助函数")
    else:
        print("[fail] 加 _event_tags 锚点未找到")
else:
    p.write_text(t, encoding="utf-8")
    print("[skip] 已有 _event_tags")

# ============================================================
# 3. reward.py：按事件 tags 生成不同 kind
# ============================================================
p = Path("server/generators/reward.py")
t = p.read_text(encoding="utf-8")

old_reward = '''async def generate_reward(event: Event, world: World) -> Reward:
    budget = compute_budget(event, world)
    value = min(budget, 1.0)
    tpl_zh = template_label(event.template_id)

    item = await generate_item(event, world, value)

    summary = str(event.payload.get("summary", "")).strip()
    if summary:
        description = "%s 的结局：%s" % (tpl_zh, summary[:40])
    else:
        description = "%s的奖励" % tpl_zh

    return Reward(
        id="rwd_%s" % uuid.uuid4().hex[:8],
        event_id=event.id,
        kind="item",
        value=value,
        description=description,
        payload={"item": item},
    )'''

new_reward = '''KIND_BY_TAG = {
    "trade": "item",
    "mystery": "info",
    "investigation": "info",
    "plot": "story",
    "political": "reputation",
    "romance": "relationship",
    "social": "relationship",
    "celebration": "relationship",
    "conflict": "info",
    "combat": "item",
    "survival": "skill",
    "adventure": "item",
    "daily": "item",
    "ritual": "story",
}


def _pick_kind(event: Event, rng_choice) -> str:
    tags = list(event.payload.get("tpl_tags", []) or [])
    if not tags:
        # 用 template_id 反查
        try:
            from server.core import director
            for tpl in director.load_templates():
                if tpl.id == event.template_id:
                    tags = list(tpl.tags)
                    break
        except Exception:
            pass
    candidates = [KIND_BY_TAG.get(t) for t in tags if KIND_BY_TAG.get(t)]
    if candidates:
        return rng_choice(candidates)
    return "item"


async def generate_reward(event: Event, world: World) -> Reward:
    import random as _r
    rng = _r.Random(hash(event.id) & 0xFFFF)

    budget = compute_budget(event, world)
    value = min(budget, 1.0)
    tpl_zh = template_label(event.template_id)

    kind = _pick_kind(event, rng.choice)

    item = None
    if kind == "item":
        item = await generate_item(event, world, value)

    summary = str(event.payload.get("summary", "")).strip()
    if summary:
        description = "%s：%s" % (tpl_zh, summary[:40])
    else:
        description = "%s的奖励" % tpl_zh

    payload = {}
    if item is not None:
        payload["item"] = item

    return Reward(
        id="rwd_%s" % uuid.uuid4().hex[:8],
        event_id=event.id,
        kind=kind,
        value=value,
        description=description,
        payload=payload,
    )'''

if old_reward in t:
    t = t.replace(old_reward, new_reward, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] reward.py 按 tag 生成 kind")
else:
    print("[fail] reward.py 未匹配（可能已改过）")

# ============================================================
# 4. event_flow：非交互分支补 tpl_tags
# ============================================================
p = Path("server/core/event_flow.py")
t = p.read_text(encoding="utf-8")

if 'event.payload["tpl_tags"] = list(tpl.tags)' not in t:
    # 找两个非交互分支
    old1 = '''    if not tpl.interactive:
        event.payload["tpl_tags"] = list(tpl.tags)
        event.state = "active"'''
    old2 = '''    if not tpl.interactive:
        event.state = "active"'''
    if old1 in t:
        print("[skip] event_flow 已加 tpl_tags")
    elif old2 in t:
        t = t.replace(old2, old1, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] event_flow 非交互分支加 tpl_tags")
    else:
        print("[fail] event_flow 未匹配")

    # 相关性判定后也无交互分支
    old3 = '''    if (not tpl.interactive) or (not relevance_ok):
        event.state = "active"'''
    new3 = '''    if (not tpl.interactive) or (not relevance_ok):
        event.payload["tpl_tags"] = list(tpl.tags)
        event.state = "active"'''
    t = p.read_text(encoding="utf-8")
    if old3 in t and 'event.payload["tpl_tags"]' not in t.split(old3)[0][-200:]:
        t = t.replace(old3, new3, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] event_flow 相关性分支加 tpl_tags")

print()
print("重启 uvicorn：Ctrl+C 后 uvicorn server.main:app --reload")