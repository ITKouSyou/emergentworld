# 家庭关系：夫妻、子女、兄弟姐妹、父母

from __future__ import annotations

import random

from sqlmodel import Session

from server.models.db import RelationshipRow
from server.models.schemas import NPC
from server.systems import relationship


def _set_kind(session, a: str, b: str, kind: str) -> None:
    rid = relationship._rel_id(a, b)
    row = session.get(RelationshipRow, rid)
    if row is None:
        row = RelationshipRow(id=rid, from_npc=a, to_npc=b)
    row.kind = kind
    session.add(row)
    session.commit()


def _set_family_baseline(session, a: str, b: str, kind: str) -> None:
    if kind == "spouse":
        rel = {"trust": 0.75, "affection": 0.85}
    elif kind == "parent":
        rel = {"trust": 0.7, "affection": 0.75, "debt": 0.3}
    elif kind == "child":
        rel = {"trust": 0.65, "affection": 0.8, "debt": 0.4}
    elif kind == "sibling":
        rel = {"trust": 0.5, "affection": 0.5}
    else:
        rel = {}

    relationship.adjust(session, a, b,
                        trust=rel.get("trust", 0.0),
                        affection=rel.get("affection", 0.0),
                        fear=rel.get("fear", 0.0),
                        debt=rel.get("debt", 0.0))
    relationship.adjust(session, b, a,
                        trust=rel.get("trust", 0.0),
                        affection=rel.get("affection", 0.0),
                        fear=rel.get("fear", 0.0),
                        debt=rel.get("debt", 0.0))
    _set_kind(session, a, b, kind)


def build_families(session, npcs, rng) -> None:
    if len(npcs) < 2:
        return

    adults_male = [n for n in npcs if n.gender == "male" and n.age >= 20]
    adults_female = [n for n in npcs if n.gender == "female" and n.age >= 20]

    rng.shuffle(adults_male)
    rng.shuffle(adults_female)

    couples = []
    for m, f in zip(adults_male, adults_female):
        couples.append((m, f))

    used_ids = set()
    for m, f in couples:
        m.family.spouse = f.id
        f.family.spouse = m.id
        _set_family_baseline(session, m.id, f.id, "spouse")
        used_ids.add(m.id)
        used_ids.add(f.id)

    single_pool = [n for n in npcs if n.id not in used_ids]
    for m, f in couples:
        n_children = rng.choice([0, 0, 1, 1, 2])
        for _ in range(n_children):
            if not single_pool:
                break
            single_pool.sort(key=lambda x: x.age)
            child = single_pool.pop(0)
            if child.age > m.age - 15 or child.age > f.age - 15:
                single_pool.append(child)
                continue
            child.family.parents = [m.id, f.id]
            m.family.children.append(child.id)
            f.family.children.append(child.id)
            _set_family_baseline(session, m.id, child.id, "parent")
            _set_family_baseline(session, f.id, child.id, "parent")

    remaining = [n for n in npcs if not n.family.spouse and not n.family.parents]
    rng.shuffle(remaining)
    while len(remaining) >= 2:
        a = remaining.pop()
        b = remaining.pop()
        if abs(a.age - b.age) > 12:
            remaining.append(b)
            continue
        a.family.siblings.append(b.id)
        b.family.siblings.append(a.id)
        _set_family_baseline(session, a.id, b.id, "sibling")

    from server.core.world import save_npc
    for npc in npcs:
        save_npc(session, npc)
