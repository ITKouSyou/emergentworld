# 1. 去掉 _cleanup_http 的误删
# 2. 加 90 秒 loading 兜底
# 3. 加请求日志
from pathlib import Path

# ============================================================
# 1. api.gd
# ============================================================
p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")

# 1.1 去掉 _cleanup_http 调用
old1 = '''func _request(method: String, path: String, body: Dictionary, signal_name: String) -> void:
	_cleanup_http()
	var http := HTTPRequest.new()
	http.timeout = 60.0
	add_child(http)'''

new1 = '''func _request(method: String, path: String, body: Dictionary, signal_name: String) -> void:
	print("[api] → %s %s" % [method, path])
	var http := HTTPRequest.new()
	http.timeout = 60.0
	add_child(http)'''

if old1 in t:
    t = t.replace(old1, new1, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 去掉 _cleanup_http 调用（_request）")
else:
    # 尝试其它格式
    old1b = '''func _request(method: String, path: String, body: Dictionary, signal_name: String) -> void:
\t_cleanup_http()
\tvar http := HTTPRequest.new()
\thttp.timeout = 60.0
\tadd_child(http)'''
    if old1b in t:
        t = t.replace(old1b, new1, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] 去掉 _cleanup_http 调用（_request 备用）")
    else:
        print("[skip] _request 已改过或格式不同")

# 1.2 干脆去掉整个 _cleanup_http 函数体（改成空操作）
t = p.read_text(encoding="utf-8")
start = t.find("func _cleanup_http() -> void:")
if start >= 0:
    end = t.find("\n\nfunc ", start + 1)
    if end < 0:
        end = len(t)
    new_cleanup = '''func _cleanup_http() -> void:
	# 空操作：之前的版本会误删正在请求的 HTTPRequest
	pass'''
    t = t[:start] + new_cleanup + t[end:]
    p.write_text(t, encoding="utf-8")
    print("[fix] _cleanup_http 改成空操作")

# 1.3 _on_response 加发送完成的 log
t = p.read_text(encoding="utf-8")
old2 = '''	print("[api] 收到 %s 响应：code=%d result=%d" % [signal_name, response_code, result])'''
new2 = '''	print("[api] ← %s code=%d result=%d" % [signal_name, response_code, result])'''
if old2 in t:
    t = t.replace(old2, new2, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] _on_response log 改短")

# ============================================================
# 2. main.gd：loading 90 秒兜底
# ============================================================
p2 = Path("client/main.gd")
t2 = p2.read_text(encoding="utf-8")

old3 = '''func _on_loading_tick() -> void:
	if loading_message == "":
		loading_timer.stop()
		return
	var elapsed := (Time.get_ticks_msec() - loading_started_ms) / 1000.0
	loading_label.text = "⏳ %s (%.1fs)" % [loading_message, elapsed]'''

new3 = '''func _on_loading_tick() -> void:
	if loading_message == "":
		loading_timer.stop()
		return
	var elapsed := (Time.get_ticks_msec() - loading_started_ms) / 1000.0
	loading_label.text = "⏳ %s (%.1fs)" % [loading_message, elapsed]

	# 兜底：超过 90 秒强制清除
	if elapsed > 90.0:
		print("[ui] loading 超过 90 秒，强制清除")
		is_step_24_running = false
		step_24_done = 0
		_set_loading("")
		status_label.text = "[color=red]请求超时（90s），请再试一次[/color]"'''

if old3 in t2:
    t2 = t2.replace(old3, new3, 1)
    p2.write_text(t2, encoding="utf-8")
    print("[fix] loading 90 秒兜底")
else:
    # 尝试另一格式
    old3b = '''func _on_loading_tick() -> void:
\tif loading_message == "":
\t\tloading_timer.stop()
\t\treturn
\tvar elapsed := (Time.get_ticks_msec() - loading_started_ms) / 1000.0
\tloading_label.text = "⏳ %s (%.1fs)" % [loading_message, elapsed]'''
    if old3b in t2:
        t2 = t2.replace(old3b, new3, 1)
        p2.write_text(t2, encoding="utf-8")
        print("[fix] loading 90 秒兜底（备用）")
    else:
        print("[skip] _on_loading_tick 格式不同，跳过")

print()
print("======= 完成 =======")
print("Godot 完全关闭重开，按 F5")
print()
print("然后点触发事件，看 Godot 编辑器的 Output 面板，应该看到：")
print("  [api] → POST /event/trigger")
print("  [api] ← event_triggered code=200 result=0")