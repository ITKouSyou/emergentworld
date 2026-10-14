# 用正则匹配任意缩进，插入 _build_faction_tab 调用
from pathlib import Path
import re

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 找 _build_ui 里的 _build_quest_tab 调用
pattern = re.compile(
    r"(\n([ \t]+)_build_quest_tab\(right_tabs\)\n)",
    re.MULTILINE,
)

m = pattern.search(t)
if not m:
    print("[fail] 找不到 _build_quest_tab(right_tabs) 调用")
    raise SystemExit(1)

indent = m.group(2)
insert_line = indent + "_build_faction_tab(right_tabs)\n"

# 在 _build_quest_tab 之后插入 _build_faction_tab
t = t[:m.end()] + insert_line + t[m.end():]
p.write_text(t, encoding="utf-8")
print("[fix] 在 _build_quest_tab 后插入 _build_faction_tab（缩进=%r）" % indent)

# 打印新的 _build_ui 尾部
t2 = p.read_text(encoding="utf-8")
i = t2.find("func _build_ui")
e = t2.find("\nfunc ", i + 1)
body = t2[i:e]
print()
print("=== _build_ui 尾部（right_tabs 相关） ===")
for line in body.split("\n"):
    if "right_tabs" in line:
        print("  " + line)

print()
print("Godot 完全关闭重开，按 F5")