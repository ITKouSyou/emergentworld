# 让 npc_dialogue 打印真实错误，别静默 fallback
from pathlib import Path

p = Path("server/generators/dialogue.py")
t = p.read_text(encoding="utf-8")

old = '''    try:
        reply = await get_llm().text(prompt)
    except Exception:
        reply = "%s沉默了一会儿，没有回答。" % npc.name'''

new = '''    try:
        reply = await get_llm().text(prompt)
    except Exception as e:
        import traceback
        print("[dialogue] LLM 调用失败：%s" % e)
        traceback.print_exc()
        reply = "%s沉默了一会儿，没有回答。" % npc.name'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] dialogue.py 打印错误")
else:
    print("[skip] 已改过或锚点未匹配")

# 检查 prompt 文件里的占位符
p2 = Path("server/prompts/dialogue.md")
t2 = p2.read_text(encoding="utf-8")
import re
placeholders = set(re.findall(r"\{(\w+)\}", t2))
print()
print("[dialogue.md 占位符] ", sorted(placeholders))

# 检查传给 format 的字段
expected = {"name", "age", "traits", "goals", "location",
            "relation_desc", "relationship_hint", "memories", "player_input"}
missing = expected - placeholders
extra = placeholders - expected
if missing:
    print("[!] dialogue.md 缺少这些占位符：", sorted(missing))
if extra:
    print("[!] dialogue.md 有额外占位符（会引发 KeyError）：", sorted(extra))

print()
print("重启后端：Ctrl+C 后 uvicorn server.main:app --reload")