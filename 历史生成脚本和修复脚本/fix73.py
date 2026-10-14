# 1. 改进 infer_faction：加更多关键词 + 无匹配时兜底分配
# 2. 清 Godot 缓存
import shutil
from pathlib import Path

# ============================================================
# 1. 重写 infer_faction
# ============================================================
p = Path("server/systems/faction.py")
t = p.read_text(encoding="utf-8")

old = '''def infer_faction(goals: list[str], age: int) -> str:
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
    return "farmer"'''

new = '''def infer_faction(goals: list[str], age: int, gender: str = "unknown") -> str:
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
    return rng.choice(["merchant", "farmer", "elder"])'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] infer_faction 改进")
else:
    print("[skip] faction.py 已改过或锚点未匹配")

# ============================================================
# 2. assign_all_factions 加 gender 参数
# ============================================================
p = Path("server/systems/faction.py")
t = p.read_text(encoding="utf-8")

old2 = '''    for r in rows:
        goals = loads(r.goals_json) or []
        f = infer_faction(goals, r.age)
        r.faction = f'''
new2 = '''    for r in rows:
        goals = loads(r.goals_json) or []
        f = infer_faction(goals, r.age, r.gender or "unknown")
        r.faction = f'''

if old2 in t:
    t = t.replace(old2, new2, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] assign_all_factions 传 gender")

# ============================================================
# 3. 清 Godot 缓存
# ============================================================
godot_dir = Path("client/.godot")
if godot_dir.exists():
    shutil.rmtree(godot_dir)
    print("[fix] 删除 client/.godot/（强制 Godot 重新编译脚本）")
else:
    print("[skip] .godot 不存在")

# ============================================================
# 4. 重新分配派系（不清库，原地更新）
# ============================================================
print()
print("========= 运行以下命令 =========")
print("1. 重新分配派系：")
print('   python -c "from sqlmodel import Session, create_engine; from server.config import settings; from server.systems.faction import assign_all_factions; e=create_engine(f\'sqlite:///{settings.db_path}\'); s=Session(e); print(assign_all_factions(s))"')
print()
print("2. 重启后端：")
print("   uvicorn server.main:app")
print()
print("3. Godot 完全关闭重开（编辑器也要关，别只关运行窗口）")