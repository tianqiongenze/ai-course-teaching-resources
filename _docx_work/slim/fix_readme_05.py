# -*- coding: utf-8 -*-
"""79号轮·README 表格周次精确修正

· 表1（对照业界12讲，旧周次编号 W4-W9）→ 映射为新编号
· 表2（课程结构，教学周编号 W1-W12）→ 恢复被误改的 W10/W11/W12
"""
import os

ROOT = r"D:/Python编程实战/教学实施资料/05-AI应用基础48课时版"
os.chdir(ROOT)
f = "README.md"
s = open(f, encoding="utf-8").read()
FIX = [
    # 表1：旧周次 → 新周次
    ("W4上·M1-1a开篇", "W7上·M1-1a开篇"),
    ("W4下·M1-1a + W5·M1-1b", "W7下·M1-1a + W10·M1-1b"),
    ("W4·M1-1a全课 + W5·EDA", "W7·M1-1a全课 + W10·EDA"),
    ("W6·M2-1a（LR+DT）+ W7·M2-2", "W11·M2-1a（LR+DT）+ W12·M2-2"),
    ("W6-W8贯通（M2-1a评估+W2-2调参+W2-3a过拟合）",
     "W11-W13贯通（M2-1a评估+M2-2调参+M2-3a过拟合）"),
    ("W9·M2-3b（CNN）+ W15·M3-1", "W14·M2-3b（CNN）+ W15·M3-1"),
    ("W8·M2-3a（MLP）", "W13·M2-3a（MLP）"),
    ("K-Means与无监督聚类（W6）", "K-Means与无监督聚类（W11）"),
    ("MNIST基准（W8）", "MNIST基准（W13）"),
    # 表2：教学周编号 → 恢复被误改
    ("| M4 NLP与大模型应用 | W9-W15 |", "| M4 NLP与大模型应用 | W9-W10 |"),
    ("| M5 多智能体与强化学习 | W16 |", "| M5 多智能体与强化学习 | W11 |"),
    ("| 综合 | W17 | Z |", "| 综合 | W12 | Z |"),
]
n = 0
for a, b in FIX:
    if a in s:
        n += s.count(a)
        s = s.replace(a, b)
    else:
        print("  [MISS]", a[:40])
open(f, "w", encoding="utf-8", newline="\n").write(s)
print("README 修正 %d 处" % n)
