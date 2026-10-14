"""初始化世界：生成 NPC、加载模板、写入数据库。"""

from __future__ import annotations

import argparse
import asyncio
import random

from sqlmodel import Session, SQLModel, create_engine

from server.config import settings
from server.core.director import load_templates
from server.core.world import create_world, save_npc, save_world
from server.generators.npc import generate_npc
from server.systems.family import build_families

MALE_NAMES = [
    "张铁柱", "李大山", "王二狗", "赵石", "陈望",
    "刘长河", "孙远", "周慎", "吴越", "郑屠",
    "冯舟", "褚守", "卫风", "蒋平", "沈墨",
]
CHILD_NAMES = [
    "小石头", "铁蛋", "栓子", "狗剩", "阿牛",
    "丫丫", "招娣", "小翠", "阿香", "杏儿",
]

FEMALE_NAMES = [
    "李秀兰", "王桂花", "赵小梅", "陈阿娇", "刘翠",
    "孙玉", "周盼", "吴侬", "郑蓉", "冯素",
    "褚莲", "卫婵", "蒋薇", "沈烟", "秦娥",
]


def pick_name_pool(n: int, rng: random.Random) -> list[tuple[str, str]]:
    males = [("male", name) for name in MALE_NAMES]
    females = [("female", name) for name in FEMALE_NAMES]
    pool = males + females
    rng.shuffle(pool)
    return [(name, gender) for (gender, name) in pool[:n]]


async def seed(n: int, seed_value: int) -> None:
    rng = random.Random(seed_value)
    engine = create_engine(f"sqlite:///{settings.db_path}")
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        world = create_world("default", seed=seed_value)
        save_world(session, world)
        picks = pick_name_pool(n, rng)
        npcs = []

        # 成年人（约 70%）
        n_adults = max(4, int(n * 0.7))
        adult_picks = picks[:n_adults]
        # 儿童（约 30%）
        n_children = n - n_adults

        for name, gender in adult_picks:
            npc = await generate_npc(name, context="一个偏远村庄", gender=gender)
            save_npc(session, npc)
            npcs.append(npc)
            print("created adult %s %s (%s, age=%d)" % (
                npc.id, npc.name, npc.gender, npc.age))

        # 儿童：从 CHILD_NAMES 取
        child_pool = list(CHILD_NAMES)
        rng.shuffle(child_pool)
        for i in range(min(n_children, len(child_pool))):
            cname = child_pool[i]
            cgender = "male" if i % 2 == 0 else "female"
            npc = await generate_npc(cname, context="村里的孩子", gender=cgender)
            # 强制年龄段
            npc.age = rng.randint(7, 15)
            save_npc(session, npc)
            npcs.append(npc)
            print("created child %s %s (age=%d)" % (npc.id, npc.name, npc.age))

        build_families(session, npcs, rng)
        print("built families")
        for npc in npcs:
            fam = npc.family
            bits = []
            if fam.spouse: bits.append("配偶")
            if fam.children: bits.append("%d子女" % len(fam.children))
            if fam.parents: bits.append("父母")
            if fam.siblings: bits.append("%d兄弟姐妹" % len(fam.siblings))
            print("  %s: %s" % (npc.name, "、".join(bits) or "独身"))

    templates = load_templates()
    print("loaded %d event templates" % len(templates))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--npc", type=int, default=8)
    parser.add_argument("--seed", type=int, default=settings.seed)
    args = parser.parse_args()
    asyncio.run(seed(args.npc, args.seed))


if __name__ == "__main__":
    main()
