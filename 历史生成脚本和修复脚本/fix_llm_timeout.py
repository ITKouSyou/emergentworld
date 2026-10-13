# 给 run_event_cycle 和 social dialogue 加 asyncio.wait_for 超时
from pathlib import Path

# 1. LLMClient._call_raw 加超时（在 tenacity 之外，用 asyncio.wait_for 保险）
p = Path("server/generators/base.py")
t = p.read_text(encoding="utf-8")

if "asyncio.wait_for" not in t:
    t = t.replace(
        "import hashlib\nimport json\n",
        "import asyncio\nimport hashlib\nimport json\n",
        1,
    )

    # 包裹 self.client.chat.completions.create
    old = '''        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a game content generator. "
                        "Always answer with valid JSON. "
                        "No prose, no markdown fences."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.9,
        )'''
    new = '''        resp = await asyncio.wait_for(
            self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a game content generator. "
                            "Always answer with valid JSON. "
                            "No prose, no markdown fences."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.9,
            ),
            timeout=40.0,
        )'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] base.py _call_raw 加 40s 超时")
    else:
        print("[fail] base.py 锚点未找到")

    # text 方法加超时
    p2 = Path("server/generators/base.py")
    t2 = p2.read_text(encoding="utf-8")
    old2 = '''        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
        )'''
    new2 = '''        resp = await asyncio.wait_for(
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
            ),
            timeout=40.0,
        )'''
    if old2 in t2:
        t2 = t2.replace(old2, new2, 1)
        p2.write_text(t2, encoding="utf-8")
        print("[fix] base.py text 方法加 40s 超时")
else:
    print("[skip] base.py 已有超时")