# 把 client/api.gd 里所有 http.timeout 从 60 改成 180
from pathlib import Path

p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")

n = t.count("http.timeout = 60.0")
t = t.replace("http.timeout = 60.0", "http.timeout = 180.0")
p.write_text(t, encoding="utf-8")
print("[fix] api.gd timeout 60s -> 180s（%d 处）" % n)