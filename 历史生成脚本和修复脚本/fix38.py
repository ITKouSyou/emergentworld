# 1. 放宽事件条件
# 2. 修 seed_world：生成不同年龄层，让家庭有子女
from pathlib import Path

# ============================================================
# 1. event_flow.py：放宽条件
# ============================================================
p = Path("server/core/event_flow.py")
t = p.read_text(encoding="utf-8")

old = '''TEMPLATE_REQUIRES = {
    "lost_child": "has_children",
    "romance_blooms": "no_spouse",
    "lovers_quarrel": "has_spouse",
    "wedding": "no_spouse",
    "broken_promise": "has_family",
    "funeral": "has_family",
    "birth_of_child": "has_spouse",
}'''

new = '''TEMPLATE_REQUIRES = {
    "lost_child": "has_spouse",
    "romance_blooms": "no_spouse",
    "lovers_quarrel": "has_spouse",
    "wedding": "no_spouse",
    "broken_promise": "has_family",
    "funeral": "has_family",
    "birth_of_child": "has_spouse",
}'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] event_flow lost_child 放宽到 has_spouse")
else:
    print("[skip] event_flow 已改过")

# ============================================================
# 2. seed_world.py：生成多个年龄段
# ============================================================
p = Path("tools/seed_world.py")
t = p.read_text(encoding="utf-8")

# 加儿童名池
if "CHILD_NAMES" not in t:
    anchor = 'FEMALE_NAMES = ['
    addition = '''CHILD_NAMES = [
    "小石头", "铁蛋", "栓子", "狗剩", "阿牛",
    "丫丫", "招娣", "小翠", "阿香", "杏儿",
]

FEMALE_NAMES = ['''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        print("[fix] seed_world 加 CHILD_NAMES")
    else:
        print("[fail] seed_world 锚点未找到")

# 替换 seed() 里的逻辑
old_seed_body = '''        picks = pick_name_pool(n, rng)
        npcs = []
        for name, gender in picks:
            npc = await generate_npc(name, context="一个偏远村庄", gender=gender)
            save_npc(session, npc)
            npcs.append(npc)
            print("created npc %s %s (%s)" % (npc.id, npc.name, npc.gender))

        build_families(session, npcs, rng)'''

new_seed_body = '''        picks = pick_name_pool(n, rng)
        npcs = []

        # 成年人（约 70%）
        n_adults = max(4, int(n * 0.7))
        adult_picks = picks[:n_adults]
        # 儿童（约 30%）
        n_children = n - n_adults

        for name, gender in adult_picks:
            npc = await generate_npc(name, context="一个偏远村庄", gender=gender)
            save_npc(session, npc)
            npcs.append(npc)
            print("created adult %s %s (%s, age=%d)" % (
                npc.id, npc.name, npc.gender, npc.age))

        # 儿童：从 CHILD_NAMES 取
        child_pool = list(CHILD_NAMES)
        rng.shuffle(child_pool)
        for i in range(min(n_children, len(child_pool))):
            cname = child_pool[i]
            cgender = "male" if i % 2 == 0 else "female"
            npc = await generate_npc(cname, context="村里的孩子", gender=cgender)
            # 强制年龄段
            npc.age = rng.randint(7, 15)
            save_npc(session, npc)
            npcs.append(npc)
            print("created child %s %s (age=%d)" % (npc.id, npc.name, npc.age))

        build_families(session, npcs, rng)'''

if old_seed_body in t:
    t = t.replace(old_seed_body, new_seed_body, 1)
    print("[fix] seed_world 生成儿童")
else:
    print("[skip] seed_world 主循环已改过或未匹配")

p.write_text(t, encoding="utf-8")

# ============================================================
# 3. family.py：把儿童优先配成夫妻的子女
# ============================================================
p = Path("server/systems/family.py")
t = p.read_text(encoding="utf-8")

old_child = '''    single_pool = [n for n in npcs if n.id not in used_ids]
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
            _set_family_baseline(session, f.id, child.id, "parent")'''

new_child = '''    # 儿童优先分配给夫妻
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
            used_ids.add(child.id)'''

if old_child in t:
    t = t.replace(old_child, new_child, 1)
    print("[fix] family.py 儿童优先配夫妻")
else:
    print("[skip] family.py 已改过或未匹配")

p.write_text(t, encoding="utf-8")

print()
print("=========== 完成 ===========")
print("方式 A（快速）：重启后端，直接玩 —— lost_child 只要参与者有配偶就行")
print("方式 B（彻底）：清库 + seed + 重启 —— 有真正的家庭结构")
print()
print("方式 B 命令：")
print("  Remove-Item data\\world.db")
print("  python tools\\seed_world.py --npc 14")
print("  uvicorn server.main:app --reload")
print()
print("方式 A 命令：")
print("  uvicorn server.main:app --reload")