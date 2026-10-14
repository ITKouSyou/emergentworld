# 前端超时 60s → 180s
from pathlib import Path

p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")

n = t.count("http.timeout = 60.0")
t = t.replace("http.timeout = 60.0", "http.timeout = 180.0")
p.write_text(t, encoding="utf-8")
print("[fix] api.gd timeout 60 → 180（%d 处）" % n)