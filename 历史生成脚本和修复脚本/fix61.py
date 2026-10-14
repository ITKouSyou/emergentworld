# 整段重写 generators/event.py
from pathlib import Path

content = '''# 事件生成器：模板 + LLM 填充 + 规则兜底
from __future__ import annotations

import random
import uuid

from server.generators.base import get_llm, load_prompt
from server.i18n import location_label, template_label
from server.models.schemas import Event, EventTemplate, NPC, Player, World


ROLE_ZH = {
    "mother_or_father": "家长",
    "child": "走失的孩子",
    "deceased": "逝者",
    "bride": "新娘",
    "groom": "新郎",
    "lover_a": "当事一方",
    "lover_b": "当事另一方",
    "parent": "父母",
}


def _pick_participants(tpl: EventTemplate, npcs: list[NPC], rng: random.Random) -> list[str]:
    n = int(tpl.params.get("participant_count", 2))
    n = min(n, len(npcs))
    if n <= 0:
        return []
    return [npc.id for npc in rng.sample(npcs, n)]


def _fallback_payload(tpl: EventTemplate, location: str, participants: list[NPC]) -> dict:
    names = "、".join(p.name for p in participants) or "无人"
    loc_zh = location_label(location)
    tpl_zh = template_label(tpl.id)
    return {
        "summary": "在%s发生了%s，涉及%s。" % (loc_zh, tpl_zh, names),
        "narrative": "（LLM 未返回，使用模板兜底。）",
    }


def _roles_text(event_roles: dict, npcs: list[NPC]) -> str:
    if not event_roles:
        return "（无）"
    parts = []
    for role_name, npc_id in event_roles.items():
        p_npc = next((n for n in npcs if n.id == npc_id), None)
        if p_npc is not None:
            role_zh = ROLE_ZH.get(role_name, role_name)
            parts.append("%s：%s" % (role_zh, p_npc.name))
    if not parts:
        return "（无）"
    return "\\n  ".join(parts)


async def fill_event(
    tpl: EventTemplate,
    world: World,
    npcs: list[NPC],
    rng: random.Random,
    player: Player | None = None,
    event_roles: dict | None = None,
) -> Event:
    participants_ids = _pick_participants(tpl, npcs, rng)
    participants = [n for n in npcs if n.id in participants_ids]
    location = tpl.params.get("location", "village_square")

    player_name = "（未创建）"
    player_loc = "（未知）"
    if player is not None and player.created:
        player_name = player.name
        player_loc = location_label(player.location_id)

    roles_text = _roles_text(event_roles or {}, npcs)

    prompt = load_prompt("event_fill.md").format(
        template_id=tpl.id,
        template_label=template_label(tpl.id),
        prompt=tpl.prompt,
        participants=", ".join("%s(%s)" % (p.name, p.id) for p in participants) or "无",
        location=location,
        location_label=location_label(location),
        player_name=player_name,
        player_location=player_loc,
        roles=roles_text,
        day=world.day,
    )
    fallback = _fallback_payload(tpl, location, participants)

    payload = fallback
    try:
        raw = await get_llm().text_json(prompt)
        if isinstance(raw, dict):
            candidate = raw.get("payload") if "payload" in raw else raw
            if isinstance(candidate, dict) and candidate.get("summary"):
                payload = {
                    "summary": str(candidate.get("summary", ""))[:300],
                    "narrative": str(candidate.get("narrative", ""))[:800],
                }
    except Exception:
        payload = fallback

    return Event(
        id="evt_%s" % uuid.uuid4().hex[:8],
        template_id=tpl.id,
        participants=participants_ids,
        location_id=location,
        state="pending",
        payload=payload,
        created_at=world.tick,
    )
'''

p = Path("server/generators/event.py")
p.write_text(content, encoding="utf-8")
print("[fix] generators/event.py 重写完成")
print("行数：%d" % len(content.split(chr(10))))

# 验证 event_fill.md 有 {roles}
p2 = Path("server/prompts/event_fill.md")
t2 = p2.read_text(encoding="utf-8")
if "{roles}" in t2:
    print("[ok] event_fill.md 有 {roles}")
else:
    print("[!] event_fill.md 没有 {roles} —— 不会报错，但角色不会注入叙事")