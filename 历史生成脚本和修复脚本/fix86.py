# 让 migrate_items.py 先跑 schema 迁移
from pathlib import Path

content = '''# 给已有物品补 category / use_effect / slot
from sqlmodel import Session, create_engine, select

from server.config import settings
from server.db.session import ensure_schema
from server.models.db import ItemRow
from server.systems import item_meta

import json


def main():
    # 关键：先跑 schema 升级（加列）
    ensure_schema()

    engine = create_engine(f"sqlite:///{settings.db_path}")
    with Session(engine) as s:
        rows = list(s.exec(select(ItemRow)).all())
        n = 0
        for r in rows:
            cat = getattr(r, "category", "") or ""
            if not cat or cat == "material":
                cat = item_meta.infer_category(r.kind)
                r.category = cat
            if cat == "consumable":
                eff = item_meta.infer_effect(r.kind)
                if eff:
                    r.use_effect_json = json.dumps(eff, ensure_ascii=False)
            if cat == "equipment":
                r.slot = item_meta.infer_slot(r.kind)
                if not r.max_durability:
                    r.max_durability = 100
                    r.durability = 100
            else:
                # 非装备不给耐久
                r.durability = 0
                r.max_durability = 0
            s.add(r)
            n += 1
        s.commit()
        print("migrated %d items" % n)


if __name__ == "__main__":
    main()
'''

p = Path("tools/migrate_items.py")
p.write_text(content, encoding="utf-8")
print("[fix] migrate_items.py 加 ensure_schema 调用")