# -*- coding: utf-8 -*-
"""87c：为《程序设计基础》《Python程序设计》生成版权与使用说明。"""
import os

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

ROOT = r"D:/工业互联网应用2026~2027第一学期（前八周）"

CFG = [
    dict(name="程序设计基础", grade="2026级", weeks="第1-12周", hours=48, n_gd=12, n_ppt=24,
         weekday="周一", carrier="精密制造事业部", teacher="张建",
         target="工业数据采集与处理程序开发", credit=3),
    dict(name="Python程序设计", grade="2025级", weeks="第1-8周", hours=32, n_gd=9, n_ppt=16,
         weekday="周三", carrier="数字化转型办公室", teacher="宫宇伟、张建",
         target="工业互联网数据工程项目交付", credit=2),
]


def set_font(run, name="仿宋", size=12, bold=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)


def build(c):
    d = docx.Document()
    sec = d.sections[0]
    sec.left_margin = sec.right_margin = Pt(72)
    st = d.styles["Normal"]
    st.font.name = "仿宋"
    st.font.size = Pt(12)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "仿宋")

    for txt, fnt, sz, bd in [
        ("《%s》教学资料" % c["name"], "黑体", 20, True),
        ("版权与使用说明", "黑体", 20, True),
        ("重庆现代制造职业学院 · 智能控制学院", "楷体", 12, False),
    ]:
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_font(p.add_run(txt), fnt, sz, bd)

    total = c["n_gd"] + c["n_ppt"] + 3
    blocks = [
        ("一、资料构成", [
            "本套教学资料包含五个部分，合计 %d 个教学文件（本说明另计）：" % total,
            "1. 课程标准（1 份）：工业互联网专业《%s》课程标准；" % c["name"],
            "2. 授课计划（1 份）：学期教学授课计划表（%s × 4 课时，共 %d 学时）；" % (c["weeks"], c["hours"]),
            "3. 教学设计（1 份）：%s 教学方案（%d 个课次）；" % (c["target"], c["n_gd"] if c["n_gd"] <= 12 else 8),
            "4. 分层工单（%d 份）：各课次 A/B/C/D 四层任务卡；" % c["n_gd"],
            "5. 教学 PPT（%d 册）：各课次「上（基础实现）」「下（优化与评价）」双册。" % c["n_ppt"],
        ]),
        ("二、版权归属", [
            "本套资料的著作权归重庆现代制造职业学院智能控制学院所有，由课程团队（任课教师：%s）"
            "负责编写、修订与维护。" % c["teacher"],
            "资料中使用的第三方开源库（Python 标准库、Pandas、NumPy、Matplotlib、scikit-learn、"
            "Jupyter、Streamlit 等）版权归各自作者所有，遵循其原始开源许可协议。",
        ]),
        ("三、使用许可", [
            "本套资料采用「知识共享 署名-非商业性使用-相同方式共享 4.0 国际许可协议"
            "（CC BY-NC-SA 4.0）」授权：",
            "· 署名：使用时须注明来源「重庆现代制造职业学院 智能控制学院《%s》课程团队」；" % c["name"],
            "· 非商业：不得用于商业培训、商业产品或以营利为目的的二次销售；",
            "· 相同方式共享：基于本资料改编的作品须以相同许可协议发布。",
            "校内教学、兄弟院校教学交流、公开课与教学能力比赛使用，均视为许可范围内使用。",
        ]),
        ("四、载体与数据说明", [
            "1. 课程统一采用虚构教学载体「重庆两江智造集团」（本课程对应%s），"
            "企业名称、组织架构、人物与剧情均为教学虚构，与任何真实企业、真实人员无关。" % c["carrier"],
            "2. 实训数据为程序生成的合成数据或经脱敏处理的教学样例，不含真实企业生产数据、"
            "不含个人隐私信息。",
            "3. 资料中涉及的工艺参数、成本数字、指标阈值均为教学设定值，不作为工程实施依据。",
        ]),
        ("五、引用与转载", [
            "引用本资料片段用于论文、报告、公开课或竞赛时，建议标注格式：",
            "「重庆现代制造职业学院智能控制学院. 《%s》教学资料[Z]. 2026.」" % c["name"],
            "如需整册转载或改编发布，请先与课程团队联系确认，并在显著位置保留本说明。",
        ]),
        ("六、质量与反馈", [
            "本套资料按「课程标准—授课计划—教学方案—分层工单—教学 PPT」四层一致性校验后发布，"
            "课次周次、课时（每次 4 课时 160 分钟＝上/下 2 次课各 80 分钟，1 班%s1~4 节 / 2 班 5~8 节）、"
            "考核口径（工单 40%% + 课堂表现 10%% + 小组项目 30%% + 期末 20%%）跨文件一致。" % c["weekday"],
            "使用中发现错漏，欢迎反馈至课程团队，我们将在下一版修订中更新。",
        ]),
    ]

    for title, lines in blocks:
        p = d.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        set_font(p.add_run(title), "黑体", 14, True, RGBColor(0x1F, 0x3B, 0x73))
        for ln in lines:
            p = d.add_paragraph()
            p.paragraph_format.first_line_indent = Pt(24)
            p.paragraph_format.space_after = Pt(2)
            set_font(p.add_run(ln), "仿宋", 12)

    for txt in ("", "重庆现代制造职业学院  智能控制学院",
                "《%s》课程团队" % c["name"], "2026 年 10 月"):
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        set_font(p.add_run(txt), "仿宋", 12)

    out = os.path.join(ROOT, c["grade"], "《%s》" % c["name"],
                       "《%s》-版权与使用说明.docx" % c["name"])
    d.save(out)
    print("  已生成:", out.split("/")[-2] + "/" + os.path.basename(out))


if __name__ == "__main__":
    for c in CFG:
        build(c)
