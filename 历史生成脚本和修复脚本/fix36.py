# 1. LLM 单次超时降到 25s，重试从 3 次降到 1 次
# 2. run_event_cycle 整体加 60s 超时保护
from pathlib import Path

# ============================================================
# 1. base.py：减少重试 + 缩短超时
# ============================================================
p = Path("server/generators/base.py")
t = p.read_text(encoding="utf-8")

# 重试次数
old_retry = '@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))'
new_retry = '@retry(stop=stop_after_attempt(1), wait=wait_exponential(min=1, max=3))'
if old_retry in t:
    t = t.replace(old_retry, new_retry, 1)
    print("[fix] 重试 3→1")

# 超时 40→25
old_to = 'timeout=40.0,'
new_to = 'timeout=25.0,'
n = t.count(old_to)
if n > 0:
    t = t.replace(old_to, new_to)
    print("[fix] LLM 超时 40→25s（%d 处）" % n)

p.write_text(t, encoding="utf-8")

# ============================================================
# 2. main.py：run_event_cycle 整体加 60s 超时
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

# 找到所有 run_event_cycle 调用处，包 asyncio.wait_for
import re

# 先确保 import asyncio
if "import asyncio" not in t.split("\n")[0:30]:
    # 加 import
    if "import random" in t:
        t = t.replace("import random\n", "import asyncio\nimport random\n", 1)
    elif "from __future__ import annotations" in t:
        t = t.replace(
            "from __future__ import annotations\n",
            "from __future__ import annotations\n\nimport asyncio\n",
            1,
        )
    print("[fix] 加 import asyncio")

# 替换 world_step 里的调用
old_world_step = '''        templates = director.load_templates()
        event = await run_event_cycle(s, world, templates, force=False)'''
new_world_step = '''        templates = director.load_templates()
        try:
            event = await asyncio.wait_for(
                run_event_cycle(s, world, templates, force=False),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            print("[world_step] 事件生成超时（60s），跳过本次事件")
            event = None'''

if old_world_step in t:
    t = t.replace(old_world_step, new_world_step, 1)
    print("[fix] world_step 加 60s 超时")

# 替换 trigger_event 里的调用
old_trigger = '''        templates = director.load_templates()
        event = await run_event_cycle(s, world, templates, force=True)
        if event is None:
            raise HTTPException(400, "no event triggered")'''
new_trigger = '''        templates = director.load_templates()
        try:
            event = await asyncio.wait_for(
                run_event_cycle(s, world, templates, force=True),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            print("[trigger] 事件生成超时（60s）")
            raise HTTPException(504, "event generation timed out (60s)")'''

if old_trigger in t:
    t = t.replace(old_trigger, new_trigger, 1)
    print("[fix] trigger_event 加 60s 超时")

# 替换 action 里的调用（如果有）
old_action = '''        templates = director.load_templates()
        event = await run_event_cycle(s, world, templates, force=False)'''
if old_action in t and old_world_step not in t:
    # 已经被上面替换过，跳过
    pass

p.write_text(t, encoding="utf-8")

# ============================================================
# 3. 客户端：给 /event/trigger 加更短的超时，快速报错
# ============================================================
p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")

# 只针对 trigger 用更短超时（可选），保持默认 180
# 不改这里

print()
print("重启后端：Ctrl+C 后 uvicorn server.main:app --reload")
print()
print("注意：这次改后，如果 LLM 挂起，最多等 60 秒会返回超时错误，不再卡 3 分钟。")