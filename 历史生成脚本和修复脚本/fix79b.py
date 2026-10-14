# Part 79B：12 个新事件模板（神秘/政务/剧情类）
from pathlib import Path

NEW_LABELS = {
    "wandering_orphan": "流浪孤儿",
    "strange_visitor": "怪客",
    "hidden_treasure": "隐藏宝藏",
    "cursed_item": "被诅咒之物",
    "old_ghost_story": "鬼故事",
    "mysterious_letter": "神秘信件",
    "new_law": "新法",
    "tax_collection": "收税",
    "land_dispute": "土地纠纷",
    "village_meeting": "村民大会",
    "prophecy_dream": "预言梦",
    "wandering_monk": "游方僧人",
}

p = Path("server/i18n.py")
t = p.read_text(encoding="utf-8")
anchor = '    "explore": "外出探索",\n'
if anchor in t and '"wandering_orphan"' not in t:
    addition = ''.join('    "%s": "%s",\n' % (k, v) for k, v in NEW_LABELS.items())
    t = t.replace(anchor, anchor + addition, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] i18n 加 12 个模板标签")
else:
    print("[skip] i18n 已改过")

events_dir = Path("content/templates/events")
FILES = {}

FILES["wandering_orphan.yaml"] = '''id: wandering_orphan
tags: [plot, social, mystery]
cooldown: 15
weight: 1.0
interactive: true
conditions:
  - director.tension < 0.6
params:
  participant_count: 2
  location: village_square
prompt: |
  一个衣衫褴褛的孩子在村口张望。
  说是来找人的，但说不出名字。村里有人觉得眼熟。
evaluator:
  require: [orphan, resemblance, claim]
  max_reward: 0.3
'''

FILES["strange_visitor.yaml"] = '''id: strange_visitor
tags: [mystery, plot]
cooldown: 18
weight: 0.9
interactive: false
conditions:
  - director.tension > 0.2
params:
  participant_count: 2
  location: tavern
prompt: |
  一位陌生客人住进酒馆，话少钱多。
  有人注意到他袖口有血迹。
evaluator:
  require: [visitor, clue, suspicion]
  max_reward: 0.25
'''

FILES["hidden_treasure.yaml"] = '''id: hidden_treasure
tags: [adventure, mystery, plot]
cooldown: 20
weight: 0.9
interactive: true
conditions:
  - director.tension < 0.6
params:
  participant_count: 3
  location: old_shrine
prompt: |
  有人在古庙遗址发现一块刻字的石砖。
  文字提到的位置，似乎在村的某处。
evaluator:
  require: [finder, clue_text, location_hint]
  max_reward: 0.4
'''

FILES["cursed_item.yaml"] = '''id: cursed_item
tags: [mystery, survival, plot]
cooldown: 22
weight: 0.8
interactive: true
conditions:
  - director.tension > 0.3
params:
  participant_count: 2
  location: home
prompt: |
  一件物品在村中辗转流传，凡持有者皆遭厄运。
  最近它落到了一位村民手中。
evaluator:
  require: [item, victims, current_owner]
  max_reward: 0.35
'''

FILES["old_ghost_story.yaml"] = '''id: old_ghost_story
tags: [mystery, ritual, daily]
cooldown: 10
weight: 1.0
interactive: false
conditions:
  - director.tension < 0.6
params:
  participant_count: 2
  location: tavern
prompt: |
  酒馆里一位老人讲起几十年前的旧事。
  说到一半，听者中有人脸色变了。
evaluator:
  require: [storyteller, story_theme, listener_reaction]
  max_reward: 0.15
'''

FILES["mysterious_letter.yaml"] = '''id: mysterious_letter
tags: [mystery, plot, investigation]
cooldown: 12
weight: 1.1
interactive: true
conditions:
  - director.tension < 0.6
params:
  participant_count: 2
  location: home
prompt: |
  一封没有署名的信被塞进某户人家门缝。
  信里提到的事情非常具体，像是熟人写的。
evaluator:
  require: [receiver, letter_hint, probable_sender]
  max_reward: 0.25
'''

FILES["new_law.yaml"] = '''id: new_law
tags: [political, plot, social]
cooldown: 25
weight: 0.8
interactive: true
conditions:
  - director.tension > 0.3
params:
  participant_count: 4
  location: village_hall
prompt: |
  村公所颁布了一条新规。
  一部分人受益，一部分人受损。当众有人抗议。
evaluator:
  require: [law_content, supporters, protestors]
  max_reward: 0.35
'''

FILES["tax_collection.yaml"] = '''id: tax_collection
tags: [political, trade, conflict]
cooldown: 20
weight: 0.9
interactive: true
conditions:
  - director.tension > 0.3
params:
  participant_count: 3
  location: market
prompt: |
  收税人来到市场。摊贩们脸色各异。
  有人乖乖交，有人讨价还价，有人干脆收摊。
evaluator:
  require: [collector, taxpayers, resistance]
  max_reward: 0.3
'''

FILES["land_dispute.yaml"] = '''id: land_dispute
tags: [conflict, political, plot]
cooldown: 18
weight: 0.9
interactive: true
conditions:
  - director.tension > 0.2
params:
  participant_count: 3
  location: village_hall
prompt: |
  两家为一块地的归属争执已久。今天终于闹到村公所。
  文书与口头之约相互矛盾。
evaluator:
  require: [party_a, party_b, evidence]
  max_reward: 0.35
'''

FILES["village_meeting.yaml"] = '''id: village_meeting
tags: [political, social, plot]
cooldown: 22
weight: 0.9
interactive: true
conditions:
  - director.tension > 0.3
params:
  participant_count: 5
  location: village_hall
prompt: |
  村里召开大会，商议一件大事。
  众人各抒己见，气氛渐趋紧张。
evaluator:
  require: [agenda, speakers, mood]
  max_reward: 0.35
'''

FILES["prophecy_dream.yaml"] = '''id: prophecy_dream
tags: [mystery, ritual, plot]
cooldown: 20
weight: 0.8
interactive: false
conditions:
  - director.tension > 0.4
params:
  participant_count: 2
  location: home
prompt: |
  一位村民梦见了村子的未来。梦里有一个清楚的景象。
  醒来后他四处告诉人，有人信，有人笑。
evaluator:
  require: [dreamer, dream_image, believers]
  max_reward: 0.2
'''

FILES["wandering_monk.yaml"] = '''id: wandering_monk
tags: [ritual, mystery, social]
cooldown: 20
weight: 0.9
interactive: true
conditions:
  - director.tension < 0.6
params:
  participant_count: 2
  location: village_square
prompt: |
  一位游方僧人来到村庄。他说化缘，也说法。
  有人想听，有人想赶他走。
evaluator:
  require: [monk, sermon_topic, reactions]
  max_reward: 0.3
'''

for name, content in FILES.items():
    (events_dir / name).write_text(content, encoding="utf-8")
    print("[write] %s" % name)

print()
print("B 完成。共加 %d 个模板。" % len(FILES))
print()
print("统计模板总数：")
total = len(list(events_dir.glob("*.yaml")))
print("  %d 个" % total)