from pathlib import Path

p = Path("client/main.gd")
lines = p.read_text(encoding="utf-8").split("\n")

# 打印 1538 前后
print("=== 行 1530-1550 ===")
for i in range(1529, min(1550, len(lines))):
    print("%4d | %s" % (i + 1, lines[i]))