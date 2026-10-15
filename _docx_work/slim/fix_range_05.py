# -*- coding: utf-8 -*-
"""79号轮·修正 RANGE_MAP 二次替换痕迹

RANGE_MAP 生成的新文本（如"第7周、第10-20周"）又被单周 re.sub 处理，
导致"第7周"被再替换为"第12周"。修正这些位置。
"""
import glob
import os

ROOT = r"D:/Python编程实战/教学实施资料/05-AI应用基础48课时版"
FIX = [
    ("第12周、第10-20周", "第7周、第10-20周"),
    ("第12周、第10-16周", "第7周、第10-16周"),
    ("第12周、第15周", "第7周、第10周"),
    ("第12周、第15-20周", "第7周、第10-20周"),
    ("第12周、第15-16周", "第7周、第10-16周"),
]
os.chdir(ROOT)
tot = 0
for f in glob.glob("*.md") + glob.glob("工单任务书/*.md"):
    s = open(f, encoding="utf-8").read()
    o = s
    n = 0
    for a, b in FIX:
        if a in s:
            n += s.count(a)
            s = s.replace(a, b)
    if s != o:
        open(f, "w", encoding="utf-8", newline="\n").write(s)
        print("  %-40s 修正 %d 处" % (f, n))
        tot += n
print("共修正 %d 处" % tot)
