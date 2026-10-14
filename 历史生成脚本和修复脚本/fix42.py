# 前端：任何响应都强制清 loading + 清理旧 HTTPRequest
from pathlib import Path

p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")

# 在 _on_response 开头加个检查日志
old = '''func _on_response(
	result: int, response_code: int,
	_headers: PackedStringArray, body: PackedByteArray,
	http: HTTPRequest, signal_name: String
) -> void:
	http.queue_free()
	if result != HTTPRequest.RESULT_SUCCESS:
		request_failed.emit(signal_name, "transport error: %d" % result)
		return'''

new = '''func _on_response(
	result: int, response_code: int,
	_headers: PackedStringArray, body: PackedByteArray,
	http: HTTPRequest, signal_name: String
) -> void:
	if http != null and is_instance_valid(http):
		http.queue_free()
	print("[api] 收到 %s 响应：code=%d result=%d" % [signal_name, response_code, result])
	if result != HTTPRequest.RESULT_SUCCESS:
		request_failed.emit(signal_name, "transport error: %d" % result)
		return'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] api.gd _on_response 加日志")
else:
    print("[skip] api.gd 已改过或锚点未匹配")

# 清理孤儿
t = p.read_text(encoding="utf-8")
if "func _cleanup_http" not in t:
    tail = '''

func _cleanup_http() -> void:
	var http_children: Array = []
	for c in get_children():
		if c is HTTPRequest:
			http_children.append(c)
	if http_children.size() > 15:
		for old_http in http_children[:http_children.size() - 5]:
			if is_instance_valid(old_http):
				old_http.queue_free()
'''
    t = t.rstrip() + "\n" + tail
    p.write_text(t, encoding="utf-8")
    print("[fix] api.gd 加 _cleanup_http")

# 在 _request 开头调用清理
t = p.read_text(encoding="utf-8")
old_req = '''func _request(method: String, path: String, body: Dictionary, signal_name: String) -> void:
	var http := HTTPRequest.new()
	http.timeout = 180.0'''
new_req = '''func _request(method: String, path: String, body: Dictionary, signal_name: String) -> void:
	_cleanup_http()
	var http := HTTPRequest.new()
	http.timeout = 60.0'''
if old_req in t:
    t = t.replace(old_req, new_req, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] _request 前清理 + 超时 60s")
else:
    print("[skip] _request 已改过")

# main.gd：加个"手动清除 loading"的方法
p2 = Path("client/main.gd")
t2 = p2.read_text(encoding="utf-8")

if "func _force_clear_loading" not in t2:
    tail2 = '''

func _force_clear_loading() -> void:
	is_step_24_running = false
	step_24_done = 0
	_set_loading("")
	if trigger_btn:
		trigger_btn.disabled = false
	if step_btn:
		step_btn.disabled = false
	if step24_btn:
		step24_btn.disabled = false
	if refresh_btn:
		refresh_btn.disabled = false
'''
    t2 = t2.rstrip() + "\n" + tail2
    p2.write_text(t2, encoding="utf-8")
    print("[fix] main.gd 加 _force_clear_loading")