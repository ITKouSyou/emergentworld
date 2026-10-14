# 直接调后端 /resolve 看 FastAPI 返回的具体错误
import urllib.request
import json

event_id = "evt_bc8bf72d"
url = "http://127.0.0.1:8000/event/%s/resolve" % event_id
body = json.dumps({"choice_id": "help"}).encode("utf-8")

req = urllib.request.Request(
    url,
    data=body,
    method="POST",
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
    },
)

print("请求 URL：%s" % url)
print("请求 body：%s" % body.decode())
print()

try:
    with urllib.request.urlopen(req) as resp:
        print("HTTP %d" % resp.status)
        print(resp.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print("HTTP %d" % e.code)
    print("响应体：")
    print(e.read().decode("utf-8"))
except Exception as e:
    print("异常：%s: %s" % (type(e).__name__, e))