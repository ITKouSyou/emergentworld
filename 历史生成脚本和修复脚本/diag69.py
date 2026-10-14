from pathlib import Path

print("=== main.gd ===")
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

print("_build_faction_tab 定义：%s" % ("func _build_faction_tab" in t))
print("_build_faction_tab 调用：%s" % ("_build_faction_tab(" in t.replace("func _build_faction_tab", "")))
print("faction_log 变量：%s" % ("var faction_log:" in t))
print("_on_factions_received：%s" % ("func _on_factions_received" in t))
print("factions_received.connect：%s" % ("factions_received.connect" in t))
print("所属派系 显示：%s" % ("所属派系" in t))
print("api.fetch_factions 调用：%s" % ("api.fetch_factions()" in t))

print()
print("=== _build_ui 里的 Tab 构建部分 ===")
i = t.find("func _build_ui")
e = t.find("\nfunc ", i + 1)
body = t[i:e]
for line in body.split("\n"):
    if "_build_" in line and "_tab" in line:
        print("  %s" % line.strip())

print()
print("=== api.gd ===")
p2 = Path("client/api.gd")
t2 = p2.read_text(encoding="utf-8")
print("fetch_factions：%s" % ("func fetch_factions" in t2))
print("factions_received signal：%s" % ("signal factions_received" in t2))

print()
print("=== /faction 端点 ===")
p3 = Path("server/main.py")
t3 = p3.read_text(encoding="utf-8")
print("/faction 端点：%s" % ('@app.get("/faction")' in t3))

print()
print("=== faction.py ===")
p4 = Path("server/systems/faction.py")
print("文件存在：%s" % p4.exists())