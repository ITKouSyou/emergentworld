import sys
import os
import asyncio
import yaml
import re
import random
import uuid

# 确保能引到 server
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.generators.base import get_llm
from server.models.schemas import EventTemplate
from server.map_layout import LOCATION_LAYOUT

OUTPUT_DIR = "content/templates/events"
TOTAL_TO_GENERATE = 20  # 这次我们一次生成 20 个！

# 自动提取地图上的所有地点（排除隐藏地点，或者保留隐藏地点你可以自己选）
LOCATIONS = list(LOCATION_LAYOUT.keys())

# 丰富的事件标签池
ALL_TAGS = [
    "mystery", "forest", "daily", "survival", 
    "conflict", "social", "romance", "trade", 
    "political", "adventure", "celebration", "ritual",
    "investigation", "plot", "combat"
]

# 强制输出 JSON
PROMPT_TEMPLATE = """你是一个顶级的游戏文案策划。请为文字 RPG 游戏生成一个事件模板。
要求事件的主题带有【{tags}】元素，主要发生在【{location_name} ({location_id})】。

请严格输出合法的 JSON 格式字典，包含以下字段：
{{
  "id": "全小写英文+下划线组合（如 forest_mystery_01），不能重复",
  "label": "这个事件的中文名字，4-6个字（如：林间怪影）",
  "tags": ["{tag_1}", "{tag_2}"],
  "cooldown": 10,
  "weight": 1.0,
  "interactive": true,
  "conditions": [],
  "params": {{
    "participant_count": 2,
    "location": "{location_id}"
  }},
  "prompt": "用 2-3 句话描述这个事件的起因和冲突（例如：夏日炎热，几个村人相约到河湾戏水，有人不慎呛水，众人慌乱）。要求接地气、有具体的行为描写，不要用宏大的词汇，不要出现现代口吻。",
  "evaluator": {{
    "require": ["participant_a", "participant_b", "clue"],
    "max_reward": 0.2
  }}
}}

只输出 JSON，不要输出任何 markdown 标记或解释性文字。
"""

def validate_and_format(data: dict) -> EventTemplate | None:
    try:
        tpl = EventTemplate(**data)
        if len(tpl.prompt) < 20:
            return None
        banned_words = ["作为AI", "无法生成", "抱歉", "我是一个"]
        for w in banned_words:
            if w in tpl.prompt:
                print(f"   [!] 包含套话 '{w}'，丢弃")
                return None
        return tpl
    except Exception as e:
        print(f"   [x] Pydantic 校验失败: {e}")
        return None

async def generate_one(idx: int) -> bool:
    # 随机抽取一个地点
    loc_id = random.choice(LOCATIONS)
    loc_name = LOCATION_LAYOUT[loc_id].get("name", loc_id)
    
    # 随机抽取 2 个标签
    current_tags = random.sample(ALL_TAGS, k=2)
    tags_str = ", ".join(current_tags)

    prompt = PROMPT_TEMPLATE.format(
        tags=tags_str, 
        tag_1=current_tags[0],
        tag_2=current_tags[1],
        location_id=loc_id,
        location_name=loc_name
    )
    
    # 增加一点随机扰动，防止生成内容同质化
    prompt += f"\n这是第 {idx+1} 次请求，请务必发挥想象力，创造一个与之前完全不同的事件剧本。"

    try:
        data = await get_llm().text_json(prompt)
        
        if not isinstance(data, dict):
            print(f"   [x] 返回内容不是字典")
            return False

        tpl = validate_and_format(data)
        if not tpl:
            return False

        # 确保 id 是合法的英文并且唯一
        base_id = re.sub(r'[^a-z0-9_]', '', tpl.id.lower())
        tpl.id = base_id
        
        filename = f"{tpl.id}.yaml"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        # 如果文件已存在，强行加后缀去重
        if os.path.exists(filepath):
            suffix = str(uuid.uuid4().hex)[:4]
            filename = f"{tpl.id}_{suffix}.yaml"
            tpl.id = f"{tpl.id}_{suffix}"
            filepath = os.path.join(OUTPUT_DIR, filename)

        # 保存为 YAML
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(tpl.model_dump(), f, allow_unicode=True, sort_keys=False)
            
        print(f"   [√] [{tpl.label}] 已生成 -> {filename}")
        return True
        
    except Exception as e:
        print(f"   [x] 请求或生成异常: {e}")
        return False

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print(f"=== 开始批量生成事件模板 ===")
    print(f"目标：{TOTAL_TO_GENERATE} 个")
    print(f"可用地点池 ({len(LOCATIONS)} 个)：{', '.join(LOCATIONS[:5])} ...")
    print(f"可用标签池：{', '.join(ALL_TAGS)}\n")
    
    # 采用分批并发，每批 5 个，防止 API 限流
    success_count = 0
    batch_size = 5
    for i in range(0, TOTAL_TO_GENERATE, batch_size):
        current_batch = min(batch_size, TOTAL_TO_GENERATE - i)
        tasks = [generate_one(i + j) for j in range(current_batch)]
        results = await asyncio.gather(*tasks)
        success_count += sum(1 for r in results if r)
        print(f"--- 已完成 {i + current_batch} / {TOTAL_TO_GENERATE} ---")
        await asyncio.sleep(1) # 稍微停 1 秒，防止超频报错
    
    print(f"\n✅ 批量生成完毕！成功 {success_count} / {TOTAL_TO_GENERATE} 个。")
    print("请重启后端（uvicorn）以加载新模板。")

if __name__ == "__main__":
    asyncio.run(main())