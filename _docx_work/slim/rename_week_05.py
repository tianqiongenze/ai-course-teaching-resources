# -*- coding: utf-8 -*-
"""79号轮·05包周次统一：文件名重命名

旧学期周 → 新学期周（教学周 k：k=1→第7周；k≥2→第(k+8)周）
  W04→W07  W05→W10  W06→W11  W07→W12  W08→W13  W09→W14
  W10→W15  W11→W16  W12→W17  W13→W18  W14→W19  W15→W20
两步重命名（先临时名）避免覆盖冲突。
"""
import glob
import os
import re

ROOT = r"D:/Python编程实战/教学实施资料/05-AI应用基础48课时版"
MAP = {"04": "07", "05": "10", "06": "11", "07": "12", "08": "13", "09": "14",
       "10": "15", "11": "16", "12": "17", "13": "18", "14": "19", "15": "20"}
DIRS = ["V1授课PPT", "微课视频", "分层工单"]
PAT = re.compile(r"^W(\d{2})(.*)$")

os.chdir(ROOT)
total = 0
for d in DIRS:
    if not os.path.isdir(d):
        print("  跳过（无目录）:", d)
        continue
    files = [f for f in os.listdir(d) if not f.startswith("~$")]
    plan = []
    for f in files:
        m = PAT.match(f)
        if m and m.group(1) in MAP:
            plan.append((f, "W%s%s" % (MAP[m.group(1)], m.group(2))))
    # 第一步：改临时名
    tmp = []
    for old, new in plan:
        t = os.path.join(d, "__tmp__" + new)
        os.rename(os.path.join(d, old), t)
        tmp.append((t, new))
    # 第二步：改目标名
    for t, new in tmp:
        os.rename(t, os.path.join(d, new))
    total += len(plan)
    print("  %-12s 重命名 %d 个" % (d, len(plan)))
print("共重命名 %d 个文件" % total)
