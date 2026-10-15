# -*- coding: utf-8 -*-
"""76号轮·全库 flake8 汇总（分批，规避命令行过长）"""
import collections
import glob
import os
import re
import subprocess

PY = r"C:/Users/Lenovo/AppData/Local/Temp/audit/env314/Scripts/python.exe"
ROOT = r"D:/Python编程实战/教学实施资料"
PAT = re.compile(r"^(.*?):(\d+):(\d+): ([A-Z]\d+)")

os.chdir(ROOT)
files = [f for f in glob.glob("**/*.py", recursive=True)
         if "_docx_work" not in f and "__pycache__" not in f and "site-packages" not in f]
rows = []
for i in range(0, len(files), 100):
    r = subprocess.run([PY, "-m", "flake8", "--max-line-length=120"] + files[i:i + 100],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    rows += [l for l in r.stdout.splitlines() if l.strip()]

print("=" * 70)
print("全库 flake8（%d 个 .py，max-line-length=120）" % len(files))
print("=" * 70)
print("总问题: %d" % len(rows))
c = collections.Counter()
z = collections.Counter()
for l in rows:
    m = PAT.match(l)
    if not m:
        continue
    code = m.group(4)
    f = m.group(1)
    c[code] += 1
    zone = ("eng" if "工程化项目" in f else
            "starter" if "学生代码框架" in f else
            "teacher" if "教师参考" in f else "other")
    z[(zone, code)] += 1
print("\n按 code:")
for k, v in c.most_common():
    print("   %-6s %d" % (k, v))
print("\n按 区域×code:")
for k, v in sorted(z.items()):
    print("   %-8s %-6s %d" % (k[0], k[1], v))
print("\n明细（前 25）:")
for l in rows[:25]:
    print("   ", l[:112])
