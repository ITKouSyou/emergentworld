# 派系系统：长老会 / 商帮 / 农会 / 中立
from __future__ import annotations

from sqlmodel import Session

from server.models.db import NPCRow, PlayerRow, dumps, loads


FACTIONS = {
    "elder":    {"label": "长老会", "desc": "守旧，重视传统与祖训"},
    "merchant": {"label": "商帮",   "desc": "新兴，重视交易与财富"},
    "farmer":   {"label": "农会",   "desc": "平民，重视土地与收成"},
    "neutral":  {"label": "中立",   "desc": "不结盟，独来独往"},
}

# 派系对立：帮一方会得罪另一方
OPPOSED = {
    "elder": "merchant",
    "merchant": "elder",
}


def infer_faction(goals: list[str], age: int, gender: str = "unknown") -> str:
    """根据 goals 关键词推断派系。关键词匹配失败时按年龄/性别兜底。"""
    if age < 16:
        return "neutral"

    text = " ".join(goals).lower()

    # 长老会：传统 / 手艺 / 祖上 / 功名
    elder_kw = [
        "祖传", "祖上", "手艺", "收徒弟", "守住", "光宗耀祖",
        "考中", "考功名", "秀才", "传统", "重振家门", "家门",
        "功名", "读书", "考一个", "打虎", "证明",
    ]
    # 商帮：生意 / 钱 / 铺子 / 商
    merchant_kw = [
        "钱", "生意", "铺", "商", "卖", "赚", "攒够钱",
        "攒钱", "赎回", "还清", "买卖", "织坊", "酒铺",
        "翻修", "典当", "盘缠", "攒", "赚", "开一",
        "开间", "开间自己的",
    ]
    # 农会：地 / 收成 / 种 / 家
    farmer_kw = [
        "种地", "收成", "田", "地", "庄稼", "公婆",
        "家人", "家人过", "照看", "娘", "女儿", "嫁妆",
        "绣", "织", "婚", "娶", "妻", "夫", "家",
        "团圆", "痊愈", "病", "医", "药", "好日子",
        "照看村里", "保护",
    ]

    score_elder = sum(1 for kw in elder_kw if kw in text)
    score_merchant = sum(1 for kw in merchant_kw if kw in text)
    score_farmer = sum(1 for kw in farmer_kw if kw in text)

    best = max(score_elder, score_merchant, score_farmer)
    if best > 0:
        if score_elder == best:
            return "elder"
        if score_merchant == best:
            return "merchant"
        return "farmer"

    # 关键词都没匹配 → 兜底分配（按年龄/性别/名字）
    import random
    seed_val = (age * 31) + (len(text) * 7) + (hash(text[:4]) & 0xFF)
    rng = random.Random(seed_val)
    if age >= 50:
        return "elder"
    if age < 25:
        return rng.choice(["merchant", "farmer", "merchant"])
    if gender == "female":
        return rng.choice(["farmer", "elder", "farmer"])
    return rng.choice(["merchant", "farmer", "elder"])


def assign_all_factions(session: Session) -> dict:
    """给所有 NPC 分配派系。返回统计。"""
    rows = session.exec(__import__("sqlmodel", fromlist=["select"]).select(NPCRow)).all()
    stats = {"elder": 0, "merchant": 0, "farmer": 0, "neutral": 0}
    for r in rows:
        goals = loads(r.goals_json) or []
        f = infer_faction(goals, r.age, r.gender or "unknown")
        r.faction = f
        session.add(r)
        stats[f] = stats.get(f, 0) + 1
    session.commit()
    return stats


def get_player_faction_rep(session: Session, faction: str) -> int:
    row = session.get(PlayerRow, "player")
    if row is None:
        return 0
    factions = loads(row.factions_json) or {}
    return int(factions.get(faction, 0))


def adjust_player_faction_rep(session: Session, faction: str, delta: int) -> None:
    """调整玩家对某派系的声望（-100 到 +100）。"""
    if faction not in FACTIONS or faction == "neutral":
        return
    row = session.get(PlayerRow, "player")
    if row is None:
        return
    factions = loads(row.factions_json) or {}
    cur = int(factions.get(faction, 0))
    factions[faction] = max(-100, min(100, cur + delta))
    row.factions_json = dumps(factions)
    session.add(row)
    session.commit()


def get_player_faction_dict(session: Session) -> dict[str, int]:
    row = session.get(PlayerRow, "player")
    if row is None:
        return {}
    return loads(row.factions_json) or {}


def apply_event_choice(
    session: Session,
    template_id: str,
    choice_id: str,
    participants: list[str],
) -> None:
    """根据事件 + 选择，调整玩家对参与派系的声望。

    规则：
      - help：参与者所属派系 +2
      - oppose：参与者所属派系 -3，对立派 +1
      - observe：+1（中立视角）
    """
    if not participants:
        return

    npc_rows = session.exec(__import__("sqlmodel", fromlist=["select"]).select(NPCRow)).all()
    by_id = {r.id: r for r in npc_rows}

    # 统计参与者所属派系
    counts: dict[str, int] = {}
    for pid in participants:
        r = by_id.get(pid)
        if r is None:
            continue
        f = r.faction or "neutral"
        if f == "neutral":
            continue
        counts[f] = counts.get(f, 0) + 1

    if not counts:
        return

    if choice_id == "help":
        for f, c in counts.items():
            adjust_player_faction_rep(session, f, 2 * c)
    elif choice_id == "oppose":
        for f, c in counts.items():
            adjust_player_faction_rep(session, f, -3 * c)
            opp = OPPOSED.get(f)
            if opp:
                adjust_player_faction_rep(session, opp, 1 * c)
    elif choice_id == "observe":
        for f, c in counts.items():
            adjust_player_faction_rep(session, f, 1)


def faction_attitude_hint(rep: int) -> str:
    """把声望转成态度提示。"""
    if rep >= 50:
        return "热情"
    if rep >= 20:
        return "友好"
    if rep >= 5:
        return "温和"
    if rep <= -50:
        return "敌视"
    if rep <= -20:
        return "冷淡"
    if rep <= -5:
        return "警惕"
    return "中立"


def player_rep_summary(session: Session) -> list[dict]:
    """给前端显示用。"""
    rep = get_player_faction_dict(session)
    result = []
    for key, meta in FACTIONS.items():
        if key == "neutral":
            continue
        val = int(rep.get(key, 0))
        result.append({
            "key": key,
            "label": meta["label"],
            "desc": meta["desc"],
            "value": val,
            "attitude": faction_attitude_hint(val),
        })
    return result


def market_discount(session: Session) -> float:
    """根据商帮声望，返回市场折扣倍率。"""
    rep = get_player_faction_rep(session, "merchant")
    if rep >= 50:
        return 0.75
    if rep >= 20:
        return 0.85
    if rep >= 5:
        return 0.95
    if rep <= -20:
        return 1.15
    if rep <= -50:
        return 1.30
    return 1.0
