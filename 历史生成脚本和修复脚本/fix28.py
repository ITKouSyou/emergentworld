# 把 SQLite 连接改成 NullPool，避免连接池耗尽
from pathlib import Path

p = Path("server/db/session.py")
t = p.read_text(encoding="utf-8")

old = 'engine = create_engine(f"sqlite:///{settings.db_path}", echo=False)'

new = '''from sqlalchemy.pool import NullPool

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    echo=False,
    poolclass=NullPool,
    connect_args={
        "timeout": 30,
        "check_same_thread": False,
    },
)'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] session.py 改用 NullPool")
else:
    print("[skip] 已改过或锚点未匹配")

# 顺手检查 main.py 里是不是也创建了一个 engine
p2 = Path("server/main.py")
t2 = p2.read_text(encoding="utf-8")
if "create_engine(" in t2:
    print("[warn] main.py 里也有 create_engine —— 需要改成从 session.py 导入")
    for i, line in enumerate(t2.split("\n")):
        if "create_engine" in line:
            print("  行 %d: %s" % (i+1, line))
else:
    print("[ok] main.py 没有独立 engine")