# 修 _ensure_explore_ui_orig 坏函数头
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

bad = "_ensure_explore_ui_orig() -> void:"
good = "func _ensure_explore_ui() -> void:"

if bad in t:
    t = t.replace(bad, good, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 恢复 _ensure_explore_ui 函数头")
else:
    if "_ensure_explore_ui_orig" in t:
        for i, line in enumerate(t.split("\n")):
            if "_ensure_explore_ui_orig" in line:
                print("行 %d: %r" % (i+1, line))
    else:
        print("[skip] 未找到 _ensure_explore_ui_orig，可能已改过")

# 顺便检查 func _ensure_action_ui 是否存在
if "func _ensure_action_ui" in t:
    print("[ok] _ensure_action_ui 存在")
else:
    print("[warn] _ensure_action_ui 不存在，可能前端行动按钮没加成功")