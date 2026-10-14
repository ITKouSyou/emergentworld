# 经济系统：市场买卖
from pathlib import Path

# ============================================================
# 1. market.py
# ============================================================
Path("server/systems/market.py").write_text('''# 市场买卖
from __future__ import annotations

import random
import uuid

from sqlmodel import Session

from server.i18n import location_label
from server.models.db import ItemRow
from server.models.schemas import Player, World
from server.systems import inventory, player as player_sys


# 商店物品池：(name, kind, base_value, min_season_factor)
SHOP_POOL = [
    ("干粮", "食材", 0.15),
    ("粗布", "布料", 0.12),
    ("草药", "草药", 0.20),
    ("粗铁", "矿石", 0.25),
    ("米酒", "酒", 0.18),
    ("旧书", "书籍", 0.22),
    ("护身符", "信物", 0.35),
    ("药膏", "药材", 0.28),
    ("蜡烛", "杂物", 0.08),
    ("绳索", "工具", 0.16),
    ("皮囊", "工具", 0.30),
    ("盐巴", "食材", 0.10),
]

SEASON_PRICE_MULT = {
    "spring": 1.0,
    "summer": 0.9,
    "autumn": 1.2,
    "winter": 1.5,
}

# 卖出价倍率 / 买入价倍率
SELL_MULT = 10
BUY_MULT = 15


def get_market_inventory(world: World, rng: random.Random) -> list[dict]:
    """返回本次进市场可购买的物品（随机 4-6 件）。"""
    pool = list(SHOP_POOL)
    rng.shuffle(pool)
    n = rng.randint(4, 6)
    season_mult = SEASON_PRICE_MULT.get(world.season, 1.0)

    result: list[dict] = []
    for name, kind, base in pool[:n]:
        # 每件价格浮动 ±15%
        price_f = base * BUY_MULT * season_mult * rng.uniform(0.85, 1.15)
        price = max(1, int(round(price_f)))
        result.append({
            "id": "shop_%s" % uuid.uuid4().hex[:6],
            "name": name,
            "kind": kind,
            "price": price,
            "base_value": base,
        })
    return result


def sell_price(item_value: float, world: World) -> int:
    season_mult = SEASON_PRICE_MULT.get(world.season, 1.0)
    price_f = item_value * SELL_MULT * season_mult
    return max(1, int(round(price_f)))


def sell_item(session: Session, world: World, player: Player, item_id: str) -> dict:
    row = inventory.get_item_row(session, item_id)
    if row is None:
        return {"ok": False, "error": "item not found"}
    if row.consumed:
        return {"ok": False, "error": "item already consumed"}
    if row.owner_id != "player":
        return {"ok": False, "error": "not your item"}

    price = sell_price(row.value, world)
    player.money += price
    # 标记为已消耗（从库存移除）
    row.consumed = True
    session.add(row)
    player_sys.save_player(session, player)

    return {
        "ok": True,
        "item_id": item_id,
        "item_name": row.name,
        "price": price,
        "player_money": player.money,
    }


def buy_item(
    session: Session, world: World, player: Player,
    name: str, kind: str, price: int, base_value: float,
) -> dict:
    if player.money < price:
        return {"ok": False, "error": "not enough money"}

    player.money -= price
    player_sys.save_player(session, player)

    # 写入物品
    new_id = "itm_%s" % uuid.uuid4().hex[:8]
    row = ItemRow(
        id=new_id,
        reward_id="shop",
        event_id="",
        name=name,
        kind=kind,
        affixes_json="[]",
        story="从市场购得。",
        value=base_value,
        owner_id="player",
        consumed=False,
    )
    session.add(row)
    session.commit()

    return {
        "ok": True,
        "item_id": new_id,
        "item_name": name,
        "price": price,
        "player_money": player.money,
    }
''', encoding="utf-8")
print("[write] server/systems/market.py")

# ============================================================
# 2. main.py 加市场端点
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

if "/market" in t:
    print("[skip] main.py 已有 /market")
else:
    anchor = '''@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''

    addition = '''# ---------- Market ----------

@app.get("/market")
def market_view() -> dict:
    import random as _r
    with get_session() as s:
        world = load_world(s)
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")
        rng = _r.Random(world.seed * 77777 + world.tick * 3)
        from server.systems import market as market_sys
        goods = market_sys.get_market_inventory(world, rng)

        # 玩家可卖物品
        my_items = inventory.list_items_by_owner(s, "player")
        sell_list = []
        for r in my_items:
            price = market_sys.sell_price(r.value, world)
            sell_list.append({
                "id": r.id,
                "name": r.name,
                "kind": r.kind,
                "value": r.value,
                "sell_price": price,
            })

        return {
            "season": world.season,
            "season_label": i18n.season_label(world.season),
            "season_mult": market_sys.SEASON_PRICE_MULT.get(world.season, 1.0),
            "player_money": player.money,
            "goods": goods,
            "sell_list": sell_list,
        }


class SellRequest(BaseModel):
    item_id: str


@app.post("/trade/sell")
def trade_sell(req: SellRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")
        from server.systems import market as market_sys
        result = market_sys.sell_item(s, world, player, req.item_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "sell failed"))
        return result


class BuyRequest(BaseModel):
    name: str
    kind: str
    price: int
    base_value: float


@app.post("/trade/buy")
def trade_buy(req: BuyRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")
        from server.systems import market as market_sys
        result = market_sys.buy_item(
            s, world, player,
            name=req.name, kind=req.kind,
            price=req.price, base_value=req.base_value,
        )
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "buy failed"))
        return result


@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''

    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] main.py 加市场端点")
    else:
        print("[fail] main.py 锚点未找到")

print()
print("后端完成。下一步 fix23b.py（前端）")