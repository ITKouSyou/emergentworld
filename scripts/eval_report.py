import sys
import os
import asyncio
import time

# 确保能引到 server
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.generators.npc import generate_npc
from server.models.schemas import NPC

TEST_NAMES = [f"测试员{i}" for i in range(100)]
GENDERS = ["male", "female"]

async def run_test():
    print("=== 启动真实 NPC 生成批量测试 ===")
    print("警告：这将真实调用 LLM API，请确保 .env 中的 key 额度充足。")
    print("按回车开始，或 Ctrl+C 退出...")
    
    # 如果你在无头环境跑，把下面这行注释掉
    # input()
    
    success_count = 0
    fallback_count = 0
    total_time = 0.0
    
    for i, name in enumerate(TEST_NAMES):
        gender = GENDERS[i % 2]
        start = time.time()
        
        print(f"[{i+1}/100] 正在生成: {name} ({gender}) ...")
        
        try:
            # 真实调用异步生成
            npc: NPC = await generate_npc(name, context="村庄里的普通村民", gender=gender)
            
            elapsed = time.time() - start
            total_time += elapsed
            
            # 由于现在的重试机制在 Pipeline 内部处理，如果走到了 fallback，
            # 你的 npc.goals 会是一个固定的随机模板。
            # 这里用个简单逻辑：如果耗时极短，大概率没走网络
            if elapsed < 1.0:
                fallback_count += 1
                print(f"  -> 快速兜底，耗时 {elapsed:.2f}s")
            else:
                success_count += 1
                print(f"  -> 生成成功，耗时 {elapsed:.2f}s")
                
            print(f"     姓名: {npc.name}, 年龄: {npc.age}, 目标: {npc.goals}")
            
        except Exception as e:
            fallback_count += 1
            print(f"  -> 发生异常，计入失败: {e}")

    print("\n" + "="*40)
    print("📊 批量生成测试报告")
    print("="*40)
    print(f"总计次数: 100")
    print(f"成功次数: {success_count}")
    print(f"兜底/失败: {fallback_count}")
    print(f"总耗时: {total_time:.2f}s")
    print(f"平均耗时: {total_time/100:.2f}s/人")
    
    if fallback_count > 10:
        print("⚠️ 兜底率超过 10%，请检查：")
        print("   1. 是否 API Key 余额不足或网络超时。")
        print("   2. 评估器规则是否过于严苛（导致 LLM 重试 2 次仍被拒）。")
    else:
        print("✅ 生成系统运转良好！")

if __name__ == "__main__":
    asyncio.run(run_test())