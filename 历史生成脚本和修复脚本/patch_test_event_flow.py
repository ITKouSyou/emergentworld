"""更新 test_event_flow.py：事件现在停在 awaiting_player，需要玩家响应。"""
from pathlib import Path

p = Path("tests/test_event_flow.py")
text = p.read_text(encoding="utf-8")

OLD = '''        evt = await event_flow.run_event_cycle(s, world, [tpl], force=True)
        assert evt is not None
        assert evt.state == "resolved"'''

NEW = '''        evt = await event_flow.run_event_cycle(s, world, [tpl], force=True)
        assert evt is not None
        # 新流程：事件生成后停在 awaiting_player，等玩家响应
        assert evt.state == "awaiting_player"
        # 应该已生成玩家选项
        assert "choices" in evt.payload
        assert len(evt.payload["choices"]) == 3
        choice_ids = [c["id"] for c in evt.payload["choices"]]
        assert choice_ids == ["help", "observe", "oppose"]'''

if OLD not in text:
    print("未找到目标断言，可能已改过。请手动打开 tests/test_event_flow.py 检查。")
    raise SystemExit(1)

text = text.replace(OLD, NEW)
p.write_text(text, encoding="utf-8", newline="\n")
print("[fix] tests/test_event_flow.py 已更新")
print()
print("再跑：pytest -v")