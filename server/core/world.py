"""世界状态管理。"""

from __future__ import annotations

from sqlmodel import Session, select

from server.models.db import EventRow, NPCRow, WorldRow, dumps, loads
from server.models.schemas import DirectorState, EconomyState, Event, Family, NPC, World


def create_world(world_id: str = "default", seed: int = 42) -> World:
    return World(id=world_id, seed=seed)


def save_world(session: Session, world: World) -> None:
    row = session.get(WorldRow, world.id) or WorldRow(id=world.id)
    row.tick = world.tick
    row.day = world.day
    row.hour = world.hour
    row.seed = world.seed
    row.director_json = dumps(world.director.model_dump())
    row.economy_json = dumps(world.economy.model_dump())
    row.location_ids_json = dumps(world.location_ids)
    row.season = world.season
    row.weather = world.weather
    row.weather_changed_tick = world.weather_changed_tick
    row.last_social_tick = world.last_social_tick
    row.social_count_today = world.social_count_today
    session.add(row)
    session.commit()


def load_world(session: Session, world_id: str = "default") -> World:
    row = session.get(WorldRow, world_id)
    if row is None:
        w = create_world(world_id)
        save_world(session, w)
        return w
    return World(
        id=row.id,
        tick=row.tick,
        day=row.day,
        hour=row.hour,
        seed=row.seed,
        season=row.season or "spring",
        weather=row.weather or "clear",
        weather_changed_tick=row.weather_changed_tick or 0,
        last_social_tick=row.last_social_tick if row.last_social_tick is not None else -999,
        social_count_today=row.social_count_today or 0,
        director=DirectorState(**loads(row.director_json)),
        economy=EconomyState(**loads(row.economy_json)),
        location_ids=loads(row.location_ids_json) or ["village_square"],
    )


def save_npc(session: Session, npc: NPC) -> None:
    row = session.get(NPCRow, npc.id) or NPCRow(id=npc.id, name=npc.name)
    row.name = npc.name
    row.age = npc.age
    row.gender = npc.gender
    row.traits_json = dumps(npc.traits)
    row.needs_json = dumps(npc.needs)
    row.goals_json = dumps(npc.goals)
    row.behavior_json = dumps(npc.behavior_profile)
    row.asset_json = dumps(npc.asset_params)
    row.memory_ids_json = dumps(npc.memory_ids)
    row.location_id = npc.location_id
    row.alive = npc.alive
    row.family_json = dumps(npc.family.model_dump())
    session.add(row)
    session.commit()


def load_npcs(session: Session) -> list[NPC]:
    rows = session.exec(select(NPCRow).where(NPCRow.alive == True)).all()  # noqa: E712
    result: list[NPC] = []
    for r in rows:
        fam_data = loads(r.family_json) or {}
        result.append(NPC(
            id=r.id, name=r.name, age=r.age,
            gender=r.gender or "unknown",
            traits=loads(r.traits_json) or {},
            needs=loads(r.needs_json) or {},
            goals=loads(r.goals_json) or [],
            behavior_profile=loads(r.behavior_json) or {},
            asset_params=loads(r.asset_json) or {},
            memory_ids=loads(r.memory_ids_json) or [],
            location_id=r.location_id,
            alive=r.alive,
            family=Family(**fam_data) if fam_data else Family(),
        ))
    return result


def save_event(session: Session, event: Event) -> None:
    row = session.get(EventRow, event.id) or EventRow(id=event.id, template_id=event.template_id)
    row.template_id = event.template_id
    row.participants_json = dumps(event.participants)
    row.location_id = event.location_id
    row.state = event.state
    row.payload_json = dumps(event.payload)
    row.created_at = event.created_at
    row.resolved_at = event.resolved_at
    session.add(row)
    session.commit()
