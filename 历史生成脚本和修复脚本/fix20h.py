# 修 main.gd 里字符串内嵌英文直引号
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 目标行：把 见"事件"Tab 改成 见【事件】Tab
bad = '（有一件事正在等你决定，见"事件"Tab）'
good = '（有一件事正在等你决定，见【事件】Tab）'

if bad in t:
    t = t.replace(bad, good)
    p.write_text(t, encoding="utf-8")
    print("[fix] 修好内嵌引号")
else:
    # 备用：直接找那一行报错打印
    for i, line in enumerate(t.split("\n")):
        if "有一件事正在等你决定" in line:
            print("行 %d: %r" % (i+1, line))
    print("[skip] 未找到目标，已打印相关行")

print()
print("回 Godot 按 F5")