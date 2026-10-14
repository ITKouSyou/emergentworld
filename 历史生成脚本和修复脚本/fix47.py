# resolve 端点加日志 + 前端加打印
from pathlib import Path

# ============================================================
# 1. 后端：resolve 加日志
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

old = '''@app.post("/event/{event_id}/resolve")
async def resolve_event_endpoint(event_id: str, req: ResolveRequest) -> dict:'''
new = '''@app.post("/event/{event_id}/resolve")
async def resolve_event_endpoint(event_id: str, req: ResolveRequest) -> dict:
    print("[resolve] event_id=%r choice_id=%r" % (event_id, req.choice_id))'''

if old in t and 'print("[resolve]' not in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 后端 resolve 加日志")
else:
    print("[skip] 后端已改过")

# ============================================================
# 2. 前端：打印 event_id / choice_id
# ============================================================
p2 = Path("client/main.gd")
t2 = p2.read_text(encoding="utf-8")

old_ui = '''func _on_event_choice_pressed(event_id: String, choice_id: String) -> void:
	_set_loading("正在结算（调用 LLM）...")'''
new_ui = '''func _on_event_choice_pressed(event_id: String, choice_id: String) -> void:
	print("[ui] 用户点击选项：event_id=%r choice_id=%r" % [event_id, choice_id])
	if event_id == "" or choice_id == "":
		print("[ui] 参数为空，忽略")
		return
	_set_loading("正在结算（调用 LLM）...")'''

if old_ui in t2:
    t2 = t2.replace(old_ui, new_ui, 1)
    p2.write_text(t2, encoding="utf-8")
    print("[fix] 前端 _on_event_choice_pressed 加日志")
else:
    print("[skip] 前端已改过")

# 顺便检查 _render_event_entry 里 choices 的 id
t2 = p2.read_text(encoding="utf-8")
i = t2.find("func _refresh_event_action_panel")
if i >= 0:
    e = t2.find("\nfunc ", i + 1)
    body = t2[i:e]
    if 'c.get("id"' not in body and "cid" not in body:
        print("[warn] _refresh_event_action_panel 里可能没读 choice id")

print()
print("重启后端：Ctrl+C → uvicorn server.main:app")
print("Godot 关闭重开")
print()
print("再点一次选项，看两个地方：")
print("  1. Godot 编辑器 Output 面板：应该是 [ui] 用户点击选项：...")
print("  2. uvicorn 窗口：应该是 [resolve] event_id=... choice_id=...")