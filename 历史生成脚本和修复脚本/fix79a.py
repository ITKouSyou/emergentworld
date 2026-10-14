# Part 79A：20 个新事件模板（日常/经济/情感类）
from pathlib import Path

# 中文标签
NEW_LABELS = {
    "gossip_mill": "磨坊闲话",
    "old_friends_reunion": "老友重逢",
    "neighbor_dispute": "邻里纠纷",
    "child_play": "孩童玩耍",
    "family_dinner": "家宴",
    "well_gathering": "井边闲谈",
    "night_watch": "守夜",
    "debt_collection": "讨债",
    "stolen_goods": "赃物交易",
    "inheritance": "遗产分配",
    "business_partnership": "合伙生意",
    "rare_item_sale": "珍品拍卖",
    "drunk_brawl": "酒后斗殴",
    "theft_accusation": "偷窃指控",
    "animal_attack": "野兽袭击",
    "fire_outbreak": "火灾",
    "secret_love": "暗恋",
    "jealous_husband": "醋意",
    "married_couple_dispute": "夫妻矛盾",
    "return_of_exile": "归乡者",
}

# 写 i18n
p = Path("server/i18n.py")
t = p.read_text(encoding="utf-8")
anchor = '    "explore": "外出探索",\n'
if anchor in t and '"gossip_mill"' not in t:
    addition = ''.join('    "%s": "%s",\n' % (k, v) for k, v in NEW_LABELS.items())
    t = t.replace(anchor, anchor + addition, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] i18n 加 20 个模板标签")
else:
    print("[skip] i18n 已改过")

events_dir = Path("content/templates/events")
events_dir.mkdir(parents=True, exist_ok=True)

FILES = {}

FILES["gossip_mill.yaml"] = '''id: gossip_mill
tags: [social, daily]
cooldown: 5
weight: 1.3
interactive: false
conditions:
  - director.tension < 0.6
params:
  participant_count: 2
  location: village_square
prompt: |
  两个村民在磨坊边闲聊，话题涉及另一位村民的隐私。
  内容应有一丝真实性，但也夹杂夸大与误传。
evaluator:
  require: [rumor_subject, gossip_content]
  max_reward: 0.1
'''

FILES["old_friends_reunion.yaml"] = '''id: old_friends_reunion
tags: [social, romance]
cooldown: 10
weight: 1.0
interactive: true
conditions:
  - director.tension < 0.5
params:
  participant_count: 2
  location: tavern
prompt: |
  两位多年未见的老友在酒馆重逢。其中一人已变了模样。
  重逢勾起旧事，也牵出未了的歉疚。
evaluator:
  require: [friend_a, friend_b, past_event]
  max_reward: 0.2
'''

FILES["neighbor_dispute.yaml"] = '''id: neighbor_dispute
tags: [conflict, daily]
cooldown: 6
weight: 1.2
interactive: true
conditions:
  - director.tension < 0.7
params:
  participant_count: 2
  location: home
prompt: |
  两家邻居因围墙、树荫或家禽起了争执。
  各说各的理，围观者越来越多。
evaluator:
  require: [neighbor_a, neighbor_b, dispute_cause]
  max_reward: 0.15
'''

FILES["child_play.yaml"] = '''id: child_play
tags: [daily, social, celebration]
cooldown: 8
weight: 1.2
interactive: false
conditions:
  - director.tension < 0.6
params:
  participant_count: 2
  location: village_square
prompt: |
  几个孩子在广场玩耍。游戏本身没什么特别，
  但其中一个孩子说的话，让旁边的大人愣了一下。
evaluator:
  require: [children, game, strange_words]
  max_reward: 0.1
'''

FILES["family_dinner.yaml"] = '''id: family_dinner
tags: [social, daily, ritual]
cooldown: 12
weight: 1.0
interactive: false
conditions:
  - director.tension < 0.6
params:
  participant_count: 3
  location: home
prompt: |
  一家人围坐吃饭。饭桌上有说有笑，也暗藏心结。
  席间有人提到一件不宜提起的旧事。
evaluator:
  require: [family, meal_scene, suppressed_topic]
  max_reward: 0.15
'''

FILES["well_gathering.yaml"] = '''id: well_gathering
tags: [social, daily]
cooldown: 5
weight: 1.3
interactive: false
conditions:
  - director.tension < 0.6
params:
  participant_count: 3
  location: village_square
prompt: |
  清晨，几位妇人在井边打水闲聊。
  有人抱怨家务，有人提起远亲的消息。
evaluator:
  require: [gatherers, topic, mood]
  max_reward: 0.1
'''

FILES["night_watch.yaml"] = '''id: night_watch
tags: [survival, daily, plot]
cooldown: 15
weight: 0.9
interactive: false
conditions:
  - director.tension > 0.3
params:
  participant_count: 2
  location: village_edge
prompt: |
  村口有人守夜。长夜里两人断断续续地聊。
  话题从家常一直聊到了村里的旧事。
evaluator:
  require: [watchers, hour, topic]
  max_reward: 0.15
'''

FILES["debt_collection.yaml"] = '''id: debt_collection
tags: [conflict, trade, plot]
cooldown: 10
weight: 1.1
interactive: true
conditions:
  - director.tension < 0.8
params:
  participant_count: 2
  location: market
prompt: |
  债主上门讨债。欠债人一脸难色，说再宽限几日。
  围观的村民议论纷纷，有人出言打圆场。
evaluator:
  require: [creditor, debtor, amount]
  max_reward: 0.3
'''

FILES["stolen_goods.yaml"] = '''id: stolen_goods
tags: [trade, mystery, plot]
cooldown: 12
weight: 1.0
interactive: true
conditions:
  - director.tension < 0.8
params:
  participant_count: 2
  location: tavern
prompt: |
  有人在酒馆悄悄兜售一批来历不明的货物。
  价格低得可疑。买主开始犹豫。
evaluator:
  require: [seller, goods, hint_origin]
  max_reward: 0.25
'''

FILES["inheritance.yaml"] = '''id: inheritance
tags: [plot, conflict, ritual]
cooldown: 20
weight: 0.9
interactive: true
conditions:
  - director.tension > 0.3
params:
  participant_count: 3
  location: village_hall
prompt: |
  一位老人过世，留下遗产。几位晚辈各执一词。
  有人拿出文书，有人声称口头承诺。
evaluator:
  require: [heirs, document, claim]
  max_reward: 0.4
'''

FILES["business_partnership.yaml"] = '''id: business_partnership
tags: [trade, social, plot]
cooldown: 10
weight: 1.0
interactive: true
conditions:
  - director.tension < 0.7
params:
  participant_count: 2
  location: market
prompt: |
  两个商贩商量合伙做一笔生意。出钱出力的比例争执不下。
  生意机会转瞬即逝，两人必须尽快定夺。
evaluator:
  require: [partner_a, partner_b, deal]
  max_reward: 0.3
'''

FILES["rare_item_sale.yaml"] = '''id: rare_item_sale
tags: [trade, mystery, celebration]
cooldown: 15
weight: 1.0
interactive: false
conditions:
  - director.tension < 0.7
params:
  participant_count: 2
  location: market
prompt: |
  一位行商摆出一件稀罕物，请村人围观。
  有识货者一眼认出它的来历，惊得说不出话。
evaluator:
  require: [seller, item, identifier]
  max_reward: 0.3
'''

FILES["drunk_brawl.yaml"] = '''id: drunk_brawl
tags: [conflict, combat, social]
cooldown: 8
weight: 1.0
interactive: true
conditions:
  - director.tension > 0.4
params:
  participant_count: 3
  location: tavern
prompt: |
  酒馆里两桌人喝多了起了冲突。拳脚相向，桌翻椅倒。
  酒保躲在柜台后，旁人纷纷避让。
evaluator:
  require: [brawler_a, brawler_b, cause]
  max_reward: 0.25
'''

FILES["theft_accusation.yaml"] = '''id: theft_accusation
tags: [conflict, investigation, plot]
cooldown: 10
weight: 1.1
interactive: true
conditions:
  - director.tension > 0.3
params:
  participant_count: 3
  location: market
prompt: |
  有人当众指控另一人偷窃。被指的人脸色大变。
  围观者议论纷纷。真相扑朔迷离。
evaluator:
  require: [accuser, accused, item]
  max_reward: 0.3
'''

FILES["animal_attack.yaml"] = '''id: animal_attack
tags: [survival, combat]
cooldown: 12
weight: 1.0
interactive: true
conditions:
  - director.tension > 0.3
params:
  participant_count: 2
  location: forest
prompt: |
  一头受伤的野兽冲出森林，朝最近的村民扑去。
  众人四散奔逃，有人挺身而出。
evaluator:
  require: [beast, defender, outcome]
  max_reward: 0.4
'''

FILES["fire_outbreak.yaml"] = '''id: fire_outbreak
tags: [survival, conflict, plot]
cooldown: 25
weight: 0.8
interactive: true
conditions:
  - director.tension > 0.5
params:
  participant_count: 4
  location: home
prompt: |
  一处民宅突然起火。火势很快蔓延。
  众人提水扑救，也有人趁乱做了什么。
evaluator:
  require: [fire_site, cause, hero]
  max_reward: 0.5
'''

FILES["secret_love.yaml"] = '''id: secret_love
tags: [romance, mystery, daily]
cooldown: 8
weight: 1.1
interactive: false
conditions:
  - director.tension < 0.6
params:
  participant_count: 2
  location: village_square
prompt: |
  有人偷偷把一封折好的信塞进某人门口。
  周围无人看见，但收信人恰好出门，撞了个正着。
evaluator:
  require: [sender, receiver, letter_content]
  max_reward: 0.15
'''

FILES["jealous_husband.yaml"] = '''id: jealous_husband
tags: [romance, conflict, plot]
cooldown: 10
weight: 1.0
interactive: true
conditions:
  - director.tension > 0.3
params:
  participant_count: 3
  location: tavern
prompt: |
  一位丈夫当众质问妻子与某人的关系。
  妻子坚称清白，被牵连的第三人一语不发。
evaluator:
  require: [husband, wife, third_party]
  max_reward: 0.3
'''

FILES["married_couple_dispute.yaml"] = '''id: married_couple_dispute
tags: [social, romance, daily]
cooldown: 6
weight: 1.2
interactive: false
conditions:
  - director.tension < 0.7
params:
  participant_count: 2
  location: home
prompt: |
  一对夫妻在屋里低声争吵，声音越吵越大。
  邻居从墙外能听见只言片语。
evaluator:
  require: [couple, cause, mood]
  max_reward: 0.15
'''

FILES["return_of_exile.yaml"] = '''id: return_of_exile
tags: [plot, mystery, social]
cooldown: 20
weight: 0.9
interactive: true
conditions:
  - director.tension > 0.3
params:
  participant_count: 3
  location: village_square
prompt: |
  一位多年未归的村民回到村里。
  有人欢迎，有人冷脸，还有人眼神躲闪。
evaluator:
  require: [returnee, welcomer, doubtful]
  max_reward: 0.35
'''

for name, content in FILES.items():
    (events_dir / name).write_text(content, encoding="utf-8")
    print("[write] %s" % name)

print()
print("A 完成。共加 %d 个模板。" % len(FILES))