# 彻底重写 _connect_signals，并把所有孤儿 api.* 行清掉
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# ============================================================
# 第 1 步：删除所有以 "api.xxx.connect" 开头但顶格的行（孤儿）
# ============================================================
lines = t.split("\n")
kept = []
removed = 0
for line in lines:
    stripped = line.lstrip()
    # 孤儿判定：以 api. 开头，且原行没有 \t 也没有前导空格
    if stripped.startswith("api.") and stripped.find(".connect(") > 0:
        if line == stripped:  # 顶格，是孤儿
            removed += 1
            print("删除孤儿：%s" % line[:80])
            continue
    kept.append(line)

t = "\n".join(kept)
print("[fix] 删除 %d 个孤儿行" % removed)

# ============================================================
# 第 2 步：用完整的信号列表重写 _connect_signals
# ============================================================
signals = [
    "i18n_received",
    "player_received",
    "player_created",
    "player_allocated",
    "explore_done",
    "world_state_received",
    "npc_list_received",
    "npc_detail_received",
    "npc_items_received",
    "dialogue_received",
    "event_triggered",
    "event_list_received",
    "event_resolved",
    "relationships_received",
    "reward_list_received",
    "item_list_received",
    "item_action_done",
    "map_received",
    "chronicle_list_received",
    "chronicle_generated",
    "action_done",
    "travel_done",
    "market_received",
    "trade_done",
    "goals_received",
    "goal_claimed",
    "request_failed",
]

T = "\t"
new_func = "func _connect_signals() -> void:\n"
for sig in signals:
    handler_map = {
        "i18n_received": "_on_i18n_received",
        "player_received": "_on_player_received",
        "player_created": "_on_player_created",
        "player_allocated": "_on_player_allocated",
        "explore_done": "_on_explore_done",
        "world_state_received": "_on_world_state",
        "npc_list_received": "_on_npc_list",
        "npc_detail_received": "_on_npc_detail",
        "npc_items_received": "_on_npc_items",
        "dialogue_received": "_on_dialogue",
        "event_triggered": "_on_event_triggered",
        "event_list_received": "_on_event_list",
        "event_resolved": "_on_event_resolved",
        "relationships_received": "_on_relationships",
        "reward_list_received": "_on_reward_list",
        "item_list_received": "_on_item_list",
        "item_action_done": "_on_item_action_done",
        "map_received": "_on_map_received",
        "chronicle_list_received": "_on_chronicle_list",
        "chronicle_generated": "_on_chronicle_generated",
        "action_done": "_on_action_done",
        "travel_done": "_on_travel_done",
        "market_received": "_on_market_received",
        "trade_done": "_on_trade_done",
        "goals_received": "_on_goals_received",
        "goal_claimed": "_on_goal_claimed",
        "request_failed": "_on_request_failed",
    }
    handler = handler_map[sig]
    new_func += T + "api.%s.connect(%s)\n" % (sig, handler)

# 去掉末尾换行
new_func = new_func.rstrip("\n")

# 找到原 _connect_signals 函数，替换
start = t.find("func _connect_signals() -> void:")
if start < 0:
    print("[fail] 找不到 _connect_signals")
    raise SystemExit(1)

after = t.find("\nfunc ", start + 1)
if after < 0:
    after = len(t)

t = t[:start] + new_func + "\n" + t[after:]
p.write_text(t, encoding="utf-8")
print("[fix] _connect_signals 重写完成")

# ============================================================
# 第 3 步：打印结果
# ============================================================
t2 = p.read_text(encoding="utf-8")
start2 = t2.find("func _connect_signals() -> void:")
after2 = t2.find("\nfunc ", start2 + 1)
print()
print("--- 新 _connect_signals ---")
for line in t2[start2:after2].split("\n"):
    if line:
        first = line[0]
        marker = "T" if first == "\t" else ("S" if first == " " else "-")
        print("%s | %s" % (marker, line[:90]))

# ============================================================
# 第 4 步：全局检查是否还有孤儿
# ============================================================
orphans = []
for i, line in enumerate(t2.split("\n")):
    s = line.lstrip()
    if s.startswith("api.") and ".connect(" in s and line == s:
        orphans.append((i+1, line))

if orphans:
    print()
    print("[warn] 还有 %d 个孤儿行：" % len(orphans))
    for ln, l in orphans:
        print("  行 %d: %s" % (ln, l[:80]))
else:
    print()
    print("[ok] 没有孤儿行")

print()
print("Godot 完全关闭重开，按 F5")