import httpx
import random
import time
import sys

BASE_URL = "http://127.0.0.1:8000"
# 全局超时设置为 90 秒，防止大模型生成卡住
client = httpx.Client(timeout=90.0)

def main():
    print("=== EmergentWorld 机器人自动化模拟器 (强交互测试版) ===")
    
    r = client.get(f"{BASE_URL}/player")
    if not r.json().get("created"):
        print("[*] 未检测到玩家，正在创建新玩家...")
        req = {"name": "无头测试员", "gender": "male", "background": "流浪者"}
        client.post(f"{BASE_URL}/player", json=req)
    else:
        print("[*] 检测到已有玩家，直接开始模拟。")
    
    total_ticks = int(sys.argv[1]) if len(sys.argv) > 1 else 72
    print(f"[*] 准备推进 {total_ticks} 个 tick (约 {total_ticks//24} 天)...\n")
    
    success_actions = 0
    resolved_events = 0
    
    for i in range(total_ticks):
        action = random.choice(["gather", "hunt", "train", "explore", "socialize"])
        
        try:
            r_action = client.post(f"{BASE_URL}/action", json={"action": action})
            if r_action.status_code != 200:
                print(f"  [x] 行动请求失败: {r_action.text}")
                continue
                
            data = r_action.json()
            success_actions += 1
            
            p = data.get("player", {})
            day = data.get("day", 1)
            hour = data.get("hour", 0)
            
            # 打印行动时，顺便看看后端返回的 world_event
            we = data.get("world_event")
            event_msg = ""
            if we:
                event_msg = f" | 触发事件: {we.get('template_label')} (待处理: {we.get('awaiting_player')})"
            
            print(f"[第 {day} 天 {hour:02d}:00] 行动: {action:<9} | 金币: {p.get('money',0):<4} | Lv: {p.get('level',1)}{event_msg}")
            
            # 查待处理事件并解决
            r_pending = client.get(f"{BASE_URL}/event/pending")
            if r_pending.status_code == 200:
                pending_events = r_pending.json()
                for ev in pending_events:
                    eid = ev["id"]
                    choices = ev.get("choices", [])
                    if choices:
                        cid = choices[0]["id"]
                        r_resolve = client.post(f"{BASE_URL}/event/{eid}/resolve", json={"choice_id": cid})
                        if r_resolve.status_code == 200:
                            resolved_events += 1
                            print(f"   -> [处理事件] {ev.get('template_label')} (选了: {choices[0].get('label')})")
                            
            # 自动去市场卖东西
            if i % 8 == 0:
                r_items = client.get(f"{BASE_URL}/item?owner_id=player")
                items = r_items.json()
                if items:
                    print(f"   -> [去市场] 发现背包有 {len(items)} 件物品，准备出售...")
                    for it in items:
                        client.post(f"{BASE_URL}/trade/sell", json={"item_id": it["id"]})
                            
        except httpx.TimeoutException:
            print(f"  [!] 第 {i+1} 次行动超时，跳过...")
            continue
        except Exception as e:
            print(f"\n[x] 发生异常: {e}")
            break
            
        time.sleep(0.1)

    print("\n" + "="*40)
    print("📊 机器人模拟报告")
    print("="*40)
    print(f"总计 Ticks  : {total_ticks}")
    print(f"成功行动次数: {success_actions}")
    print(f"解决事件次数: {resolved_events}")
    print("="*40)

if __name__ == "__main__":
    main()