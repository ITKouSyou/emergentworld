# 整段重写 _connect_signals，保证每行两个 Tab
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

start = t.find("func _connect_signals() -> void:")
if start < 0:
    print("[fail] 找不到 _connect_signals")
    raise SystemExit(1)

after = t.find("\nfunc ", start + 1)
if after < 0:
    after = len(t)

# 硬编码完整函数体，用制表符
T = "\t"
new_body = (
    "func _connect_signals() -> void:" + "\n"
    + T + "api.i18n_received.connect(_on_i18n_received)" + "\n"
    + T + "api.player_received.connect(_on_player_received)" + "\n"
    + T + "api.player_created.connect(_on_player_created)" + "\n"
    + T + "api.player_allocated.connect(_on_player_allocated)" + "\n"
    + T + "api.explore_done.connect(_on_explore_done)" + "\n"
    + T + "api.world_state_received.connect(_on_world_state)" + "\n"
    + T + "api.npc_list_received.connect(_on_npc_list)" + "\n"
    + T + "api.npc_detail_received.connect(_on_npc_detail)" + "\n"
    + T + "api.npc_items_received.connect(_on_npc_items)" + "\n"
    + T + "api.dialogue_received.connect(_on_dialogue)" + "\n"
    + T + "api.event_triggered.connect(_on_event_triggered)" + "\n"
    + T + "api.event_list_received.connect(_on_event_list)" + "\n"
    + T + "api.event_resolved.connect(_on_event_resolved)" + "\n"
    + T + "api.relationships_received.connect(_on_relationships)" + "\n"
    + T + "api.reward_list_received.connect(_on_reward_list)" + "\n"
    + T + "api.item_list_received.connect(_on_item_list)" + "\n"
    + T + "api.item_action_done.connect(_on_item_action_done)" + "\n"
    + T + "api.map_received.connect(_on_map_received)" + "\n"
    + T + "api.chronicle_list_received.connect(_on_chronicle_list)" + "\n"
    + T + "api.chronicle_generated.connect(_on_chronicle_generated)" + "\n"
    + T + "api.action_done.connect(_on_action_done)" + "\n"
    + T + "api.travel_done.connect(_on_travel_done)" + "\n"
    + T + "api.market_received.connect(_on_market_received)" + "\n"
    + T + "api.trade_done.connect(_on_trade_done)" + "\n"
    + T + "api.request_failed.connect(_on_request_failed)"
)

t = t[:start] + new_body + t[after:]
p.write_text(t, encoding="utf-8")
print("[fix] _connect_signals 已重写")

# 打印确认，检查缩进
t2 = p.read_text(encoding="utf-8")
start2 = t2.find("func _connect_signals() -> void:")
after2 = t2.find("\nfunc ", start2 + 1)
print()
print("--- 检查缩进 ---")
for line in t2[start2:after2].split("\n"):
    if line:
        first = line[0]
        prefix = "TAB" if first == "\t" else ("SPACE" if first == " " else "-")
        print("%s | %s" % (prefix, line[:80]))