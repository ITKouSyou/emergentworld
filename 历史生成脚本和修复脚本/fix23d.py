# 给 _connect_signals 函数体里缺缩进的行补缩进
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

start = t.find("func _connect_signals() -> void:")
if start < 0:
    print("[fail] 找不到 _connect_signals")
    raise SystemExit(1)

# 找函数结束（下一个顶层 func 或文件末尾）
after = t.find("\nfunc ", start + 1)
if after < 0:
    after = len(t)

body = t[start:after]

# 逐行处理：以 api. 开头但无缩进的，补 8 空格
lines = body.split("\n")
fixed = []
count = 0
for line in lines:
    if line.startswith("api."):
        fixed.append("        " + line)
        count += 1
    else:
        fixed.append(line)

new_body = "\n".join(fixed)
t = t[:start] + new_body + t[after:]
p.write_text(t, encoding="utf-8")
print("[fix] 补缩进 %d 行" % count)

# 打印确认
t2 = p.read_text(encoding="utf-8")
start2 = t2.find("func _connect_signals() -> void:")
after2 = t2.find("\nfunc ", start2 + 1)
print()
print("--- 新 _connect_signals ---")
print(t2[start2:after2])