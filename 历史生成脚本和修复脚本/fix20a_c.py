"""Part 20A - C：给 server/main.py 的 _npc_to_display 加 family 字段。"""
from pathlib import Path

p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

OLD = (
    'def _npc_to_display(npc: NPC) -> dict:\n'
    '    return {\n'
    '        "id": npc.id, "name": npc.name, "age": npc.age,\n'
    '        "gender": npc.gender,\n'
    '        "gender_label": i18n.gender_label(npc.gender),\n'
    '        "location_id": npc.location_id,\n'
    '        "location_label": i18n.location_label(npc.location_id),\n'
    '        "goals": npc.goals,\n'
    '        "traits": [\n'
    '            {"key": k, "label": i18n.trait_label(k), "value": float(v)}\n'
    '            for k, v in npc.traits.items()\n'
    '        ],\n'
    '        "needs": [\n'
    '            {"key": k, "label": i18n.need_label(k), "value": float(v)}\n'
    '            for k, v in npc.needs.items()\n'
    '        ],\n'
    '    }'
)

NEW = (
    'def _npc_to_display(npc: NPC, npc_names: dict[str, str] | None = None) -> dict:\n'
    '    names = npc_names or {}\n'
    '    fam = npc.family\n'
    '    family_info = {\n'
    '        "spouse_id": fam.spouse,\n'
    '        "spouse_name": names.get(fam.spouse, "") if fam.spouse else "",\n'
    '        "children_ids": list(fam.children),\n'
    '        "children_names": [names.get(c, c) for c in fam.children],\n'
    '        "parents_ids": list(fam.parents),\n'
    '        "parents_names": [names.get(p, p) for p in fam.parents],\n'
    '        "siblings_ids": list(fam.siblings),\n'
    '        "siblings_names": [names.get(s, s) for s in fam.siblings],\n'
    '    }\n'
    '    return {\n'
    '        "id": npc.id, "name": npc.name, "age": npc.age,\n'
    '        "gender": npc.gender,\n'
    '        "gender_label": i18n.gender_label(npc.gender),\n'
    '        "location_id": npc.location_id,\n'
    '        "location_label": i18n.location_label(npc.location_id),\n'
    '        "goals": npc.goals,\n'
    '        "traits": [\n'
    '            {"key": k, "label": i18n.trait_label(k), "value": float(v)}\n'
    '            for k, v in npc.traits.items()\n'
    '        ],\n'
    '        "needs": [\n'
    '            {"key": k, "label": i18n.need_label(k), "value": float(v)}\n'
    '            for k, v in npc.needs.items()\n'
    '        ],\n'
    '        "family": family_info,\n'
    '    }'
)

if OLD not in t:
    print("[skip] 未匹配到 _npc_to_display（可能已改过）")
else:
    t = t.replace(OLD, NEW, 1)

    # 调用方加 npc_names
    t = t.replace(
        '''@app.get("/npc")
def list_npcs() -> list[dict]:
    with get_session() as s:
        return [_npc_to_display(n) for n in load_npcs(s)]''',
        '''@app.get("/npc")
def list_npcs() -> list[dict]:
    with get_session() as s:
        npcs = load_npcs(s)
        names = {n.id: n.name for n in npcs}
        return [_npc_to_display(n, names) for n in npcs]''',
        1,
    )

    t = t.replace(
        '''@app.get("/npc/{npc_id}")
def get_npc(npc_id: str) -> dict:
    with get_session() as s:
        npcs = {n.id: n for n in load_npcs(s)}
        if npc_id not in npcs:
            raise HTTPException(404, "npc not found")
        return _npc_to_display(npcs[npc_id])''',
        '''@app.get("/npc/{npc_id}")
def get_npc(npc_id: str) -> dict:
    with get_session() as s:
        all_npcs = load_npcs(s)
        names = {n.id: n.name for n in all_npcs}
        npcs = {n.id: n for n in all_npcs}
        if npc_id not in npcs:
            raise HTTPException(404, "npc not found")
        return _npc_to_display(npcs[npc_id], names)''',
        1,
    )

    p.write_text(t, encoding="utf-8", newline="\n")
    print("[fix] main.py _npc_to_display 加 family + 更新调用方")