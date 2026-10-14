# GDScript: in (a, b, c) 要改成 in [a, b, c]
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 替换所有 `in ("...", "...", ...)` 为 `in ["...", ...]`
import re

# 模式：in ( 后面是带引号的字符串列表，直到 )
# 简单替换：只处理出现的这一处
old = 'elif st in ("completed", "failed", "abandoned"):'
new = 'elif st in ["completed", "failed", "abandoned"]:'

if old in t:
    t = t.replace(old, new)
    print("[fix] 修 elif st in (...) 为 [...]")
else:
    # 通用正则
    pattern = re.compile(r'\bin\s*\(\s*("([^"]*)",?\s*)+\)')
    matches = pattern.findall(t)
    if matches:
        def repl(m):
            inner = m.group(0)[m.group(0).index("(")+1:-1]
            return "in [%s]" % inner
        t = pattern.sub(repl, t)
        print("[fix] 通用替换完成")
    else:
        print("[skip] 未找到，可能已经改过")

p.write_text(t, encoding="utf-8")

# 扫描还有多少 in ( ... )
remaining = re.findall(r'\bin\s*\([^)]*\)', t)
bad = [r for r in remaining if '"' in r or "'" in r]
if bad:
    print()
    print("[warn] 还有 %d 处可能的 in (...)：" % len(bad))
    for b in bad[:5]:
        print("  %s" % b)
else:
    print()
    print("[ok] 没有 in (...) 用法")

print()
print("Godot 完全关闭重开，按 F5")