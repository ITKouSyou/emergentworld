# Part 20E：行动系统（探索/采集/打猎/修炼/社交）+ 世界同步
from pathlib import Path

# ============================================================
# 1. 写 actions.py
# ============================================================
Path("server/systems/actions.py").write_text('''# 玩家行动：探索、采集、打猎、修炼、社交
from __future__ import annotations

import json
import random
import uuid

from sqlmodel import Session

from server.i18n import location_label
from server.map_layout import hidden_location_ids
from server.models.db import WorldRow
from server.models.schemas import Player, World
from server.systems import player as player_sys


ACTION_META = {
    "explore":   {"label": "外出探索", "attribute": "perception", "difficulty": "normal", "desc": "寻找未知的地方"},
    "gather":    {"label": "采集",     "attribute": "perception", "difficulty": "easy",   "desc": "在当前区域收集材料"},
    "hunt":      {"label": "打猎",     "attribute": "agility",    "difficulty": "normal", "desc": "追捕野生动物"},
    "train":     {"label": "修炼",     "attribute": "strength",   "difficulty": "easy",   "desc": "锻炼身体"},
    "socialize": {"label": "社交",     "attribute": "charisma",   "difficulty": "easy",   "desc": "与附近的人交谈"},
}


EXPLORE_DIFFICULTY = {
    "deep_forest": "normal", "old_mine": "normal", "river_bend": "easy",
    "old_shrine": "hard", "abandoned_farm": "easy", "mountain_pass": "hard",
}

EXPLORE_FLAVORS = {
    "deep_forest": "幽深的林间，你拨开纠缠的藤蔓。",
    "old_mine": "废矿的入口塌了一半，空气里满是铁锈味。",
    "river_bend": "河水在此拐弯，冲积出一片细沙滩。",
    "old_shrine": "残破的神像倒在草丛里，香炉早已冰冷。",
    "abandoned_farm": "农舍的屋顶已经塌了，院里的井还盖着。",
    "mountain_pass": "山风呼啸，一条小径隐没在云雾里。",
}

GATHER_POOL = {
    "village_square": [("野草", "草药"), ("旧铜钱", "古物"), ("小石子", "杂物")],
    "market": [("散落铜钱", "杂物"), ("碎布头", "布料")],
    "tavern": [("空酒壶", "杂物"), ("木屑", "杂物")],
    "home": [("旧布", "布料"), ("柴火", "燃料")],
    "forest": [("松果", "食材"), ("野菌", "食材"), ("草药", "草药")],
    "village_edge": [("柴火", "燃料"), ("鸟蛋", "食材")],
    "village_hall": [("旧纸", "杂物")],
    "deep_forest": [("百年参", "药材"), ("鹿茸", "药材")],
    "old_mine": [("铁矿", "矿石"), ("煤块", "燃料")],
    "river_bend": [("河蚌", "食材"), ("芦苇", "材料")],
    "old_shrine": [("香灰", "信物"), ("古钱", "古物")],
    "abandoned_farm": [("干草", "材料"), ("旧钉", "杂物")],
    "mountain_pass": [("云母石", "矿石"), ("野草", "草药")],
}

HUNT_POOL = {
    "forest": [("野兔", "猎物"), ("山鸡", "猎物")],
    "village_edge": [("野兔", "猎物")],
    "deep_forest": [("野鹿", "猎物"), ("野猪", "猎物")],
    "mountain_pass": [("岩羊", "猎物")],
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


def _make_item(name: str, kind: str, story: str, rng: random.Random) -> dict:
    affixes = rng.sample(["古老的", "磨损的", "新鲜的", "常见的"], 1)
    return {
        "id": "itm_%s" % uuid.uuid4().hex[:8],
        "name": name, "kind": kind, "affixes": affixes,
        "story": story, "value": round(rng.uniform(0.05, 0.4), 2),
    }


def _pick_undiscovered(session, world, rng):
    discovered = get_discovered(session, world.id)
    candidates = [loc for loc in hidden_location_ids() if loc not in discovered]
    if not candidates:
        return None
    return rng.choice(candidates)


async def do_action(session: Session, world: World, player: Player, action: str) -> dict:
    rng = random.Random(world.seed * 77771 + world.tick * 13 + hash(action))
    if action not in ACTION_META:
        return {"ok": False, "error": "unknown action: %s" % action}

    meta = ACTION_META[action]
    origin = player.location_id or "village_square"

    result = {
        "ok": True, "kind": action,
        "action_label": meta["label"],
        "origin": origin,
        "origin_label": location_label(origin),
        "check": None, "found_location": None, "found_item": None,
        "message": "", "exp_gain": 0, "summary": "",
        "target_id": "", "target_label": "", "flavor": "",
    }

    if action == "explore":
        return await _do_explore(session, world, player, origin, rng, result)
    if action == "gather":
        return _do_gather(session, world, player, origin, rng, result)
    if action == "hunt":
        return _do_hunt(session, world, player, origin, rng, result)
    if action == "train":
        return _do_train(session, world, player, rng, result)
    if action == "socialize":
        return _do_socialize(session, world, player, rng, result)
    return result


async def _do_explore(session, world, player, origin, rng, result):
    target = _pick_undiscovered(session, world, rng)
    if target is None:
        result["message"] = "附近的地界你已经走遍了。"
        result["summary"] = "你四处走了走，但附近已经没什么新鲜的了。"
        return result

    difficulty = EXPLORE_DIFFICULTY.get(target, "normal")
    check = player_sys.roll_check(player, "perception", difficulty, rng)
    result["check"] = check
    result["target_id"] = target
    result["target_label"] = location_label(target)
    result["flavor"] = EXPLORE_FLAVORS.get(target, "你向前走去。")

    if check["result"] == "critical":
        add_discovered(session, world.id, target)
        if target not in world.location_ids:
            world.location_ids.append(target)
        player.location_id = target
        player_sys.save_player(session, player)
        result["found_location"] = True
        name, kind = rng.choice([("草药", "草药"), ("旧物", "古物")])
        result["found_item"] = _make_item(name, kind, "从%s带回。" % location_label(target), rng)
        result["message"] = "你不仅找到了入口，还捡到了一件东西。"
        result["exp_gain"] = 30
        result["summary"] = "你发现了【%s】" % location_label(target)
    elif check["result"] == "success":
        add_discovered(session, world.id, target)
        if target not in world.location_ids:
            world.location_ids.append(target)
        player.location_id = target
        player_sys.save_player(session, player)
        result["found_location"] = True
        result["message"] = "你发现了新的去处。"
        result["exp_gain"] = 20
        result["summary"] = "你发现了【%s】" % location_label(target)
    elif check["result"] == "partial":
        result["message"] = "你察觉到一点踪迹，但没能深入。"
        result["exp_gain"] = 8
        result["summary"] = "你循着一些痕迹找了找，但没能找到什么"
    else:
        result["message"] = "你一无所获，还浪费了半天。"
        result["exp_gain"] = 2
        result["summary"] = "你在附近转了一圈，没什么发现"

    if result["exp_gain"] > 0:
        player_sys.add_exp(session, result["exp_gain"])
    return result


def _do_gather(session, world, player, origin, rng, result):
    pool = GATHER_POOL.get(origin, [("杂物", "杂物")])
    check = player_sys.roll_check(player, "perception", "easy", rng)
    result["check"] = check

    if check["result"] in ("critical", "success"):
        name, kind = rng.choice(pool)
        result["found_item"] = _make_item(name, kind, "在%s捡到。" % location_label(origin), rng)
        result["message"] = "你在附近捡到了一些东西。"
        result["exp_gain"] = 10 if check["result"] == "success" else 15
        result["summary"] = "你在%s采集到【%s】" % (location_label(origin), name)
    elif check["result"] == "partial":
        result["message"] = "你找了一阵，没找到什么有用的。"
        result["exp_gain"] = 5
        result["summary"] = "你在%s采集了一阵，所获不多" % location_label(origin)
    else:
        result["message"] = "你什么都没找到。"
        result["exp_gain"] = 2
        result["summary"] = "你在%s采集，一无所获" % location_label(origin)

    if result["exp_gain"] > 0:
        player_sys.add_exp(session, result["exp_gain"])
    return result


def _do_hunt(session, world, player, origin, rng, result):
    pool = HUNT_POOL.get(origin)
    if not pool:
        result["message"] = "%s没有可猎的动物。" % location_label(origin)
        result["summary"] = "你在%s想打猎，但这里没有猎物" % location_label(origin)
        player_sys.add_exp(session, 2)
        result["exp_gain"] = 2
        return result

    check = player_sys.roll_check(player, "agility", "normal", rng)
    result["check"] = check

    if check["result"] in ("critical", "success"):
        name, kind = rng.choice(pool)
        result["found_item"] = _make_item(name, kind, "在%s猎得。" % location_label(origin), rng)
        result["exp_gain"] = 25 if check["result"] == "critical" else 15
        result["message"] = "你猎到一只猎物。"
        result["summary"] = "你在%s猎得【%s】" % (location_label(origin), name)
    elif check["result"] == "partial":
        result["message"] = "你追了一阵，猎物跑掉了。"
        result["exp_gain"] = 8
        result["summary"] = "你在%s打猎，追了一阵，猎物跑了" % location_label(origin)
    else:
        result["message"] = "你什么都没猎到。"
        result["exp_gain"] = 3
        result["summary"] = "你在%s打猎，空手而归" % location_label(origin)

    if result["exp_gain"] > 0:
        player_sys.add_exp(session, result["exp_gain"])
    return result


def _do_train(session, world, player, rng, result):
    check = player_sys.roll_check(player, "strength", "easy", rng)
    result["check"] = check
    if check["result"] == "critical":
        result["message"] = "你感觉自己比昨天更强了一点。"
        result["exp_gain"] = 35
        result["summary"] = "你练了一阵子武，颇有收获"
    elif check["result"] == "success":
        result["message"] = "你练了一阵。"
        result["exp_gain"] = 25
        result["summary"] = "你练了一阵子武"
    elif check["result"] == "partial":
        result["message"] = "你练得有点累。"
        result["exp_gain"] = 12
        result["summary"] = "你练了一会儿"
    else:
        result["message"] = "你心不在焉，没练出什么。"
        result["exp_gain"] = 5
        result["summary"] = "你勉强练了一会儿"
    player_sys.add_exp(session, result["exp_gain"])
    return result


def _do_socialize(session, world, player, rng, result):
    check = player_sys.roll_check(player, "charisma", "easy", rng)
    result["check"] = check
    if check["result"] == "critical":
        result["message"] = "你和几位村人相谈甚欢。"
        result["exp_gain"] = 20
        result["summary"] = "你和村人谈得很愉快"
    elif check["result"] == "success":
        result["message"] = "你和几个人聊了聊。"
        result["exp_gain"] = 12
        result["summary"] = "你和村人闲聊了一阵"
    elif check["result"] == "partial":
        result["message"] = "你和人聊了几句，没什么收获。"
        result["exp_gain"] = 6
        result["summary"] = "你和村人聊了几句"
    else:
        result["message"] = "你说话没什么人接。"
        result["exp_gain"] = 2
        result["summary"] = "你想找人聊天，但大家都忙"
    player_sys.add_exp(session, result["exp_gain"])
    return result
''', encoding="utf-8")
print("[write] server/systems/actions.py")

# ============================================================
# 2. main.py 加 /action 端点
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

if "/action" in t:
    print("[skip] main.py 已有 /action")
else:
    anchor = "@app.get(\"/event\")\ndef list_events(limit: int = 20) -> list[dict]:"
    addition = '''class ActionRequest(BaseModel):
    action: str


@app.post("/action")
async def action_endpoint(req: ActionRequest) -> dict:
    """执行一个玩家行动，同时推进世界 1 tick。"""
    from server.systems import actions as actions_sys
    import uuid as _uuid

    with get_session() as s:
        world = load_world(s)
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")

        # 1. 玩家行动
        action_result = await actions_sys.do_action(s, world, player, req.action)

        # 2. 推进世界 1 tick
        tick(s, world)
        await check_timeouts(s, world)

        # 3. NPC 闲谈
        npcs = load_npcs(s)
        rng = random.Random(world.seed * 1000003 + world.tick * 7)
        social = await maybe_social_dialogue(s, world, npcs, rng)

        # 4. 世界事件
        templates = director.load_templates()
        event = await run_event_cycle(s, world, templates, force=False)

        # 5. 记录玩家行动到 event 表
        try:
            from server.models.schemas import Event as EventModel
            evt_id = "evt_act_%s" % _uuid.uuid4().hex[:8]
            evt = EventModel(
                id=evt_id,
                template_id=req.action,
                participants=["player"],
                location_id=action_result.get("target_id") or player.location_id,
                state="resolved",
                payload={
                    "summary": action_result.get("summary", ""),
                    "narrative": action_result.get("flavor", ""),
                    "outcome": action_result.get("message", ""),
                    "check": action_result.get("check") or {},
                    "exp_gain": int(action_result.get("exp_gain", 0)),
                    "interactive": False,
                    "as_message": True,
                    "is_player_action": True,
                },
                created_at=world.tick,
                resolved_at=world.tick,
            )
            save_event(s, evt)
        except Exception as e:
            print("[action] 事件记录失败：%s" % e)

        # 6. 物品入库
        item_data = action_result.get("found_item")
        if item_data is not None:
            from server.models.db import ItemRow
            row = ItemRow(
                id=item_data["id"], reward_id="", event_id="",
                name=item_data.get("name", ""),
                kind=item_data.get("kind", ""),
                affixes_json=dumps(item_data.get("affixes", [])),
                story=item_data.get("story", ""),
                value=float(item_data.get("value", 0.0)),
                owner_id="player", consumed=False,
            )
            s.add(row)
            s.commit()

        save_world(s, world)

        p2 = player_sys.load_player(s)
        action_result["player"] = p2.model_dump() if p2 else {}
        action_result["tick"] = world.tick
        action_result["day"] = world.day
        action_result["hour"] = world.hour
        action_result["world_event"] = {
            "id": event.id,
            "summary": event.payload.get("summary"),
            "template_label": i18n.template_label(event.template_id),
            "awaiting_player": event.state == "awaiting_player",
        } if event else None
        action_result["social"] = social

        return action_result


@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''

    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] main.py 加 /action")
    else:
        print("[fail] main.py 锚点未找到")

# ============================================================
# 3. i18n 补行动名
# ============================================================
p = Path("server/i18n.py")
t = p.read_text(encoding="utf-8")
if '"gather"' not in t:
    anchor = '    "explore": "外出探索",\n'
    if anchor in t:
        t = t.replace(anchor, anchor
            + '    "gather": "采集",\n'
            + '    "hunt": "打猎",\n'
            + '    "train": "修炼",\n'
            + '    "socialize": "社交",\n', 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] i18n 加行动名")
    else:
        print("[skip] i18n explore 锚点未找到")
else:
    print("[skip] i18n 已有行动名")

print()
print("后端完成。重启 uvicorn。")