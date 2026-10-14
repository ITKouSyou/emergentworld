# 修 main.gd：把孤儿 api.market_received 等移到 _connect_signals 里
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")
lines = t.split("\n")

# 找到所有孤儿行：以 "api.market_received" 或 "api.trade_done" 开头，
# 但不在 _connect_signals 函数体里
# 判断方法：从后往前找 _connect_signals 的结束位置

# 先找 _connect_signals 的范围
start = t.find("func _connect_signals() -> void:")
if start < 0:
    print("[fail] 找不到 _connect_signals")
    raise SystemExit(1)

end = t.find("\n\nfunc ", start + 1)
if end < 0:
    end = len(t)

body = t[start:end]
print("--- 原 _connect_signals ---")
print(body)

# 检查孤儿行是否在 body 之外
orphan_lines = []
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("api.market_received.connect") or stripped.startswith("api.trade_done.connect"):
        # 检查这个位置是否在 _connect_signals 范围内
        # 计算 line 在文件中的绝对字符位置
        char_pos = sum(len(l) + 1 for l in lines[:i])
        if not (start <= char_pos <= end):
            orphan_lines.append(i)

print("孤儿行索引：%r" % orphan_lines)

# 删除孤儿行
if orphan_lines:
    for i in sorted(orphan_lines, reverse=True):
        print("删除行 %d: %r" % (i+1, lines[i]))
        del lines[i]
    t = "\n".join(lines)
    p.write_text(t, encoding="utf-8")
    print("[fix] 删除孤儿行")

# 重新计算 body 并插入
t = p.read_text(encoding="utf-8")
start = t.find("func _connect_signals() -> void:")
end = t.find("\n\nfunc ", start + 1)
body = t[start:end]

if "api.market_received.connect" not in body:
    anchor = "        api.request_failed.connect(_on_request_failed)"
    if anchor not in body:
        anchor = "\tapi.request_failed.connect(_on_request_failed)"
    if anchor in body:
        indent = anchor[:len(anchor) - len(anchor.lstrip())]
        new_lines = (
            indent + "api.market_received.connect(_on_market_received)\n"
            + indent + "api.trade_done.connect(_on_trade_done)\n"
        )
        body = body.replace(anchor, new_lines + anchor, 1)
        t = t[:start] + body + t[end:]
        p.write_text(t, encoding="utf-8")
        print("[fix] 插入市场信号连接到 _connect_signals")

# 打印最终结果确认
t = p.read_text(encoding="utf-8")
start = t.find("func _connect_signals() -> void:")
end = t.find("\n\nfunc ", start + 1)
print()
print("--- 新 _connect_signals ---")
print(t[start:end])

print()
print("Godot 完全关闭重开，按 F5")