# 给 main.py 导入 save_event
from pathlib import Path

p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

# 检查是否已导入
if "save_event" in t.split("def ")[0] and "from server.core.world import" in t:
    # 已导入或从 core.world 导入
    if "save_event" not in t.split("\n@app")[0]:
        pass

old = "from server.core.world import load_npcs, load_world, save_world"
new = "from server.core.world import load_npcs, load_world, save_event, save_world"

if old in t and "save_event" not in t.split("\n@app")[0]:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] main.py 导入 save_event")
else:
    # 检查是否已经导入
    if "save_event" in t.split("\n@app")[0]:
        print("[skip] 已有 save_event 导入")
    else:
        print("[fail] 锚点未找到，请手动在 main.py 顶部加：")
        print("from server.core.world import load_npcs, load_world, save_event, save_world")