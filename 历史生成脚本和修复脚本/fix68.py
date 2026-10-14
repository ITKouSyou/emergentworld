# 分性别名字池 + 强制性别匹配
from pathlib import Path

# ============================================================
# 1. 重写 seed_world.py
# ============================================================
content = '''# 初始化世界：生成 NPC、构建家庭、加载模板
from __future__ import annotations

import argparse
import asyncio
import random

from sqlmodel import Session, SQLModel, create_engine

from server.config import settings
from server.core.director import load_templates
from server.core.world import create_world, save_npc, save_world
from server.generators.npc import generate_npc, CHILD_GOALS
from server.systems.family import build_families
from server.systems.schedule import generate_schedule

# 男名 / 女名 / 儿童男名 / 儿童女名
MALE_NAMES = [
    "张铁柱", "李大山", "王二狗", "赵石", "陈望",
    "刘长河", "孙远", "周慎", "吴越", "郑屠",
    "冯舟", "褚守", "卫风", "蒋平", "沈墨",
]
FEMALE_NAMES = [
    "李秀兰", "王桂花", "赵小梅", "陈阿娇", "刘翠",
    "孙玉", "周盼", "吴侬", "郑蓉", "冯素",
    "褚莲", "卫婵", "蒋薇", "沈烟", "秦娥",
]
CHILD_MALE_NAMES = [
    "小石头", "铁蛋", "栓子", "狗剩", "阿牛",
    "黑娃", "棒槌", "小虎",
]
CHILD_FEMALE_NAMES = [
    "丫丫", "招娣", "小翠", "阿香", "杏儿",
    "小桃", "翠莲", "二妮",
]


def pick_adults(n: int, rng: random.Random) -> list[tuple[str, str]]:
    """返回 n 个成人 (name, gender)。保证性别尽量均衡。"""
    males = list(MALE_NAMES)
    females = list(FEMALE_NAMES)
    rng.shuffle(males)
    rng.shuffle(females)

    result = []
    # 交替性别，保证均衡
    for i in range(n):
        if i % 2 == 0 and males:
            result.append((males.pop(), "male"))
        elif females:
            result.append((females.pop(), "female"))
        elif males:
            result.append((males.pop(), "male"))
    rng.shuffle(result)
    return result


def pick_children(n: int, rng: random.Random) -> list[tuple[str, str]]:
    """返回 n 个儿童 (name, gender)。"""
    males = list(CHILD_MALE_NAMES)
    females = list(CHILD_FEMALE_NAMES)
    rng.shuffle(males)
    rng.shuffle(females)

    result = []
    for i in range(n):
        if i % 2 == 0 and males:
            result.append((males.pop(), "male"))
        elif females:
            result.append((females.pop(), "female"))
        elif males:
            result.append((males.pop(), "male"))
    rng.shuffle(result)
    return result


async def seed(n: int, seed_value: int) -> None:
    rng = random.Random(seed_value)
    engine = create_engine(f"sqlite:///{settings.db_path}")
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)

    # 约 70% 成人，30% 儿童
    n_adults = max(4, int(n * 0.7))
    n_children = n - n_adults

    with Session(engine) as session:
        world = create_world("default", seed=seed_value)
        save_world(session, world)

        npcs = []

        # 成人
        for name, gender in pick_adults(n_adults, rng):
            npc = await generate_npc(name, context="一个偏远村庄", gender=gender)
            # 成人年龄再随机一次
            npc.age = rng.randint(20, 55)
            save_npc(session, npc)
            npcs.append(npc)
            print("created adult %s %s (%s, age=%d) goals=%r" % (
                npc.id, npc.name, npc.gender, npc.age, npc.goals))

        # 儿童
        for name, gender in pick_children(n_children, rng):
            npc = await generate_npc(name, context="村里的孩子", gender=gender)
            # 强制 7-15 岁 + 童年版 goals
            npc.age = rng.randint(7, 15)
            npc.goals = list(rng.choice(CHILD_GOALS))
            save_npc(session, npc)
            npcs.append(npc)
            print("created child %s %s (%s, age=%d) goals=%r" % (
                npc.id, npc.name, npc.gender, npc.age, npc.goals))

        # 家庭
        build_families(session, npcs, rng)
        print("built families")

        # 日程
        for npc in npcs:
            npc.schedule = generate_schedule(npc, rng)
            save_npc(session, npc)
        print("assigned schedules")

        for npc in npcs:
            fam = npc.family
            bits = []
            if fam.spouse: bits.append("配偶")
            if fam.children: bits.append("%d子女" % len(fam.children))
            if fam.parents: bits.append("父母")
            if fam.siblings: bits.append("%d兄弟姐妹" % len(fam.siblings))
            print("  %s (%s %d岁): %s" % (
                npc.name, npc.gender, npc.age, "、".join(bits) or "独身"))

    templates = load_templates()
    print("loaded %d event templates" % len(templates))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--npc", type=int, default=14)
    parser.add_argument("--seed", type=int, default=settings.seed)
    args = parser.parse_args()
    asyncio.run(seed(args.npc, args.seed))


if __name__ == "__main__":
    main()
'''

p = Path("tools/seed_world.py")
p.write_text(content, encoding="utf-8")
print("[fix] seed_world.py 分性别名字池")

# ============================================================
# 2. npc.py：加名字性别推断（兜底）
# ============================================================
p2 = Path("server/generators/npc.py")
t2 = p2.read_text(encoding="utf-8")

if "_guess_gender" not in t2:
    anchor = "def gender_zh(gender: str) -> str:"
    addition = '''# 按名字推断性别的兜底（防止 LLM 或调用方传错）
FEMALE_NAME_HINTS = [
    "秀", "兰", "桂", "梅", "娇", "翠", "玉", "盼",
    "蓉", "莲", "婵", "薇", "烟", "娥", "丫", "娣",
    "香", "杏", "桃", "妮", "侬", "素",
]
MALE_NAME_HINTS = [
    "铁", "柱", "山", "狗", "望", "河", "远", "慎",
    "越", "屠", "舟", "守", "风", "平", "墨",
    "石", "蛋", "栓", "剩", "牛", "娃", "棒", "虎",
]


def _guess_gender(name: str) -> str:
    """按名字特征推断性别。返回 "male" / "female" / "unknown"。"""
    if not name:
        return "unknown"
    # 优先检查女性特征
    for ch in name:
        if ch in FEMALE_NAME_HINTS:
            return "female"
    for ch in name:
        if ch in MALE_NAME_HINTS:
            return "male"
    return "unknown"


def gender_zh(gender: str) -> str:'''
    if anchor in t2:
        t2 = t2.replace(anchor, addition, 1)
        print("[fix] npc.py 加 _guess_gender")

    # 在 generate_npc 里使用
    old = '''    npc.id = npc_id
    npc.name = npc.name or seed_name
    if gender != "unknown":
        npc.gender = gender'''
    new = '''    npc.id = npc_id
    npc.name = npc.name or seed_name

    # 名字推断性别 vs 传入性别，冲突时以名字为准
    name_gender = _guess_gender(npc.name)
    if name_gender != "unknown":
        if gender != "unknown" and name_gender != gender:
            print("[npc] %s 名字性别 %s 与传入 %s 冲突，用名字" % (
                npc.name, name_gender, gender))
        npc.gender = name_gender
    elif gender != "unknown":
        npc.gender = gender

    # 强制覆盖一次，避免 LLM 乱写
    if gender != "unknown":
        npc.gender = gender if name_gender == "unknown" else name_gender'''
    if old in t2:
        t2 = t2.replace(old, new, 1)
        print("[fix] npc.py generate_npc 名字性别优先")
    else:
        print("[skip] npc.py generate_npc 锚点未找到")

    p2.write_text(t2, encoding="utf-8")
else:
    print("[skip] npc.py 已有 _guess_gender")

print()
print("清库重 seed：")
print("  Remove-Item data\\world.db")
print("  python tools\\seed_world.py --npc 14")