# Part 20D：修探索 + 玩家移动 + 探索记录 + 史册增量
from pathlib import Path

# ============================================================
# 1. 重写 explore.py
# ============================================================
p = Path("server/systems/explore.py")
p.write_text('''# 探索系统
from __future__ import annotations

import json
import random
import uuid

from sqlmodel import Session

from server.i18n import location_label
from server.map_layout import LOCATION_LAYOUT, hidden_location_ids
from server.models.db import WorldRow
from server.models.schemas import Player, World
from server.systems import player as player_sys

LOCATION_DIFFICULTY = {
    "deep_forest": "normal",
    "old_mine": "normal",
    "river_bend": "easy",
    "old_shrine": "hard",
    "abandoned_farm": "easy",
    "mountain_pass": "hard",
}

LOCATION_FLAVORS = {
    "deep_forest": "幽深的林间，你拨开纠缠的藤蔓。",
    "old_mine": "废矿的入口塌了一半，空气里满是铁锈味。",
    "river_bend": "河水在此拐弯，冲积出一片细沙滩。",
    "old_shrine": "残破的神像倒在草丛里，香炉早已冰冷。",
    "abandoned_farm": "农舍的屋顶已经塌了，院里的井还盖着。",
    "mountain_pass": "山风呼啸，一条小径隐没在云雾里。",
}


def get_discovered(session: Session, world_id: str) -> list[str]:
    row = session.get(WorldRow, world_id)
    if row is None:
        return []
    return json.loads(row.location_ids_json or "[]")


def add_discovered(session: Session, world_id: str, loc_id: str) -> None:
    row = session.get(WorldRow, world_id)
    if row is None:
        return
    cur = json.loads(row.location_ids_json or "[]")
    if loc_id not in cur:
        cur.append(loc_id)
    row.location_ids_json = json.dumps(cur, ensure_ascii=False)
    session.add(row)
    session.commit()


def pick_undiscovered_location(session, world, rng):
    discovered = get_discovered(session, world.id)
    candidates = [loc for loc in hidden_location_ids() if loc not in discovered]
    if not candidates:
        return None
    return rng.choice(candidates)


async def explore_once(session: Session, world: World, player: Player) -> dict:
    rng = random.Random(world.seed * 77771 + world.tick)
    origin = player.location_id or "village_square"
    target = pick_undiscovered_location(session, world, rng)
    if target is None:
        return {
            "ok": True,
            "kind": "no_more",
            "message": "附近的地界你已经走遍了。",
            "check": None,
            "found_location": False,
            "found_item": None,
            "exp_gain": 0,
        }

    difficulty = LOCATION_DIFFICULTY.get(target, "normal")
    check = player_sys.roll_check(player, "perception", difficulty, rng)
    result = check["result"]
    flavor = LOCATION_FLAVORS.get(target, "你向前走去。")

    response = {
        "ok": True,
        "kind": "explore",
        "origin": origin,
        "origin_label": location_label(origin),
        "target_id": target,
        "target_label": location_label(target),
        "check": check,
        "flavor": flavor,
        "found_location": False,
        "found_item": None,
        "message": "",
        "exp_gain": 0,
    }

    if result == "critical":
        add_discovered(session, world.id, target)
        # 同步内存对象，避免后面 save_world 覆盖
        if target not in world.location_ids:
            world.location_ids.append(target)
        # 玩家移动到新地点
        player.location_id = target
        player_sys.save_player(session, player)
        response["found_location"] = True
        response["found_item"] = _generate_find_item(target, rng)
        response["message"] = "你不仅找到了入口，还捡到了一件东西。"
        response["exp_gain"] = 30
    elif result == "success":
        add_discovered(session, world.id, target)
        if target not in world.location_ids:
            world.location_ids.append(target)
        player.location_id = target
        player_sys.save_player(session, player)
        response["found_location"] = True
        response["message"] = "你发现了新的去处。"
        response["exp_gain"] = 20
    elif result == "partial":
        response["message"] = "你察觉到一点踪迹，但没能深入。"
        response["exp_gain"] = 8
    else:
        response["message"] = "你一无所获，还浪费了半天。"
        response["exp_gain"] = 2

    if response["exp_gain"] > 0:
        player_sys.add_exp(session, response["exp_gain"])

    return response


def _generate_find_item(loc_id: str, rng: random.Random) -> dict:
    templates = {
        "deep_forest": [("草编药囊", "草药"), ("鹿角", "杂物"), ("松果油", "药材")],
        "old_mine": [("铁矿石", "矿石"), ("矿灯", "工具"), ("生锈的镐头", "工具")],
        "river_bend": [("光滑的卵石", "饰物"), ("河蚌", "食材"), ("浮木", "杂物")],
        "old_shrine": [("断香", "信物"), ("青铜符", "信物"), ("古钱币", "古物")],
        "abandoned_farm": [("陈年酒坛", "酒"), ("破陶碗", "杂物"), ("锈镰刀", "工具")],
        "mountain_pass": [("山参", "药材"), ("旧罗盘", "工具"), ("风化石", "矿石")],
    }
    pool = templates.get(loc_id, [("无名石", "杂物")])
    name, kind = rng.choice(pool)
    affixes = rng.sample(["古老的", "磨损的", "半掩于土中的", "有点古怪的"], 1)
    return {
        "id": "itm_%s" % uuid.uuid4().hex[:8],
        "name": name,
        "kind": kind,
        "affixes": affixes,
        "story": "从%s带回。" % location_label(loc_id),
        "value": round(rng.uniform(0.1, 0.4), 2),
    }
''', encoding="utf-8")
print("[write] server/systems/explore.py")

# ============================================================
# 2. 重写 chronicle.py（增量生成）
# ============================================================
p = Path("server/systems/chronicle.py")
p.write_text('''# 编年史：增量生成
from __future__ import annotations

import uuid
from typing import Optional

from sqlmodel import Session, select

from server.generators.base import get_llm, load_prompt
from server.models.db import ChronicleRow, EventRow, loads


def _collect_since(session: Session, since_tick: int, limit: int = 60) -> list[str]:
    rows = session.exec(
        select(EventRow)
        .where(EventRow.created_at > since_tick)
        .order_by(EventRow.created_at.asc())
        .limit(limit)
    ).all()
    lines: list[str] = []
    for r in rows:
        payload = loads(r.payload_json) or {}
        summary = payload.get("summary") or ""
        outcome = payload.get("outcome") or ""
        line = "- [%s] %s" % (r.template_id, summary)
        if outcome:
            line += "  →  %s" % outcome
        lines.append(line)
    return lines


def _fallback_body(events: list[str]) -> str:
    if not events:
        return "（这段时间村里风平浪静。）"
    return "近日要闻：\\n" + "\\n".join(events[-10:])


async def generate_chronicle(
    session: Session,
    from_tick: int = 0,
    to_tick: int = 0,
    title_hint: str = "",
) -> Optional[dict]:
    # 找上一次史册的 to_tick
    last = session.exec(
        select(ChronicleRow).order_by(ChronicleRow.created_at.desc()).limit(1)
    ).first()
    since = last.to_tick if last else from_tick

    events = _collect_since(session, since, limit=60)

    if not events:
        body = "（上次史册之后，村里暂无新的记载。）"
        title = title_hint or "第 %d tick 记" % to_tick
        row = ChronicleRow(
            id="chr_%s" % uuid.uuid4().hex[:8],
            title=title,
            body=body,
            from_tick=since,
            to_tick=to_tick,
            created_at=to_tick,
        )
        session.add(row)
        session.commit()
        return {
            "id": row.id, "title": row.title, "body": row.body,
            "from_tick": row.from_tick, "to_tick": row.to_tick,
            "created_at": row.created_at,
        }

    prompt = load_prompt("chronicle.md").format(events="\\n".join(events))
    body = ""
    try:
        body = await get_llm().text(prompt)
    except Exception:
        body = _fallback_body(events)

    if not body.strip():
        body = _fallback_body(events)

    title = title_hint or "第 %d tick 记" % to_tick

    row = ChronicleRow(
        id="chr_%s" % uuid.uuid4().hex[:8],
        title=title,
        body=body.strip(),
        from_tick=since,
        to_tick=to_tick,
        created_at=to_tick,
    )
    session.add(row)
    session.commit()

    return {
        "id": row.id, "title": row.title, "body": row.body,
        "from_tick": row.from_tick, "to_tick": row.to_tick,
        "created_at": row.created_at,
    }


def list_chronicles(session: Session, limit: int = 20) -> list[dict]:
    rows = session.exec(
        select(ChronicleRow).order_by(ChronicleRow.created_at.desc()).limit(limit)
    ).all()
    return [
        {
            "id": r.id, "title": r.title, "body": r.body,
            "from_tick": r.from_tick, "to_tick": r.to_tick,
            "created_at": r.created_at,
        }
        for r in rows
    ]
''', encoding="utf-8")
print("[write] server/systems/chronicle.py")

# ============================================================
# 3. main.py 的 /explore 端点：加事件记录
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

old = '''        result = await explore_sys.explore_once(s, world, player)

        # 处理物品入库
        item_data = result.get("found_item")'''

new = '''        result = await explore_sys.explore_once(s, world, player)

        # 生成一条探索事件记录
        try:
            from server.models.schemas import Event as EventModel
            evt_id = "evt_exp_%s" % __import__("uuid").uuid4().hex[:8]
            summary = "你离开村庄四处探寻"
            if result.get("found_location"):
                summary = "你发现了【%s】" % str(result.get("target_label", ""))
            elif result.get("kind") == "no_more":
                summary = "附近的地界你已经走遍了"
            else:
                summary = "你四处探寻，但一无所获"

            evt = EventModel(
                id=evt_id,
                template_id="explore",
                participants=["player"],
                location_id=result.get("target_id", player.location_id),
                state="resolved",
                payload={
                    "summary": summary,
                    "narrative": str(result.get("flavor", "")),
                    "outcome": str(result.get("message", "")),
                    "check": result.get("check") or {},
                    "exp_gain": int(result.get("exp_gain", 0)),
                    "interactive": False,
                    "as_message": True,
                },
                created_at=world.tick,
                resolved_at=world.tick,
            )
            save_event(s, evt)
        except Exception as e:
            print("[explore] 事件记录失败：%s" % e)

        # 处理物品入库
        item_data = result.get("found_item")'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] main.py /explore 加事件记录")
else:
    print("[skip] main.py /explore 已改过或锚点未匹配")

# ============================================================
# 4. i18n 补 explore 事件名
# ============================================================
p = Path("server/i18n.py")
t = p.read_text(encoding="utf-8")
if '"explore"' not in t:
    anchor = '    "execution": "公开处刑",\n'
    if anchor in t:
        t = t.replace(anchor, anchor + '    "explore": "外出探索",\n', 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] i18n 加 explore")
    else:
        print("[skip] i18n explore 锚点未找到")
else:
    print("[skip] i18n 已有 explore")

print()
print("============================")
print("完成后：")
print("  1. 重启 uvicorn（Ctrl+C 后重新运行）")
print("  2. Godot 完全关闭再打开（不是按 F5）")
print("============================")