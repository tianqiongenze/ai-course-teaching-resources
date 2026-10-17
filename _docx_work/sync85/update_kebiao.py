# -*- coding: utf-8 -*-
"""84号轮：更新《AI技术应用基础》课程标准至 05 最新口径。

- 开课时间：第1-12周 → 第7周起（跳过第8、9周）·第10-20周·每周五4课时
- 模块周次：教学周 1-12 → 实际学期周 7/10/11…20
- 学习评价：改为 平时工单40% + 课堂表现10% + 小组项目30% + 期末20%
- 正文教学周表述去歧义（W1-4 → 第1-4次课）
"""
import os
import sys

import docx

DOC = (r"D:/工业互联网应用2026~2027第一学期（前八周）/2026级/《AI技术应用基础》"
       r"/《AI技术应用基础》-课程标准/工业互联网专业《AI技术应用基础》课程标准.docx")

# 段落级替换（原文 → 新文）
PARA_FIX = [
    ("递进设计：初级（W1-4夯实ML）→中级（W5-8深度与视觉）→高级（W9-12大模型与智能体）",
     "递进设计：初级（第1-4次课夯实ML）→中级（第5-8次课深度与视觉）→高级（第9-12次课大模型与智能体）"),
    ("案例映射：W4工时账→职业操守；W9脱敏红线→数据伦理；W11奖励漏洞→制度设计者的责任",
     "案例映射：第4次课工时账→职业操守；第9次课脱敏红线→数据伦理；第11次课奖励漏洞→制度设计者的责任"),
    ("过程性评价80%：周工单50%+代码审查20%+学习投入10%",
     "过程性评价80%：平时工单40%（10次工单×4分：正确性+规范+留痕）+课堂表现10%（出勤·参与·互动游戏·答问）+小组项目30%（期末项目册20选1：代码+README+答辩）"),
    ("期末20%：第12周综合项目答辩",
     "期末20%：第20周统一组织期末考试（综合项目答辩并入小组项目考核）"),
    ("每周24小时内反馈，第6周中期诊断",
     "每周24小时内反馈；第14周（教学周第6周）中期诊断"),
]

# 表3 周次·学时（R1..R6 第2列）
MODULE_WEEKS = [
    "第7、10周·8课时",
    "第11-14周·16课时",
    "第15-16周·8课时",
    "第17-18周·8课时",
    "第19周·8课时",
    "第20周·4课时",
]


def set_cell_text(cell, new_text):
    paras = cell.paragraphs
    first = paras[0]
    if not first.runs:
        first.add_run("")
    first.runs[0].text = new_text
    for r in first.runs[1:]:
        r.text = ""
    for p in paras[1:]:
        for r in p.runs:
            r.text = ""


def para_replace(par, old, new):
    txt = par.text
    if old not in txt:
        return 0
    for r in par.runs:
        if old in r.text:
            r.text = r.text.replace(old, new)
            return 1
    if not par.runs:
        return 0
    par.runs[0].text = txt.replace(old, new)
    for r in par.runs[1:]:
        r.text = ""
    return 1


def main():
    apply = "--apply" in sys.argv
    d = docx.Document(DOC)
    n = 0

    # ① 正文段落
    for par in d.paragraphs:
        for old, new in PARA_FIX:
            if old in par.text:
                n += para_replace(par, old, new)
                print("  [段落] %s → %s" % (old[:36], new[:46]))

    # ② 表0 开课时间
    t0 = d.tables[0]
    for row in t0.rows:
        for c in row.cells:
            if "第1-12周" in c.text:
                set_cell_text(c, "第7周起（跳过第8、9周）·第10-20周·每周五4课时（12周×4课时，扩展班）")
                n += 1
                print("  [表0] 开课时间 → 第7周起（跳过第8、9周）·第10-20周·每周五4课时")

    # ③ 表3 周次·学时
    t3 = d.tables[3]
    for i, newv in enumerate(MODULE_WEEKS):
        ri = 1 + i
        cell = t3.rows[ri].cells[1]
        old = cell.text.strip()
        if old != newv:
            set_cell_text(cell, newv)
            n += 1
            print("  [表3 R%d] %s → %s" % (ri, old, newv))

    print("\n合计 %d 处；%s" % (n, "已写入" if apply else "空跑"))
    if apply:
        d.save(DOC)
        print("已保存:", os.path.basename(DOC))


if __name__ == "__main__":
    main()
