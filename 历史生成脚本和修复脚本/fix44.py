# 清 Godot 缓存
import shutil
from pathlib import Path

# 删除 .godot 目录
godot_dir = Path("client/.godot")
if godot_dir.exists():
    shutil.rmtree(godot_dir)
    print("[fix] 删除 client/.godot/")
else:
    print("[skip] .godot 不存在")

# 删除 .import（旧 Godot 3 的残留）
imp = Path("client/.import")
if imp.exists():
    shutil.rmtree(imp)
    print("[fix] 删除 client/.import/")

# 检查是否有重复的 api.gd 副本（比如 api.gd.bak）
for f in Path("client").glob("api.gd*"):
    print("  client/%s" % f.name)