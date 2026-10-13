"""NPC 对话端点：关系上下文 + 语义记忆检索。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.core.world import load_npcs, load_world
from server.db.session import get_session
from server.generators.dialogue import npc_dialogue

router = APIRouter(prefix="/npc", tags=["dialogue"])


class DialogueRequest(BaseModel):
    player_input: str


class DialogueResponse(BaseModel):
    npc_id: str
    npc_name: str
    reply: str
    memories_used: list[str]
    relation_desc: str


@router.post("/{npc_id}/dialogue", response_model=DialogueResponse)
async def dialogue(npc_id: str, req: DialogueRequest) -> DialogueResponse:
    with get_session() as s:
        world = load_world(s)
        npcs = {n.id: n for n in load_npcs(s)}
        if npc_id not in npcs:
            raise HTTPException(404, "npc not found")
        npc = npcs[npc_id]

        result = await npc_dialogue(
            session=s,
            npc=npc,
            player_input=req.player_input,
            world=world,
        )

    return DialogueResponse(
        npc_id=npc.id,
        npc_name=npc.name,
        reply=result["reply"],
        memories_used=result["memories_used"],
        relation_desc=result["relation_desc"],
    )
