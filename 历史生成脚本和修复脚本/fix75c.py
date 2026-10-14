# 前端：地图上显示季节 + 市场显示季节倍率提示
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 地图上显示季节提示
old = '''	status_label.text = "第 %d 天  %02d:00   %s · %s   Tick %d   张力 %.2f" % ['''
new = '''	status_label.text = "第 %d 天  %02d:00   %s · %s   Tick %d   张力 %.2f" % ['''
# 已经显示季节了，不用改

# 但可以在季节文本加颜色
old2 = '''	var season_zh: String = str(data.get("season_label", ""))
	var weather_zh: String = str(data.get("weather_label", ""))
	status_label.text = "第 %d 天  %02d:00   %s · %s   Tick %d   张力 %.2f" % [
		int(data.get("day", 0)),
		int(data.get("hour", 0)),
		season_zh, weather_zh,
		int(data.get("tick", 0)),
		float(data.get("tension", 0.0)),
	]'''

new2 = '''	var season_zh: String = str(data.get("season_label", ""))
	var weather_zh: String = str(data.get("weather_label", ""))
	var season_key: String = str(data.get("season", "spring"))
	var season_color := "gold"
	if season_key == "summer":
		season_color = "orange"
	elif season_key == "autumn":
		season_color = "chocolate"
	elif season_key == "winter":
		season_color = "lightblue"
	status_label.text = "第 %d 天  %02d:00   [color=%s]%s[/color] · %s   Tick %d   张力 %.2f" % [
		int(data.get("day", 0)),
		int(data.get("hour", 0)),
		season_color, season_zh, weather_zh,
		int(data.get("tick", 0)),
		float(data.get("tension", 0.0)),
	]'''

if old2 in t:
    t = t.replace(old2, new2, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 季节上色")

# 测试
print()
print("C 完成。重启后端 + Godot 完全关闭重开")