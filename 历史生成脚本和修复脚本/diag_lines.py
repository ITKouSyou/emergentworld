# 打印 main.gd 里几个可疑区域
from pathlib import Path

p = Path("client/main.gd")
lines = p.read_text(encoding="utf-8").split("\n")

print("=== 行 140-155 ===")
for i in range(140, min(155, len(lines))):
    print("%4d | %s" % (i+1, lines[i]))

print()
print("=== 行 2240-2260 ===")
for i in range(2239, min(2260, len(lines))):
    print("%4d | %s" % (i+1, lines[i]))

print()
print("=== 所有孤儿 api.* 行 ===")
for i, line in enumerate(lines):
    stripped = line.lstrip()
    if stripped.startswith("api.") and ".connect(" in stripped and line == stripped:
        print("行 %d: %s" % (i+1, line[:100]))

print()
print("=== 所有 4 空格开头但非 Tab 的行（怀疑混用） ===")
for i, line in enumerate(lines):
    if line.startswith("    ") and not line.startswith("\t"):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            print("行 %d: %s" % (i+1, line[:100]))