"""Part 20A - D：修 client/main.gd。"""
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 1. status_label 改为 RichTextLabel
old_status = (
    "\tstatus_label = Label.new()\n"
    "\tstatus_label.text = \"加载中...\"\n"
)
new_status = (
    "\tstatus_label = RichTextLabel.new()\n"
    "\tstatus_label.bbcode_enabled = true\n"
    "\tstatus_label.fit_content = false\n"
    "\tstatus_label.scroll_active = false\n"
    "\tstatus_label.text = \"加载中...\"\n"
)
if old_status in t:
    t = t.replace(old_status, new_status, 1)
    print("[fix] status_label → RichTextLabel")
else:
    print("[skip] status_label 已改过")

# 2. 加 npc_poll_timer
old_poll = (
    "\tmap_poll_timer = Timer.new()\n"
    "\tmap_poll_timer.wait_time = 1.2\n"
    "\tmap_poll_timer.autostart = true\n"
    "\tmap_poll_timer.timeout.connect(func(): api.fetch_map())\n"
    "\tadd_child(map_poll_timer)"
)
new_poll = (
    "\tmap_poll_timer = Timer.new()\n"
    "\tmap_poll_timer.wait_time = 1.2\n"
    "\tmap_poll_timer.autostart = true\n"
    "\tmap_poll_timer.timeout.connect(func(): api.fetch_map())\n"
    "\tadd_child(map_poll_timer)\n"
    "\n"
    "\tvar npc_poll_timer := Timer.new()\n"
    "\tnpc_poll_timer.wait_time = 3.0\n"
    "\tnpc_poll_timer.autostart = true\n"
    "\tnpc_poll_timer.timeout.connect(func():\n"
    "\t\tif player_created:\n"
    "\t\t\tapi.fetch_npcs()\n"
    "\t)\n"
    "\tadd_child(npc_poll_timer)"
)
if old_poll in t:
    t = t.replace(old_poll, new_poll, 1)
    print("[fix] 加 npc_poll_timer")
else:
    print("[skip] npc_poll_timer 已加过")

# 3. NPC 详情加家庭
old_detail = (
    '\tlines.append("")\n'
    '\tlines.append("[b]目标[/b]")\n'
    '\tfor g in data.get("goals", []):\n'
    '\t\tlines.append("   · %s" % str(g))\n'
    '\tnpc_detail.text = "\\n".join(lines)'
)
new_detail = (
    '\tlines.append("")\n'
    '\tlines.append("[b]目标[/b]")\n'
    '\tfor g in data.get("goals", []):\n'
    '\t\tlines.append("   · %s" % str(g))\n'
    '\n'
    '\t# 家庭\n'
    '\tvar fam = data.get("family", {})\n'
    '\tif fam is Dictionary:\n'
    '\t\tvar fam_lines: Array[String] = []\n'
    '\t\tvar sp: String = str(fam.get("spouse_name", ""))\n'
    '\t\tif sp != "":\n'
    '\t\t\tfam_lines.append("   配偶：%s" % sp)\n'
    '\t\tvar ch_arr = fam.get("children_names", [])\n'
    '\t\tif ch_arr != null and ch_arr.size() > 0:\n'
    '\t\t\tvar ch_names: Array[String] = []\n'
    '\t\t\tfor c in ch_arr:\n'
    '\t\t\t\tch_names.append(str(c))\n'
    '\t\t\tfam_lines.append("   子女：%s" % "、".join(ch_names))\n'
    '\t\tvar pa_arr = fam.get("parents_names", [])\n'
    '\t\tif pa_arr != null and pa_arr.size() > 0:\n'
    '\t\t\tvar pa_names: Array[String] = []\n'
    '\t\t\tfor c in pa_arr:\n'
    '\t\t\t\tpa_names.append(str(c))\n'
    '\t\t\tfam_lines.append("   父母：%s" % "、".join(pa_names))\n'
    '\t\tvar si_arr = fam.get("siblings_names", [])\n'
    '\t\tif si_arr != null and si_arr.size() > 0:\n'
    '\t\t\tvar si_names: Array[String] = []\n'
    '\t\t\tfor c in si_arr:\n'
    '\t\t\t\tsi_names.append(str(c))\n'
    '\t\t\tfam_lines.append("   兄弟姐妹：%s" % "、".join(si_names))\n'
    '\t\tif not fam_lines.is_empty():\n'
    '\t\t\tlines.append("")\n'
    '\t\t\tlines.append("[b]家庭[/b]")\n'
    '\t\t\tfor fl in fam_lines:\n'
    '\t\t\t\tlines.append(fl)\n'
    '\n'
    '\tnpc_detail.text = "\\n".join(lines)'
)
if old_detail in t:
    t = t.replace(old_detail, new_detail, 1)
    print("[fix] NPC 详情加家庭")
else:
    print("[skip] NPC 详情已改过")

p.write_text(t, encoding="utf-8", newline="\n")
print("\nD 部分完成。")