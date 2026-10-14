# 目标系统
from pathlib import Path

# ============================================================
# 1. db.py 加 GoalRow
# ============================================================
p = Path("server/models/db.py")
t = p.read_text(encoding="utf-8")

if "class GoalRow" not in t:
    anchor = "class EvaluationRow(SQLModel, table=True):"
    addition = '''class GoalRow(SQLModel, table=True):
    __tablename__ = "goal"
    id: str = Field(primary_key=True)
    kind: str = "daily"           # daily / milestone
    key: str = ""                 # 唯一键
    label: str = ""
    target: int = 1
    progress: int = 0
    done: bool = False
    claimed: bool = False
    exp_reward: int = 0
    money_reward: int = 0
    created_day: int = 0
    created_tick: int = 0


class EvaluationRow(SQLModel, table=True):'''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] db.py 加 GoalRow")
    else:
        print("[fail] db.py 锚点未找到")
else:
    print("[skip] db.py 已有 GoalRow")

# ============================================================
# 2. goal.py
# ============================================================
Path("server/systems/goal.py").write_text('''# 目标系统：每日目标 + 长期里程碑
from __future__ import annotations

import random
from typing import Optional

from sqlmodel import Session, select

from server.models.db import GoalRow
from server.models.schemas import Player, World
from server.systems import player as player_sys

# 每日目标池：(key, label, 目标量, exp奖励, 钱奖励)
DAILY_POOL = [
    ("earn_money_today", "今天赚到 {n} 钱", 5, 15, 0),
    ("hunt_today", "猎得 {n} 只猎物", 1, 20, 0),
    ("gather_today", "采集 {n} 次", 1, 10, 0),
    ("train_today", "修炼 {n} 次", 1, 15, 0),
    ("socialize_today", "社交 {n} 次", 1, 12, 0),
    ("explore_today", "探索 {n} 次", 1, 15, 0),
    ("event_today", "参与 {n} 个事件", 1, 20, 0),
]

# 长期里程碑池
MILESTONE_POOL = [
    ("total_money", "累计赚到 {n} 钱", 100, 100, 20),
    ("total_locations", "发现 {n} 个新地点", 3, 80, 15),
    ("total_items", "收集 {n} 件物品", 10, 60, 10),
    ("total_level", "达到 {n} 级", 3, 150, 30),
]


def _gen_goal_row(key: str, label: str, target: int, exp_r: int, money_r: int,
                  kind: str, day: int, tick: int) -> GoalRow:
    import uuid
    return GoalRow(
        id="goal_%s" % uuid.uuid4().hex[:8],
        kind=kind,
        key=key,
        label=label.replace("{n}", str(target)),
        target=target,
        progress=0,
        done=False,
        claimed=False,
        exp_reward=exp_r,
        money_reward=money_r,
        created_day=day,
        created_tick=tick,
    )


def get_daily_goals(session: Session) -> list[GoalRow]:
    rows = session.exec(
        select(GoalRow).where(GoalRow.kind == "daily")
    ).all()
    return list(rows)


def get_milestones(session: Session) -> list[GoalRow]:
    rows = session.exec(
        select(GoalRow).where(GoalRow.kind == "milestone")
    ).all()
    return list(rows)


def ensure_daily_goals(session: Session, world: World, rng: random.Random) -> None:
    """如果今天还没有目标，生成一批。跨天刷新。"""
    rows = get_daily_goals(session)
    # 判断是否过期：所有 daily 的 created_day 都不等于 world.day
    if rows and all(r.created_day == world.day for r in rows):
        return
    # 删除旧的
    for r in rows:
        session.delete(r)
    session.commit()

    # 生成 3 个
    pool = list(DAILY_POOL)
    rng.shuffle(pool)
    for key, label, target, exp_r, money_r in pool[:3]:
        row = _gen_goal_row(key, label, target, exp_r, money_r, "daily", world.day, world.tick)
        session.add(row)
    session.commit()


def ensure_milestones(session: Session, world: World) -> None:
    rows = get_milestones(session)
    if rows:
        return
    for key, label, target, exp_r, money_r in MILESTONE_POOL:
        row = _gen_goal_row(key, label, target, exp_r, money_r, "milestone", world.day, world.tick)
        session.add(row)
    session.commit()


def _key_matches(key: str, action: str, delta: int) -> bool:
    """判断某个 key 是否因这次行动而变化。"""
    if key == "earn_money_today" and action == "earn_money":
        return True
    if key == "hunt_today" and action == "hunt_success":
        return True
    if key == "gather_today" and action == "gather":
        return True
    if key == "train_today" and action == "train":
        return True
    if key == "socialize_today" and action == "socialize":
        return True
    if key == "explore_today" and action == "explore":
        return True
    if key == "event_today" and action == "event_resolved":
        return True
    return False


def _milestone_matches(session: Session, key: str, player: Player) -> int:
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
    return 0


def record_action(
    session: Session,
    world: World,
    player: Player,
    action: str,
    delta: int = 1,
) -> list[dict]:
    """记录一次行动，更新目标进度。返回刚刚完成的目标列表。"""
    just_completed: list[dict] = []

    # 每日目标
    for row in get_daily_goals(session):
        if row.done:
            continue
        if _key_matches(row.key, action, delta):
            row.progress = min(row.target, row.progress + delta)
            if row.progress >= row.target:
                row.done = True
            session.add(row)
    session.commit()

    # 里程碑
    for row in get_milestones(session):
        if row.done:
            continue
        cur = _milestone_matches(session, row.key, player)
        if cur >= row.target:
            row.progress = row.target
            row.done = True
        else:
            row.progress = cur
        session.add(row)
    session.commit()

    # 返回刚刚变为 done 但还没 claimed 的
    for row in get_daily_goals(session) + get_milestones(session):
        if row.done and not row.claimed:
            just_completed.append({
                "id": row.id,
                "label": row.label,
                "kind": row.kind,
                "exp_reward": row.exp_reward,
                "money_reward": row.money_reward,
            })

    return just_completed


def claim_goal(session: Session, world: World, player: Player, goal_id: str) -> dict:
    row = session.get(GoalRow, goal_id)
    if row is None:
        return {"ok": False, "error": "goal not found"}
    if not row.done:
        return {"ok": False, "error": "goal not done"}
    if row.claimed:
        return {"ok": False, "error": "already claimed"}

    row.claimed = True
    session.add(row)
    session.commit()

    if row.exp_reward > 0:
        player_sys.add_exp(session, row.exp_reward)
    if row.money_reward > 0:
        player = player_sys.load_player(session)
        if player is not None:
            player.money += row.money_reward
            player_sys.save_player(session, player)

    return {
        "ok": True,
        "label": row.label,
        "exp_reward": row.exp_reward,
        "money_reward": row.money_reward,
    }


def list_all(session: Session) -> dict:
    daily = get_daily_goals(session)
    milestones = get_milestones(session)
    return {
        "daily": [
            {
                "id": r.id, "label": r.label,
                "progress": r.progress, "target": r.target,
                "done": r.done, "claimed": r.claimed,
                "exp_reward": r.exp_reward, "money_reward": r.money_reward,
            }
            for r in daily
        ],
        "milestones": [
            {
                "id": r.id, "label": r.label,
                "progress": r.progress, "target": r.target,
                "done": r.done, "claimed": r.claimed,
                "exp_reward": r.exp_reward, "money_reward": r.money_reward,
            }
            for r in milestones
        ],
    }
''', encoding="utf-8")
print("[write] server/systems/goal.py")

# ============================================================
# 3. main.py 加目标端点 + 在 /action 里记录
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

if "/goal" in t:
    print("[skip] main.py 已有 /goal")
else:
    anchor = '''@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''
    addition = '''# ---------- Goals ----------

@app.get("/goal")
def goal_list() -> dict:
    with get_session() as s:
        world = load_world(s)
        from server.systems import goal as goal_sys
        import random as _r
        rng = _r.Random(world.seed + world.day)
        goal_sys.ensure_daily_goals(s, world, rng)
        goal_sys.ensure_milestones(s, world)
        return goal_sys.list_all(s)


class ClaimRequest(BaseModel):
    goal_id: str


@app.post("/goal/claim")
def goal_claim(req: ClaimRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")
        from server.systems import goal as goal_sys
        result = goal_sys.claim_goal(s, world, player, req.goal_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "claim failed"))
        p2 = player_sys.load_player(s)
        result["player"] = _player_to_response(s, p2) if p2 else {}
        return result


@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] main.py 加 /goal")

# ============================================================
# 4. /action 里记录行动
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

old = '''        # 6. 物品入库
        item_data = action_result.get("found_item")'''
new = '''        # 5.5 目标记录
        try:
            from server.systems import goal as goal_sys
            goal_sys.ensure_daily_goals(s, world, random.Random(world.seed + world.day))
            goal_sys.ensure_milestones(s, world)

            # 根据行动和结果映射
            action_name = req.action
            found_item = action_result.get("found_item") is not None
            record_action = None
            if action_name == "hunt" and found_item:
                record_action = "hunt_success"
            elif action_name == "gather":
                record_action = "gather"
            elif action_name == "train":
                record_action = "train"
            elif action_name == "socialize":
                record_action = "socialize"
            elif action_name == "explore" and action_result.get("found_location"):
                record_action = "explore"

            if record_action:
                goal_sys.record_action(s, world, player, record_action, 1)
        except Exception as e:
            import traceback
            print("[action] 目标记录失败：%s" % e)
            traceback.print_exc()

        # 6. 物品入库
        item_data = action_result.get("found_item")'''
if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] /action 记录目标进度")

# ============================================================
# 5. /trade/sell 里记录赚钱
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

old_sell = '''        result = market_sys.sell_item(s, world, player, req.item_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "sell failed"))
        return result'''
new_sell = '''        result = market_sys.sell_item(s, world, player, req.item_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "sell failed"))

        # 记录目标
        try:
            from server.systems import goal as goal_sys
            import random as _r
            goal_sys.ensure_daily_goals(s, world, _r.Random(world.seed + world.day))
            goal_sys.ensure_milestones(s, world)
            p2 = player_sys.load_player(s)
            if p2 is not None:
                goal_sys.record_action(s, world, p2, "earn_money",
                                       int(result.get("price", 0)))
        except Exception as e:
            print("[sell] 目标记录失败：%s" % e)

        return result'''
if old_sell in t:
    t = t.replace(old_sell, new_sell, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] /trade/sell 记录赚钱")

print()
print("后端完成。下一步 fix24b.py（前端）")