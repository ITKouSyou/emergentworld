# 把 var status_label: Label 改成 RichTextLabel
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

old = "var status_label: Label\n"
new = "var status_label: RichTextLabel\n"

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] status_label 类型改为 RichTextLabel")
else:
    print("[skip] 未找到 var status_label: Label，可能已改过")
    # 看看现在是什么
    for line in t.split("\n"):
        if "status_label" in line and "var " in line:
            print("  当前声明：%r" % line)