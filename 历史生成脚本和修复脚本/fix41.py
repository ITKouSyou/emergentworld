# 清理孤儿 HTTPRequest 节点 + 减少前端轮询
from pathlib import Path

p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")

# 1. 每次创建 HTTPRequest 时先清理旧的（用 queue_free 延迟）
# 其实已经 queue_free 了。改为加个上限检查
old = '''func _request(method: String, path: String, body: Dictionary, signal_name: String) -> void:
	var http := HTTPRequest.new()
	http.timeout = 180.0
	add_child(http)'''

new = '''func _request(method: String, path: String, body: Dictionary, signal_name: String) -> void:
	# 清理超过 20 个的旧 HTTPRequest 节点
	var http_children := []
	for c in get_children():
		if c is HTTPRequest:
			http_children.append(c)
	if http_children.size() > 20:
		for old_http in http_children[:http_children.size() - 10]:
			old_http.queue_free()

	var http := HTTPRequest.new()
	http.timeout = 60.0
	add_child(http)'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] api.gd _request 清理 + 60s 超时")
else:
    print("[skip] api.gd 已改过")

# 2. item_request 也改
t = p.read_text(encoding="utf-8")
old2 = '''func _item_request(method: String, path: String, body: Dictionary, action_name: String) -> void:
	var http := HTTPRequest.new()
	http.timeout = 180.0
	add_child(http)'''

new2 = '''func _item_request(method: String, path: String, body: Dictionary, action_name: String) -> void:
	var http := HTTPRequest.new()
	http.timeout = 60.0
	add_child(http)'''

if old2 in t:
    t = t.replace(old2, new2, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] api.gd item 60s 超时")

# 3. main.gd：减少轮询频率
p2 = Path("client/main.gd")
t2 = p2.read_text(encoding="utf-8")

old3 = '''	map_poll_timer.wait_time = 1.2'''
new3 = '''	map_poll_timer.wait_time = 3.0'''
if old3 in t2:
    t2 = t2.replace(old3, new3, 1)
    print("[fix] 地图轮询 1.2→3.0 秒")

old4 = '''	npc_poll_timer.wait_time = 3.0'''
new4 = '''	npc_poll_timer.wait_time = 6.0'''
if old4 in t2:
    t2 = t2.replace(old4, new4, 1)
    print("[fix] NPC 轮询 3→6 秒")

p2.write_text(t2, encoding="utf-8")

print()
print("Godot 完全关闭重开，按 F5")