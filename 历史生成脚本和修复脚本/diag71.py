from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

print("=== _build_ui 函数体 ===")
i = t.find("func _build_ui() -> void:")
e = t.find("\nfunc ", i + 1)
body = t[i:e]
print(body)

print()
print("=== _build_faction_tab 出现位置 ===")
for n, line in enumerate(t.split("\n")):
    if "_build_faction_tab" in line:
        print("%4d | %s" % (n + 1, line.strip()))

print()
print("=== 是否还有重复的 right_tabs 声明 ===")
count = t.count("var right_tabs")
print("right_tabs 声明次数：%d" % count)
for n, line in enumerate(t.split("\n")):
    if "var right_tabs" in line:
        print("%4d | %s" % (n + 1, line.strip()))