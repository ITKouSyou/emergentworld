你是游戏事件模板设计师。根据编年史，设计 1 个新的可复用事件模板。

规则：
- 输出必须是合法 JSON
- 结构必须完全符合以下格式：
  {{"id": "snake_case_id", "tags": ["..."], "cooldown": <int>, "weight": <float 0-2>,
    "conditions": ["..."], "params": {{"participant_count": <int>, "location": "..."}},
    "prompt": "给 LLM 的事件生成提示，2-3 句",
    "evaluator": {{"require": ["..."], "max_reward": <float 0-1>}}}}
- id 必须唯一，不能与已有模板重复
- tags 从 [conflict, social, daily, mystery, trade, survival, plot, investigation, celebration, adventure] 中选
- 不要输出 markdown，不要输出解释

已有模板 ID：{existing_ids}

编年史：
{chronicle}
