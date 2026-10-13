"""修复 map_view.gd 里 min()/max() 返回 Variant 导致的类型推断错误。"""
from pathlib import Path

REPLACEMENTS = [
    (
        "var t := min(1.0, float(anim[\"t\"]) + delta / MOVE_DURATION)",
        "var t: float = min(1.0, float(anim[\"t\"]) + delta / MOVE_DURATION)",
    ),
    (
        "var e := t * t * (3.0 - 2.0 * t)",
        "var e: float = t * t * (3.0 - 2.0 * t)",
    ),
]

p = Path("client/map_view.gd")
if not p.exists():
    print("未找到 client/map_view.gd")
    raise SystemExit(1)

text = p.read_text(encoding="utf-8")
total = 0
for old, new in REPLACEMENTS:
    n = text.count(old)
    if n:
        text = text.replace(old, new)
        total += n
        print(f"[fix] {n} 处：{old.strip()[:50]}...")
    else:
        print(f"[skip] 未匹配：{old.strip()[:50]}...")

if total:
    p.write_text(text, encoding="utf-8", newline="\n")
    print(f"\n共 {total} 处。回到 Godot 会自动重载。")
else:
    print("\n没有需要修改的。可能你已经改过了。")