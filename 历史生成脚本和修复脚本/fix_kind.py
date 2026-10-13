# 给 RelationshipRow 加 kind 字段，并让 relationship.py 用 getattr 兜底
from pathlib import Path

# 1. db.py：RelationshipRow 加 kind
p = Path("server/models/db.py")
t = p.read_text(encoding="utf-8")
old = (
    'class RelationshipRow(SQLModel, table=True):\n'
    '    __tablename__ = "relationship"\n'
    '    id: str = Field(primary_key=True)\n'
    '    from_npc: str = Field(index=True)\n'
    '    to_npc: str = Field(index=True)\n'
    '    trust: float = 0.0\n'
    '    affection: float = 0.0\n'
    '    fear: float = 0.0\n'
    '    debt: float = 0.0\n'
)
new = (
    'class RelationshipRow(SQLModel, table=True):\n'
    '    __tablename__ = "relationship"\n'
    '    id: str = Field(primary_key=True)\n'
    '    from_npc: str = Field(index=True)\n'
    '    to_npc: str = Field(index=True)\n'
    '    trust: float = 0.0\n'
    '    affection: float = 0.0\n'
    '    fear: float = 0.0\n'
    '    debt: float = 0.0\n'
    '    kind: str = ""\n'
)
if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] db.py RelationshipRow 加 kind")
else:
    print("[skip] db.py 已改过或锚点未匹配")

# 2. relationship.py：用 getattr 兜底
p = Path("server/systems/relationship.py")
t = p.read_text(encoding="utf-8")

# 全部 kind=row.kind 改成 getattr
n = t.count('kind=row.kind or ""')
if n > 0:
    t = t.replace('kind=row.kind or ""', 'kind=getattr(row, "kind", "") or ""')
    p.write_text(t, encoding="utf-8")
    print("[fix] relationship.py kind=row.kind 改成 getattr（%d 处）" % n)
else:
    print("[skip] relationship.py 已改过")

# 3. session.py：加 relationship.kind 迁移
p = Path("server/db/session.py")
t = p.read_text(encoding="utf-8")
if 'relationship' not in t or '"kind"' not in t:
    anchor = '        _add_col(conn, "world", "social_count_today",\n                 "social_count_today INTEGER NOT NULL DEFAULT 0")\n'
    if anchor in t:
        addition = anchor + '        _add_col(conn, "relationship", "kind", "kind TEXT NOT NULL DEFAULT \'\'")\n'
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] session.py 加 relationship.kind 迁移")
    else:
        print("[skip] session.py 迁移锚点未找到，可能不需要")
else:
    print("[skip] session.py 已含 relationship.kind")

print()
print("接下来：pytest -v")