from pathlib import Path

p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")
lines = t.split("\n")

print("总行数：%d" % len(lines))
print()

# 检查缩进：所有行用 Tab 还是空格？
print("=== 缩进检查 ===")
tab_lines = 0
space_lines = 0
for i, line in enumerate(lines):
    if line.startswith("\t"):
        tab_lines += 1
    elif line.startswith("    ") and not line.startswith("\t"):
        space_lines += 1
        print("行 %d 用空格缩进: %r" % (i+1, line[:80]))

print("Tab 行数：%d  空格行数：%d" % (tab_lines, space_lines))
print()

# 打印所有 func 声明及行号
print("=== 所有函数 ===")
for i, line in enumerate(lines):
    if line.lstrip().startswith("func "):
        print("%4d | %s" % (i+1, line))

print()
print("=== 所有 signal 声明 ===")
for i, line in enumerate(lines):
    if "signal " in line and line.lstrip().startswith("signal "):
        print("%4d | %s" % (i+1, line))

# 找可疑行：奇数个引号（可能字符串未闭合）
print()
print("=== 疑似未闭合的字符串 ===")
for i, line in enumerate(lines):
    # 去掉转义的引号
    clean = line.replace('\\"', '').replace("\\'", "")
    dq = clean.count('"')
    if dq % 2 == 1 and not clean.lstrip().startswith("#"):
        print("行 %d: %s" % (i+1, line[:100]))