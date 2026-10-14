# Part 69B：派系系统
from pathlib import Path

# ============================================================
# 1. faction.py 新文件
# ============================================================
Path("server/systems/faction.py").write_text('''# 派系系统：长老会 / 商帮 / 农会 / 中立
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


def infer_faction(goals: list[str], age: int) -> str:
    """根据 goals 关键词推断派系。"""
    if age < 16:
        return "neutral"

    text = " ".join(goals).lower()

    # 长老会：传统 / 手艺 / 祖上 / 守成
    elder_kw = ["祖传", "祖上", "手艺", "收徒弟", "守住", "光宗耀祖",
                "考中", "考功名", "秀才", "传统", "重振家门"]
    # 商帮：生意 / 钱 / 铺子 / 商
    merchant_kw = ["钱", "生意", "铺", "商", "卖", "赚", "攒够钱",
                   "攒钱", "赎回", "还清", "买卖", "织坊", "酒铺",
                   "翻修", "典当"]
    # 农会：地 / 收成 / 种 / 家
    farmer_kw = ["种地", "收成", "田", "地", "庄稼", "公婆",
                 "家人", "家人过", "照看", "娘", "女儿", "嫁妆"]

    score_elder = sum(1 for kw in elder_kw if kw in text)
    score_merchant = sum(1 for kw in merchant_kw if kw in text)
    score_farmer = sum(1 for kw in farmer_kw if kw in text)

    best = max(score_elder, score_merchant, score_farmer)
    if best == 0:
        return "neutral"
    if score_elder == best:
        return "elder"
    if score_merchant == best:
        return "merchant"
    return "farmer"


def assign_all_factions(session: Session) -> dict:
    """给所有 NPC 分配派系。返回统计。"""
    rows = session.exec(__import__("sqlmodel", fromlist=["select"]).select(NPCRow)).all()
    stats = {"elder": 0, "merchant": 0, "farmer": 0, "neutral": 0}
    for r in rows:
        goals = loads(r.goals_json) or []
        f = infer_faction(goals, r.age)
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
''', encoding="utf-8")
print("[write] server/systems/faction.py")

# ============================================================
# 2. event_flow.py：resolve 时调整声望
# ============================================================
p = Path("server/core/event_flow.py")
t = p.read_text(encoding="utf-8")

old = '''    # 写印象
    try:
        from server.systems import impression as impr_sys'''

new = '''    # 派系声望
    try:
        from server.systems import faction as faction_sys
        faction_sys.apply_event_choice(
            session, event.template_id, choice_id, event.participants,
        )
    except Exception as e:
        import traceback
        print("[event] 派系声望写入失败：%s" % e)
        traceback.print_exc()

    # 写印象
    try:
        from server.systems import impression as impr_sys'''

if old in t and "派系声望" not in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] event_flow resolve 调派系声望")
else:
    print("[skip] event_flow 已改过或锚点未匹配")

# ============================================================
# 3. dialogue.py：注入派系声望
# ============================================================
p = Path("server/generators/dialogue.py")
t = p.read_text(encoding="utf-8")

old2 = '''    # 玩家给这个 NPC 留下的印象
    try:
        from server.systems import impression as impr_sys
        impression_text = impr_sys.describe_for_prompt(session, npc.id, limit=4)
    except Exception:
        impression_text = "（你对他还没有特别的印象）"'''

new2 = '''    # 玩家给这个 NPC 留下的印象
    try:
        from server.systems import impression as impr_sys
        impression_text = impr_sys.describe_for_prompt(session, npc.id, limit=4)
    except Exception:
        impression_text = "（你对他还没有特别的印象）"

    # 派系态度
    try:
        from server.systems import faction as faction_sys
        if npc.faction and npc.faction != "neutral":
            rep = faction_sys.get_player_faction_rep(session, npc.faction)
            attitude = faction_sys.faction_attitude_hint(rep)
            faction_label = faction_sys.FACTIONS.get(npc.faction, {}).get("label", npc.faction)
            faction_text = "你对玩家所属派系态度：%s（%s，声望 %d）" % (
                attitude, faction_label, rep)
        else:
            faction_text = "（你不属于任何派系）"
    except Exception:
        faction_text = "（未知）"'''

if old2 in t and "派系态度" not in t:
    t = t.replace(old2, new2, 1)
    print("[fix] dialogue.py 加派系态度")

# 加 faction 参数到 prompt
t = p.read_text(encoding="utf-8")
old3 = '''        recent_events=recent_text,
        active_quests=active_quests_text,
        impression=impression_text,'''
new3 = '''        recent_events=recent_text,
        active_quests=active_quests_text,
        impression=impression_text,
        faction_attitude=faction_text,'''
if old3 in t and "faction_attitude" not in t.split("load_prompt")[1][:500]:
    t = t.replace(old3, new3, 1)
    print("[fix] dialogue.py 传 faction_attitude")

p.write_text(t, encoding="utf-8")

# ============================================================
# 4. dialogue.md 加占位符
# ============================================================
p = Path("server/prompts/dialogue.md")
t = p.read_text(encoding="utf-8")

if "{faction_attitude}" not in t:
    old4 = '''你对玩家的印象（基于过去发生的事）：
  {impression}'''
    new4 = '''你对玩家的印象（基于过去发生的事）：
  {impression}

你的派系立场：
  {faction_attitude}'''
    if old4 in t:
        t = t.replace(old4, new4, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] dialogue.md 加 faction_attitude")

# ============================================================
# 5. market.py：应用派系折扣
# ============================================================
p = Path("server/systems/market.py")
t = p.read_text(encoding="utf-8")

old5 = '''def get_market_inventory(world: World, rng: random.Random) -> list[dict]:'''
new5 = '''def get_market_inventory(world: World, rng: random.Random, session=None) -> list[dict]:'''
if old5 in t and "session=None" not in t:
    t = t.replace(old5, new5, 1)
    print("[fix] market get_market_inventory 加 session 参数")

# 在价格计算处应用折扣
old6 = '''        price_f = base * BUY_MULT * season_mult * rng.uniform(0.85, 1.15)
        price = max(1, int(round(price_f)))'''
new6 = '''        price_f = base * BUY_MULT * season_mult * rng.uniform(0.85, 1.15)
        # 派系折扣
        discount = 1.0
        if session is not None:
            try:
                from server.systems import faction as faction_sys
                discount = faction_sys.market_discount(session)
            except Exception:
                pass
        price_f *= discount
        price = max(1, int(round(price_f)))'''
if old6 in t:
    t = t.replace(old6, new6, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] market 应用派系折扣")
else:
    print("[skip] market 价格锚点未找到")

# ============================================================
# 6. main.py：/market 传 session + /faction 端点
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

old7 = '''        goods = market_sys.get_market_inventory(world, rng)'''
new7 = '''        goods = market_sys.get_market_inventory(world, rng, session=s)'''
if old7 in t:
    t = t.replace(old7, new7, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] /market 传 session")

# /faction 端点
t = p.read_text(encoding="utf-8")
if "/faction" not in t:
    anchor = '''@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''
    addition = '''@app.get("/faction")
def faction_status() -> dict:
    with get_session() as s:
        from server.systems import faction as faction_sys
        return {
            "factions": faction_sys.player_rep_summary(s),
            "market_discount": faction_sys.market_discount(s),
        }


@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] main.py 加 /faction 端点")

# /npc/{id} 返回 faction
t = p.read_text(encoding="utf-8")
old8 = '''        result = _npc_to_display(npcs[npc_id], names)
        result["impressions"] = _impressions_for_npc(s, npc_id)
        return result'''
new8 = '''        result = _npc_to_display(npcs[npc_id], names)
        result["impressions"] = _impressions_for_npc(s, npc_id)
        # 派系
        try:
            from server.systems import faction as faction_sys
            npc = npcs[npc_id]
            if npc.faction and npc.faction != "neutral":
                meta = faction_sys.FACTIONS.get(npc.faction, {})
                result["faction"] = npc.faction
                result["faction_label"] = meta.get("label", npc.faction)
            else:
                result["faction"] = "neutral"
                result["faction_label"] = "中立"
        except Exception:
            pass
        return result'''
if old8 in t:
    t = t.replace(old8, new8, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] /npc/{id} 返回 faction")

print()
print("B 完成。下一步 fix69c.py（前端）")