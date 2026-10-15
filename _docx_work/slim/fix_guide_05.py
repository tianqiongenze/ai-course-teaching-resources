# -*- coding: utf-8 -*-
"""79号轮·软件指南周次修正（统一为学期周口径）"""
import os

ROOT = r"D:/Python编程实战/教学实施资料/05-AI应用基础48课时版"
os.chdir(ROOT)
f = "课程软件与环境配置完全指南.md"
s = open(f, encoding="utf-8").read()
FIX = [
    # 小节标题（旧周次 → 学期周）
    ("### W4（学期第7周）数据清洗", "### W7（教学周1）数据清洗"),
    ("### W5 特征设计", "### W10（教学周2）特征设计"),
    ("确认W4包已装", "确认W7包已装"),
    ("### W6 传统分类", "### W11（教学周3）传统分类"),
    ("### W7 XGBoost调优", "### W12（教学周4）XGBoost调优"),
    ("### W8 MLP神经网络", "### W13（教学周5）MLP神经网络"),
    ("### W9 CNN/LSTM竞标", "### W14（教学周6）CNN/LSTM竞标"),
    # 软件表
    ("| 运行时 | W1 | Anaconda自带 |", "| 运行时 | W7 | Anaconda自带 |"),
    ("| 编码与`Jupyter实训/` | W1 | notebook含W5/W20专属4个 |",
     "| 编码与`Jupyter实训/` | W7 | notebook含W13/W20专属4个 |"),
    ("| M1全程+评估 | W1 | numpy保持<2（见排查表） |",
     "| M1全程+评估 | W7 | numpy保持<2（见排查表） |"),
    ("| W4限时调优 | W4 | pip；CPU即可 |", "| W12限时调优 | W12 | pip；CPU即可 |"),
    ("| W5 MLP/W6 CNN | W5 |", "| W13 MLP/W14 CNN | W13 |"),
    ("| W7 ResNet预训练权重 | W7 |", "| W15 ResNet预训练权重 | W15 |"),
    ("| W8 YOLO | W8 |", "| W16 YOLO | W16 |"),
    ("| W9 LLM调用 | W9 |", "| W17 LLM调用 | W17 |"),
    ("| 检索词扩展（选做） | W19 | pip |", "| 检索词扩展（选做） | W18 | pip |"),
]
n = 0
for a, b in FIX:
    if a in s:
        n += s.count(a)
        s = s.replace(a, b)
    else:
        print("  [MISS]", a[:46])
open(f, "w", encoding="utf-8", newline="\n").write(s)
print("软件指南修正 %d 处" % n)
