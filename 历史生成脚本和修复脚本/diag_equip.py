import urllib.request
import json

print("=== /player 返回 ===")
with urllib.request.urlopen("http://127.0.0.1:8000/player") as r:
    data = json.loads(r.read())

print("含 equipment 字段：%s" % ("equipment" in data))
print("含 equipment_slots：%s" % ("equipment_slots" in data))
print("含 total_attributes：%s" % ("total_attributes" in data))
print()
print("equipment:", data.get("equipment"))
print("equipment_slots:", json.dumps(data.get("equipment_slots"), ensure_ascii=False))
print()
print("=== /equipment 端点 ===")
with urllib.request.urlopen("http://127.0.0.1:8000/equipment") as r:
    print(json.dumps(json.loads(r.read()), ensure_ascii=False, indent=2))