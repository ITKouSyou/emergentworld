from pathlib import Path

p = Path("client/main.gd")
lines = p.read_text(encoding="utf-8").split("\n")

# 打印所有含 autowrap_mode 的行，以及它前面 3 行
targets = []
for i, line in enumerate(lines):
    if "autowrap_mode" in line:
        targets.append(i)

print("共 %d 处" % len(targets))
print()
for idx in targets[:8]:
    print("=== 行 %d ===" % (idx + 1))
    for j in range(max(0, idx - 3), min(len(lines), idx + 2)):
        marker = ">>>" if j == idx else "   "
        print("%s %4d | %s" % (marker, j + 1, lines[j]))
    print()