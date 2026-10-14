# 初始化世界：生成 NPC、构建家庭、加载模板
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
from server.systems.faction import assign_all_factions

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
        # 分配派系
        stats = assign_all_factions(session)
        print("assigned factions: %r" % stats)

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
