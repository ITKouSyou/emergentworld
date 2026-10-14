# 重写 base.py 的 _call_raw：去掉 tenacity + 用 client 自带超时
from pathlib import Path

p = Path("server/generators/base.py")
t = p.read_text(encoding="utf-8")

# 找 _call_raw 函数
start = t.find("    @retry(")
if start < 0:
    start = t.find("    async def _call_raw(")
    if start < 0:
        print("[fail] 找不到 _call_raw")
        raise SystemExit(1)

# 找函数结束（下一个 def 或 class 级缩进结束）
end = t.find("\n    async def ", start + 1)
if end < 0:
    end = t.find("\n    def ", start + 1)
if end < 0:
    end = len(t)

new_func = '''    async def _call_raw(self, prompt: str, schema_json: dict | None = None) -> str:
        """调用 LLM。使用 openai client 自带 timeout，避免 tenacity+asyncio 死锁。"""
        import time as _time
        t0 = _time.time()
        print("[llm] 开始调用 len=%d" % len(prompt))
        try:
            resp = await self.client.chat.completions.create(
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
                timeout=30.0,
            )
            content = resp.choices[0].message.content or "{}"
            print("[llm] 完成 %.1fs len=%d" % (_time.time() - t0, len(content)))
            return content
        except Exception as e:
            print("[llm] 失败 %.1fs: %s: %s" % (
                _time.time() - t0, type(e).__name__, str(e)[:120]))
            raise

    async def text(self, prompt: str) -> str:
        """纯文本调用。"""
        import time as _time
        t0 = _time.time()
        print("[llm.text] 开始 len=%d" % len(prompt))
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                timeout=30.0,
            )
            content = resp.choices[0].message.content or ""
            print("[llm.text] 完成 %.1fs" % (_time.time() - t0))
            return content
        except Exception as e:
            print("[llm.text] 失败 %.1fs: %s" % (_time.time() - t0, type(e).__name__))
            raise
'''

t = t[:start] + new_func + t[end:]

# 检查 tenacity 是否还被引用
if "@retry" in t:
    print("[warn] 文件里还有 @retry 装饰器残留")

# 移除 tenacity import（可选，先保留）
p.write_text(t, encoding="utf-8")
print("[fix] base.py _call_raw + text 重写（去掉 tenacity）")

# 检查 _call_raw 的参数调用
# _call_raw 现在接受 (prompt, schema_json=None)，检查调用方
if "_call_raw(prompt, " in t or "_call_raw(prompt)" in t:
    print("[ok] 调用方会兼容")

# trigger_event 里去外层 wait_for
p2 = Path("server/main.py")
t2 = p2.read_text(encoding="utf-8")

old_trigger = '''        for attempt in range(3):
            remaining = [t for t in templates if t.id not in exclude]
            if not remaining:
                break

            seed_extra = random.randint(0, 10**9)
            tried += 1

            try:
                event = await asyncio.wait_for(
                    run_event_cycle(
                        s, world, remaining,
                        force=True, attempt=seed_extra,
                    ),
                    timeout=25.0,
                )
            except asyncio.TimeoutError:
                print("[trigger] attempt %d 超时（25s）" % attempt)
                continue

            if event is not None:
                break

            rejected = _ef.get_last_rejected_template_id()
            if rejected:
                exclude.add(rejected)
                print("[trigger] attempt %d 被拒：%s" % (attempt, rejected))'''

new_trigger = '''        for attempt in range(3):
            remaining = [t for t in templates if t.id not in exclude]
            if not remaining:
                break

            seed_extra = random.randint(0, 10**9)
            tried += 1

            # 不再用外层 wait_for，让 LLM client 自己超时（30 秒）
            try:
                event = await run_event_cycle(
                    s, world, remaining,
                    force=True, attempt=seed_extra,
                )
            except Exception as e:
                print("[trigger] attempt %d 异常：%s" % (attempt, e))
                continue

            if event is not None:
                break

            rejected = _ef.get_last_rejected_template_id()
            if rejected:
                exclude.add(rejected)
                print("[trigger] attempt %d 被拒：%s" % (attempt, rejected))'''

if old_trigger in t2:
    t2 = t2.replace(old_trigger, new_trigger, 1)
    p2.write_text(t2, encoding="utf-8")
    print("[fix] trigger_event 去掉外层 wait_for")
else:
    print("[skip] trigger_event 已改过")

# 检查 event_flow 里是否有遗留的 wait_for
p3 = Path("server/core/event_flow.py")
t3 = p3.read_text(encoding="utf-8")
if "asyncio.wait_for" in t3:
    print("[warn] event_flow.py 里还有 asyncio.wait_for")
    for i, line in enumerate(t3.split("\n")):
        if "asyncio.wait_for" in line:
            print("  行 %d: %s" % (i+1, line.strip()))

print()
print("重启后端：Ctrl+C → uvicorn server.main:app（不要 --reload）")