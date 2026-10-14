# 把 _connect_signals 函数体里所有缩进统一成 Tab
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

start = t.find("func _connect_signals() -> void:")
if start < 0:
    print("[fail] 找不到 _connect_signals")
    raise SystemExit(1)

after = t.find("\nfunc ", start + 1)
if after < 0:
    after = len(t)

body = t[start:after]

# 每一行把前导空格换成 Tab（每 4 空格 = 1 Tab）
lines = body.split("\n")
fixed = []
count = 0
for line in lines:
    if line == "":
        fixed.append(line)
        continue
    # 数前导空格
    stripped = line.lstrip(" ")
    leading_spaces = len(line) - len(stripped)
    if leading_spaces > 0:
        tabs = "\t" * (leading_spaces // 4)
        rest = " " * (leading_spaces % 4) + stripped
        fixed.append(tabs + rest)
        count += 1
    else:
        fixed.append(line)

new_body = "\n".join(fixed)
t = t[:start] + new_body + t[after:]

# 也顺便检查：整个文件里如果有连续 4 空格缩进的 _connect_signals 外行，也一并处理
# 简单起见只处理 _connect_signals

p.write_text(t, encoding="utf-8")
print("[fix] 补 Tab %d 行" % count)

# 打印确认
t2 = p.read_text(encoding="utf-8")
start2 = t2.find("func _connect_signals() -> void:")
after2 = t2.find("\nfunc ", start2 + 1)
print()
print("--- 新 _connect_signals ---")
print(t2[start2:after2])

# 顺便检查整个文件是否还有混用：以 4 空格开头但不是 tab 的行
mixed = 0
for i, line in enumerate(t2.split("\n")):
    if line.startswith("    ") and not line.startswith("\t"):
        # 检查这一行前面是函数体（不是顶层）
        if i > 0:
            prev = t2.split("\n")[i-1]
            if prev.startswith("\t") or prev.startswith("    "):
                mixed += 1

if mixed > 0:
    print()
    print("[warn] 文件里还有 %d 处疑似混用缩进" % mixed)
    print("如果 Godot 再报错，把报错行号发我")