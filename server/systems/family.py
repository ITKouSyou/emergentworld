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

    # 儿童优先分配给夫妻
    children = [n for n in npcs if n.age < 18 and n.id not in used_ids]
    rng.shuffle(children)
    single_pool = [n for n in npcs
                   if n.id not in used_ids and n.id not in {c.id for c in children}]

    # 每对夫妻至少领 1 个孩子（如果有）
    for m, f in couples:
        if not children:
            break
        # 70% 概率生孩子
        if rng.random() < 0.3:
            continue
        child = children.pop(0)
        child.family.parents = [m.id, f.id]
        m.family.children.append(child.id)
        f.family.children.append(child.id)
        _set_family_baseline(session, m.id, child.id, "parent")
        _set_family_baseline(session, f.id, child.id, "parent")
        used_ids.add(child.id)

    # 剩下的孩子看运气加给夫妻
    for m, f in couples:
        if not children:
            break
        if rng.random() < 0.4:
            child = children.pop(0)
            child.family.parents = [m.id, f.id]
            m.family.children.append(child.id)
            f.family.children.append(child.id)
            _set_family_baseline(session, m.id, child.id, "parent")
            _set_family_baseline(session, f.id, child.id, "parent")
            used_ids.add(child.id)

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
