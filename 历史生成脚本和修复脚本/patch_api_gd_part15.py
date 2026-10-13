"""给 api.gd 加 resolve_event 方法和 event_resolved 信号。"""
from pathlib import Path

p = Path("client/api.gd")
text = p.read_text(encoding="utf-8")

# 加信号
if "signal event_resolved" not in text:
    text = text.replace(
        "signal event_list_received(data: Array)",
        "signal event_list_received(data: Array)\nsignal event_resolved(data: Dictionary)",
    )

# 加方法
if "func resolve_event" not in text:
    NEW_METHOD = '''

func resolve_event(event_id: String, choice_id: String) -> void:
	_request("POST", "/event/%s/resolve" % event_id, {"choice_id": choice_id}, "event_resolved")
'''
    # 插在 fetch_map 之前
    text = text.replace("\n\nfunc fetch_map(", NEW_METHOD + "\n\nfunc fetch_map(", 1)

p.write_text(text, encoding="utf-8", newline="\n")
print("[fix] client/api.gd 已更新")