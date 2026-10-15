# -*- coding: utf-8 -*-
"""76号轮·收尾修复：真正未用的 rng + w02/w12 续行取 27 列"""
import ast
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

# ── ① 仅在「完全不用 rng.」的 core_py 中移除赋值 ──
s = open("specs_01.py", encoding="utf-8").read()
out = s
removed = 0
for m in list(re.finditer(r"core_py='''(.*?)'''", s, re.S)):
    body = m.group(1)
    if "rng." in body:
        continue
    if "rng = np.random.RandomState(seed)" in body:
        nb = body.replace("    rng = np.random.RandomState(seed)\n", "", 1)
        out = out.replace(body, nb, 1)
        removed += 1
if removed:
    ast.parse(out)
    open("specs_01.py", "w", encoding="utf-8", newline="\n").write(out)
print("specs_01: 移除真正未用 rng %d 处" % removed)

# ── ② w02/w12 续行 28 → 27 ──
s = open("specs_02.py", encoding="utf-8").read()
s2 = s.replace(" " * 28 + '"去重抑制 %d 条属预期行为（防刷屏）"',
               " " * 27 + '"去重抑制 %d 条属预期行为（防刷屏）"')
s2 = s2.replace(" " * 28 + "% (len(out) - len(fired))])]",
                " " * 27 + "% (len(out) - len(fired))])]")
s2 = s2.replace(" " * 28 + '"② quarantine.json（隔离区 %d 条）" % len(quarantine),',
                " " * 27 + '"② quarantine.json（隔离区 %d 条）" % len(quarantine),')
s2 = s2.replace(" " * 28 + '"③ result.json（含分级与词频）", "④ report.txt（本报告）"]),',
                " " * 27 + '"③ result.json（含分级与词频）", "④ report.txt（本报告）"]),')
if s2 != s:
    ast.parse(s2)
    open("specs_02.py", "w", encoding="utf-8", newline="\n").write(s2)
    print("specs_02: 续行 28→27 已应用")
else:
    print("specs_02: 无 28 缩行可改")
print("完成")
