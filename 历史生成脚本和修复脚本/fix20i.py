# 确保 _ensure_action_ui 被调用，并隐藏旧的 explore_btn
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 1. 检查函数是否存在
has_func = "func _ensure_action_ui" in t
has_call = "_ensure_action_ui()" in t.split("func _ensure_action_ui")[0] if has_func else False

print("函数存在：%s" % has_func)
print("已有调用：%s" % has_call)

# 2. 如果没有函数，先报错
if not has_func:
    print("[fail] _ensure_action_ui 函数不存在，需要先跑 fix20f.py")
    raise SystemExit(1)

# 3. 在 _ready 末尾确保调用
if not has_call:
    anchor = "\t_build_ui()\n"
    if anchor in t:
        t = t.replace(anchor, anchor + "\t_ensure_action_ui()\n", 1)
        print("[fix] 在 _build_ui 后调用 _ensure_action_ui")
    else:
        # 备用：在 api.fetch_i18n() 后
        anchor2 = "\tapi.fetch_i18n()\n"
        if anchor2 in t:
            t = t.replace(anchor2, anchor2 + "\t_ensure_action_ui()\n", 1)
            print("[fix] 在 fetch_i18n 后调用 _ensure_action_ui")
        else:
            print("[fail] 找不到 _ready 锚点")
else:
    print("[skip] 已有调用")

# 4. 在 _ensure_action_ui 里隐藏旧的 explore_btn
# 找 explore_btn.visible = false 是否已经在函数里
if "explore_btn.visible = false" not in t:
    anchor = "func _ensure_action_ui() -> void:\n"
    if anchor in t:
        # 在函数体开头插入隐藏逻辑
        body_start = t.find(anchor) + len(anchor)
        insert = (
            "\tif explore_btn != null and is_instance_valid(explore_btn):\n"
            "\t\texplore_btn.visible = false\n"
            "\t\tif explore_result_label != null and is_instance_valid(explore_result_label):\n"
            "\t\t\texplore_result_label.visible = false\n"
        )
        t = t[:body_start] + insert + t[body_start:]
        print("[fix] 隐藏旧 explore_btn")

p.write_text(t, encoding="utf-8")
print()
print("回 Godot 完全关闭再开，按 F5")