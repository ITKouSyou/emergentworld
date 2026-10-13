# 把 action_done.connect 加进 _connect_signals，去掉重复的 explore_done
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 1. 找到 _connect_signals 函数
start = t.find("func _connect_signals() -> void:")
if start < 0:
    print("[fail] 找不到 _connect_signals")
    raise SystemExit(1)

end = t.find("\n\nfunc ", start + 1)
if end < 0:
    end = len(t)

body = t[start:end]

# 2. 去重 explore_done.connect
if body.count("api.explore_done.connect(_on_explore_done)") >= 2:
    # 保留一份
    body_new = body.replace(
        "\tapi.explore_done.connect(_on_explore_done)\n\tapi.explore_done.connect(_on_explore_done)\n",
        "\tapi.explore_done.connect(_on_explore_done)\n",
    )
    # 兼容 8 空格缩进
    body_new = body_new.replace(
        "        api.explore_done.connect(_on_explore_done)\n        api.explore_done.connect(_on_explore_done)\n",
        "        api.explore_done.connect(_on_explore_done)\n",
    )
    body = body_new
    print("[fix] 去掉重复的 explore_done.connect")

# 3. 加 action_done.connect（在 _connect_signals 里）
if "action_done.connect" not in body:
    # 插到 request_failed.connect 前面
    anchor = "\tapi.request_failed.connect(_on_request_failed)"
    if anchor in body:
        body = body.replace(
            anchor,
            "\tapi.action_done.connect(_on_action_done)\n" + anchor,
            1,
        )
        print("[fix] 加 action_done.connect")
    else:
        # 备用：插在 player_allocated 后面
        anchor2 = "\tapi.player_allocated.connect(_on_player_allocated)\n"
        if anchor2 in body:
            body = body.replace(
                anchor2,
                anchor2 + "\tapi.action_done.connect(_on_action_done)\n",
                1,
            )
            print("[fix] 加 action_done.connect（备用锚点）")
        else:
            print("[fail] 找不到锚点")
else:
    print("[skip] _connect_signals 里已有 action_done.connect")

# 4. 写回
t = t[:start] + body + t[end:]
p.write_text(t, encoding="utf-8")

# 5. 打印新函数确认
start2 = t.find("func _connect_signals() -> void:")
end2 = t.find("\n\nfunc ", start2 + 1)
print()
print("--- 新 _connect_signals ---")
print(t[start2:end2 if end2 > 0 else len(t)])