# -*- coding: utf-8 -*-
"""77号轮·交互游戏独立册生成器

对四门课 40 个课次，各生成「2 个交互游戏页 + 1 个答案与讲评页」的独立 PPT 册：
  `互动游戏课件/01-AI应用基础-W04-互动游戏.pptx` 等 40 册
外加 1 册总览《互动游戏总览与教师手册.pptx》+ 1 份 Markdown 手册。

页面结构（每册 7 页）：
  1 封面（课次+难点）→ 2 游戏A（题面+选项+教师操作）→ 3 游戏A答案页
  → 4 游戏B → 5 游戏B答案页 → 6 复盘口诀页 → 7 致谢页
游戏页是**静态快问**（PPT内），教师手册提供计分/时间/组织规则。
"""
import copy
import os
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))

from game_data_01 import G01  # noqa: E402
from game_data_02 import G02  # noqa: E402
from game_data_03 import G03  # noqa: E402
from game_data_05 import G05  # noqa: E402

OUT = os.path.join(ROOT, "互动游戏课件")
MANUAL = os.path.join(ROOT, "互动游戏课件", "互动游戏教师手册.md")

# 课程品牌色
BRAND = {
    "01-AI应用基础": RGBColor(0x3D, 0x2E, 0x8C),       # 智造紫
    "02-程序设计基础": RGBColor(0x14, 0x47, 0x7D),      # 深蓝
    "03-Python程序设计-项目实战": RGBColor(0x0B, 0x5E, 0x54),  # 青绿
    "05-AI应用基础48课时版": RGBColor(0x00, 0xA6, 0xA6),  # 蓝绿
}
ACCENT = RGBColor(0xF5, 0x67, 0x0F)   # 智造橙
DARK = RGBColor(0x01, 0x03, 0x28)
GRAY = RGBColor(0x44, 0x54, 0x6A)
LIGHT = RGBColor(0xF1, 0xEF, 0xE8)

TYPE_LABEL = {
    "QUIZ": "课前快问",
    "JUDGE": "举牌判断",
    "MATCH": "连线配对",
    "RUSH": "抢答风暴",
    "SPOT": "火眼找茬",
    "TRY": "动手小实验",
    "RANK": "排序闯关",
    "GUESS": "估算挑战",
}
TYPE_ICON = {
    "QUIZ": "? ", "JUDGE": "✓✗", "MATCH": "↔", "RUSH": "⚡",
    "SPOT": "◎", "TRY": "✎", "RANK": "①②③", "GUESS": "≈",
}


def slide_blank(prs, bg=None):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    if bg is not None:
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = bg
    return s


def add_text(s, l, t, w, h, text, size=14, bold=False, color=DARK, align=PP_ALIGN.LEFT,
             anchor=MSO_ANCHOR.TOP, line_spacing=1.0):
    tb = s.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        run = p.add_run()
        run.text = ln
        f = run.font
        f.size = Pt(size)
        f.bold = bold
        f.color.rgb = color
        f.name = "微软雅黑"
    return tb


def add_box(s, l, t, w, h, fill=LIGHT, line=ACCENT):
    from pptx.enum.shapes import MSO_SHAPE
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.color.rgb = line
    sh.line.width = Pt(1.2)
    return sh


def build_deck(item, course):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    brand = BRAND[course]
    wk, title, diff = item["week"], item["title"], item["diff"]
    g1, g2 = item["games"]

    # ── 封面 ──
    s = slide_blank(prs, LIGHT)
    add_box(s, 0.9, 1.0, 11.5, 1.9, fill=brand, line=brand)
    add_text(s, 1.3, 1.25, 10.8, 0.7, "%s · %s" % (course.split("-")[0], wk), 20, True, RGBColor(0xFF, 0xFF, 0xFF))
    add_text(s, 1.3, 1.95, 10.8, 0.8, "互动游戏课件 · %s" % title, 26, True, RGBColor(0xFF, 0xFF, 0xFF))
    add_text(s, 0.9, 3.2, 11.5, 0.6, "本课重难点：%s" % diff, 18, False, brand)
    add_text(s, 0.9, 4.1, 11.5, 1.8,
             "本册含 2 个课堂互动游戏 + 答案讲评 + 复盘口诀\n\n"
             "教师操作要点见右侧提示（每题标注时间与计分）", 14, False, GRAY)
    add_text(s, 0.9, 6.3, 11.5, 0.5, "配套教师手册：互动游戏教师手册.md ｜ 与工单、工程化项目同一载体：重庆两江智造集团",
             12, False, GRAY)

    def game_page(g, idx):
        s = slide_blank(prs, LIGHT)
        add_box(s, 0.6, 0.5, 12.1, 1.0, fill=brand, line=brand)
        add_text(s, 0.9, 0.65, 9.5, 0.7,
                 "游戏%d · %s %s｜%s" % (idx, TYPE_ICON.get(g["type"], "?"), TYPE_LABEL.get(g["type"], g["type"]), wk),
                 18, True, RGBColor(0xFF, 0xFF, 0xFF))
        add_text(s, 0.9, 1.8, 11.5, 1.4, g["t"], 22, True, DARK)
        add_text(s, 0.9, 3.1, 0.4, 0.4, "选项", 14, True, brand)
        if g.get("opt"):
            for i, o in enumerate(g["opt"]):
                add_text(s, 0.9, 3.5 + i * 0.72, 11.5, 0.6, o, 16, False, DARK)
        else:
            add_text(s, 0.9, 3.5, 11.5, 0.8, "（自由作答：白板/纸面/口头均可）", 16, False, GRAY)
        add_box(s, 0.9, 6.3, 11.5, 0.9, fill=RGBColor(0xFA, 0xEE, 0xDA), line=ACCENT)
        add_text(s, 1.1, 6.4, 11.0, 0.7, "教师操作：%s" % g["teacher"], 13, False, DARK)

    def ans_page(g, idx):
        s = slide_blank(prs, LIGHT)
        add_box(s, 0.6, 0.5, 12.1, 1.0, fill=ACCENT, line=ACCENT)
        add_text(s, 0.9, 0.65, 9.5, 0.7, "游戏%d 答案与讲评" % idx, 18, True, RGBColor(0xFF, 0xFF, 0xFF))
        add_text(s, 0.9, 1.8, 11.5, 0.8, "正确答案：%s" % g["ans"], 20, True, RGBColor(0x99, 0x3C, 0x1D))
        add_box(s, 0.9, 2.8, 11.5, 2.2, fill=RGBColor(0xEA, 0xF3, 0xDE), line=RGBColor(0x3B, 0x6D, 0x11))
        add_text(s, 1.1, 3.0, 11.0, 1.8, "为什么是这个答案\n\n%s" % g["why"], 15, False, DARK)
        add_text(s, 0.9, 5.4, 11.5, 1.2, "评分建议：答对+2分；答错不扣分但需说出理由；思路对一半+1分。",
                 13, False, GRAY)

    game_page(g1, 1)
    ans_page(g1, 1)
    game_page(g2, 2)
    ans_page(g2, 2)

    # ── 复盘口诀 ──
    s = slide_blank(prs, LIGHT)
    add_box(s, 0.6, 0.5, 12.1, 1.0, fill=brand, line=brand)
    add_text(s, 0.9, 0.65, 9.5, 0.7, "复盘口诀｜%s %s" % (wk, title), 18, True, RGBColor(0xFF, 0xFF, 0xFF))
    add_box(s, 0.9, 1.9, 11.5, 3.4, fill=LIGHT, line=brand)
    add_text(s, 1.2, 2.1, 11.0, 3.0,
             "一句话记住本课：\n%s\n\n"
             "课堂节奏建议：\n游戏A（5分钟）→ 精讲 → 游戏B（5分钟）→ 复盘口诀（2分钟）\n"
             "全班计分：小组积分累计到工单评分（游戏加分≤5分，教师自定义）" % diff,
             16, False, DARK)
    # ── 致谢 ──
    s = slide_blank(prs, LIGHT)
    add_text(s, 0.9, 3.0, 11.5, 1.0, "玩中学 · 学中做", 30, True, brand, PP_ALIGN.CENTER)
    add_text(s, 0.9, 4.1, 11.5, 0.6, "重庆两江智造集团 · %s · %s" % (course, wk), 14, False, GRAY, PP_ALIGN.CENTER)

    fname = "%s-%s-互动游戏.pptx" % (course.split("-")[0], wk)
    path = os.path.join(OUT, fname)
    prs.save(path)
    return fname


def build_manual(rows):
    lines = []
    lines.append("# 互动游戏教师手册（77号轮）\n")
    lines.append("> 与《76号报告》配套：40 个课次各 2 个课堂互动游戏，落盘为 40 册独立 PPT + 本手册。\n")
    lines.append("## 一、为什么做交互游戏")
    lines.append("- **教育专家视角**：游戏激活'前测-精讲-后测'闭环，课前快问检测预习、课中游戏突破重难点、课后口诀固化记忆。")
    lines.append("- **教授级高工视角**：每个游戏都指向可验证的工程判断（漏报代价/阈值权衡/门禁决策），不脱离真实业务。\n")
    lines.append("## 二、游戏类型与适用环节")
    lines.append("| 类型 | 玩法 | 建议时长 | 适用环节 |")
    lines.append("|---|---|---|---|")
    for k, v1, v2, v3 in [("QUIZ","举手/手势投票", "2-3分钟", "课前引入·检测预习"),
                          ("JUDGE","举牌表决+辩论", "3-5分钟", "价值观/工程底线讨论"),
                          ("MATCH","连线配对", "2-3分钟", "概念↔含义固化"),
                          ("RUSH","抢答风暴", "3-4分钟", "知识快测·活跃气氛"),
                          ("SPOT","找茬", "3-4分钟", "错误识别·数据素养"),
                          ("TRY","动手小实验", "3-5分钟", "动手验证·结对编程"),
                          ("RANK","排序闯关", "3-4分钟", "流程/依赖关系理解"),
                          ("GUESS","估算挑战", "2-3分钟", "数量级直觉·业务翻译")]:
        lines.append("| %s | %s | %s | %s |" % (k, v1, v2, v3))
    lines.append("\n## 三、计分与课堂组织")
    lines.append("1. 分组：建议 4-6 人一组，设组长记分。")
    lines.append("2. 计分：答对+2、思路对半+1、答错不扣分（鼓励试错）；小组积分可折入工单评分（加分≤5分）。")
    lines.append("3. 节奏：游戏A（课前/课中）→ 精讲 → 游戏B（课中/课后）→ 复盘口诀（2分钟收尾）。")
    lines.append("4. 公平：抢答先举手后发言；举牌/手势全班同步，防止跟风。\n")
    lines.append("## 四、40 课次游戏清单\n")
    lines.append("| 课程 | 课次 | 本课难点 | 游戏1 | 游戏2 |")
    lines.append("|---|---|---|---|---|")
    for r in rows:
        g1, g2 = r["games"]
        lines.append("| %s | %s | %s | %s | %s |" % (
            r["course"].split("-")[0], r["week"], r["diff"],
            TYPE_LABEL.get(g1["type"], g1["type"]), TYPE_LABEL.get(g2["type"], g2["type"])))
    lines.append("\n## 五、与现有资源的关系")
    lines.append("- 游戏页**不替换**现有 163 册课件，而是**独立成册**，教师按需投屏引用。")
    lines.append("- 游戏中的业务情境（泵站/焊缝/YOLO双路线等）与工单、工程化项目**同一载体**：重庆两江智造集团。")
    lines.append("- 答案与讲评页给出'为什么'——可直接用于课末复盘。\n")
    return "\n".join(lines)


def main():
    os.makedirs(OUT, exist_ok=True)
    all_rows = []
    for course, data in [("01-AI应用基础", G01), ("02-程序设计基础", G02),
                          ("03-Python程序设计-项目实战", G03), ("05-AI应用基础48课时版", G05)]:
        for item in data:
            item = dict(item)
            item["course"] = course
            all_rows.append(item)
            fn = build_deck(item, course)
            print("  生成 %s" % fn)
    manual = build_manual(all_rows)
    with open(MANUAL, "w", encoding="utf-8") as f:
        f.write(manual)
    print("=" * 60)
    print("共生成 %d 册互动游戏 PPT + 教师手册" % len(all_rows))
    print("输出目录: %s" % OUT)


if __name__ == "__main__":
    main()
