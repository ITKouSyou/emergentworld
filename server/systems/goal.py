# 目标系统：每日目标 + 长期里程碑
from __future__ import annotations

import random
from typing import Optional

from sqlmodel import Session, select

from server.models.db import GoalRow
from server.models.schemas import Player, World
from server.systems import player as player_sys

# 每日目标池：(key, label, 目标量, exp奖励, 钱奖励)
DAILY_POOL = [
    ("earn_money_today", "今天赚到 {n} 钱", 5, 15, 3),
    ("hunt_today", "猎得 {n} 只猎物", 1, 20, 5),
    ("gather_today", "采集 {n} 次", 1, 10, 2),
    ("train_today", "修炼 {n} 次", 1, 15, 2),
    ("socialize_today", "社交 {n} 次", 1, 12, 3),
    ("explore_today", "探索 {n} 次", 1, 15, 4),
    ("event_today", "参与 {n} 个事件", 1, 20, 5),
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
        from server.models.db import WorldRow
        from server.map_layout import LOCATION_LAYOUT
        import json
        row = session.get(WorldRow, "default")
        if row is None:
            return 0
        discovered = json.loads(row.location_ids_json or "[]")
        count = 0
        for loc in discovered:
            if loc in LOCATION_LAYOUT and LOCATION_LAYOUT[loc].get("hidden", False):
                count += 1
        return count
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

    # 直接读数据库里的 PlayerRow，改它
    from server.models.db import PlayerRow
    pr = session.get(PlayerRow, "player")
    if pr is None:
        return {"ok": False, "error": "player row not found"}

    row.claimed = True
    session.add(row)

    exp_added = 0
    money_added = 0

    if row.exp_reward > 0:
        pr.exp = (pr.exp or 0) + row.exp_reward
        exp_added = row.exp_reward
        # 升级
        while pr.exp >= pr.exp_next:
            pr.exp -= pr.exp_next
            pr.level += 1
            pr.unspent_points = (pr.unspent_points or 0) + 2
            pr.exp_next = player_sys.exp_for_level(pr.level)
            pr.max_hp = (pr.max_hp or 100) + 10
            pr.hp = pr.max_hp

    if row.money_reward > 0:
        pr.money = (pr.money or 0) + row.money_reward
        money_added = row.money_reward

    session.add(pr)
    session.commit()
    session.refresh(pr)

    print("[claim] goal=%s exp+%d money+%d -> pr.money=%d lv=%d" % (
        goal_id, exp_added, money_added, pr.money, pr.level))

    # 同步回传入的 Player（让调用方看到最新值）
    player.exp = pr.exp
    player.level = pr.level
    player.money = pr.money
    player.max_hp = pr.max_hp
    player.hp = pr.hp
    player.unspent_points = pr.unspent_points
    player.exp_next = pr.exp_next

    # 写 Reward
    try:
        from server.models.db import RewardRow, dumps
        import uuid as _uuid
        rr = RewardRow(
            id="rwd_goal_%s" % _uuid.uuid4().hex[:8],
            event_id="",
            kind="reputation" if money_added > 0 else "skill",
            value=float(money_added or exp_added),
            description="完成目标：%s（经验 +%d，铜钱 +%d）" % (
                row.label, exp_added, money_added),
            payload_json=dumps({"goal_id": goal_id, "source": "goal"}),
        )
        session.add(rr)
        session.commit()
    except Exception as e:
        print("[goal] reward 写入失败：%s" % e)

    return {
        "ok": True,
        "label": row.label,
        "exp_reward": exp_added,
        "money_reward": money_added,
        "player_money": pr.money,
        "player_level": pr.level,
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
