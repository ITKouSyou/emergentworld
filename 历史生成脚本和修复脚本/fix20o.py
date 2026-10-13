# 强制在 _connect_signals 里插入 action_done.connect
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

start = t.find("func _connect_signals() -> void:")
if start < 0:
    print("[fail] 找不到 _connect_signals")
    raise SystemExit(1)

end = t.find("\n\nfunc ", start + 1)
if end < 0:
    end = len(t)

body = t[start:end]

# 检查是否真的有 api.action_done.connect
if "api.action_done.connect" in body:
    print("[skip] 已存在")
else:
    # 在 request_failed 前面插入
    anchor = "\tapi.request_failed.connect(_on_request_failed)"
    if anchor not in body:
        anchor = "        api.request_failed.connect(_on_request_failed)"
    if anchor in body:
        # 保留原缩进
        indent = anchor[:len(anchor) - len(anchor.lstrip())]
        new_line = indent + "api.action_done.connect(_on_action_done)"
        body = body.replace(anchor, new_line + "\n" + anchor, 1)
        t = t[:start] + body + t[end:]
        p.write_text(t, encoding="utf-8")
        print("[fix] 强制插入 action_done.connect")
    else:
        print("[fail] 找不到 request_failed 锚点")
        print("--- body 内容 ---")
        print(body)

# 重新打印确认
t2 = p.read_text(encoding="utf-8")
start2 = t2.find("func _connect_signals() -> void:")
end2 = t2.find("\n\nfunc ", start2 + 1)
print()
print("--- 现在 _connect_signals ---")
print(t2[start2:end2 if end2 > 0 else len(t2)])