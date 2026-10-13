# 把按钮文字里的 tick 换中文
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

repls = [
    ('step_btn.text = "推进一 tick"', 'step_btn.text = "推进 1 回合"'),
    ('step_btn.text = "推进 1 tick"', 'step_btn.text = "推进 1 回合"'),
    ('step24_btn.text = "推进 24 tick"', 'step24_btn.text = "推进 24 回合"'),
    ('"推进一 tick"', '"推进 1 回合"'),
    ('"推进 24 tick"', '"推进 24 回合"'),
]

count = 0
for old, new in repls:
    if old in t:
        n = t.count(old)
        t = t.replace(old, new)
        print("[fix] %r → %r  (%d 处)" % (old, new, n))
        count += n

# 保险：正则处理剩余的 tick 字样（只在 .text 里）
import re
t, n = re.subn(r'(\.text\s*=\s*"[^"]*?)tick', r'\1回合', t)
if n:
    print("[fix] 正则替换剩余 tick：%d 处" % n)
    count += n

p.write_text(t, encoding="utf-8")

if count == 0:
    print("[skip] 没找到 tick 相关文本")
    # 打印所有含 tick 的行
    for i, line in enumerate(t.split("\n")):
        if "tick" in line.lower() and "text" in line.lower():
            print("  行 %d: %r" % (i + 1, line))

print()
print("Godot 完全关闭重开，按 F5")