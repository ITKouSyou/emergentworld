# 给 base.py 加 import asyncio
from pathlib import Path

p = Path("server/generators/base.py")
t = p.read_text(encoding="utf-8")

if "import asyncio" in t:
    print("[skip] 已有 import asyncio")
else:
    old = "import hashlib\nimport json\n"
    new = "import asyncio\nimport hashlib\nimport json\n"
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] base.py 加 import asyncio")
    else:
        # 备用锚点
        old2 = "from __future__ import annotations\n"
        if old2 in t:
            t = t.replace(old2, old2 + "\nimport asyncio\n", 1)
            p.write_text(t, encoding="utf-8")
            print("[fix] base.py 加 import asyncio（备用）")
        else:
            print("[fail] 找不到锚点，请手动在 base.py 顶部加 import asyncio")

# 顺便检查其它可能缺失的 import
t2 = p.read_text(encoding="utf-8")
if "wait_for" in t2 and "import asyncio" not in t2:
    print("[WARN] 还有 wait_for 但没 asyncio")
else:
    print("[ok]")