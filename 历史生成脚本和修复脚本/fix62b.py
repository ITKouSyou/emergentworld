# 顶层 import uuid as _uuid
from pathlib import Path

p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

# 找第一个 from __future__ 或 import 区
if "import uuid as _uuid" in t.split("\n@app")[0]:
    print("[skip] 顶层已 import uuid")
else:
    # 加在 import asyncio 后面（或第一个 import 后）
    if "import asyncio\n" in t:
        t = t.replace("import asyncio\n", "import asyncio\nimport uuid as _uuid\n", 1)
    else:
        t = t.replace(
            "from __future__ import annotations\n",
            "from __future__ import annotations\n\nimport uuid as _uuid\n",
            1,
        )
    p.write_text(t, encoding="utf-8")
    print("[fix] 顶层 import uuid as _uuid")