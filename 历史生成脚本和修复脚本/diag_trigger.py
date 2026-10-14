# 直接测 trigger 的每一步，看时间花在哪
import asyncio
import time
from pathlib import Path

async def main():
    from sqlmodel import Session, create_engine
    from server.config import settings
    from server.core.world import load_world, load_npcs
    from server.core import director, event_flow

    engine = create_engine(f"sqlite:///{settings.db_path}")
    with Session(engine) as s:
        world = load_world(s)
        npcs = load_npcs(s)
        templates = director.load_templates()

        print("NPC 数：%d" % len(npcs))
        print("模板数：%d" % len(templates))
        print()

        # 1. 预扫
        t0 = time.time()
        exclude = event_flow.impossible_templates(templates, npcs)
        print("[1] 预扫 (%.3fs)：排除 %d 个" % (time.time() - t0, len(exclude)))
        print("    排除：%s" % sorted(exclude))
        print()

        remaining = [t for t in templates if t.id not in exclude]
        print("[2] 剩余候选模板：%d 个" % len(remaining))
        print()

        # 3. 一次完整 run_event_cycle
        print("[3] 调用 run_event_cycle（含 LLM）...")
        t0 = time.time()
        try:
            event = await asyncio.wait_for(
                event_flow.run_event_cycle(s, world, remaining, force=True),
                timeout=60.0,
            )
            dt = time.time() - t0
            if event is None:
                print("    返回 None (%.1fs)" % dt)
                print("    最后被拒模板：%s" % event_flow.get_last_rejected_template_id())
            else:
                print("    成功 (%.1fs)：%s" % (dt, event.id))
                print("    模板：%s" % event.template_id)
                print("    摘要：%s" % event.payload.get("summary", ""))
        except asyncio.TimeoutError:
            print("    [超时] 60 秒无响应")
        except Exception as e:
            import traceback
            print("    [异常] %s" % e)
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())