# -*- coding: utf-8 -*-
"""88b：两门课课程标准封面格式对齐《AI技术应用基础》。

- 标题：《课程名》/课程标准 → 30pt（原 36pt）
- 信息行：黑体 18pt（原 Times New Roman 18pt）
- 课程名更正；删除「编制依据」行（05 无此行）
"""
import glob
import os
import sys

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

ROOT = r"D:/工业互联网应用2026~2027第一学期（前八周）"

CFG = [
    dict(name="程序设计基础", grade="2026级", old_names=["《Python编程基础》", "《程序设计基础》"],
         drop_prefix="编制依据"),
    dict(name="Python程序设计", grade="2025级",
         old_names=["《Python程序设计（项目实战）》", "《Python程序设计》"], drop_prefix=None),
]


def set_run(run, size, ea="黑体", latin="Times New Roman", bold=None):
    run.font.size = Pt(size)
    run.font.name = latin
    if run._element.rPr is None:
        run._element.get_or_add_rPr()
    run._element.rPr.rFonts.set(qn("w:eastAsia"), ea)
    if bold is not None:
        run.font.bold = bold


def main():
    apply = "--apply" in sys.argv
    for c in CFG:
        p = glob.glob(os.path.join(ROOT, c["grade"], "《%s》" % c["name"],
                                   "《%s》-课程标准" % c["name"], "*.docx"))[0]
        d = docx.Document(p)
        log = []

        # 删除「编制依据」行
        if c["drop_prefix"]:
            for par in list(d.paragraphs):
                if par.text.strip().startswith(c["drop_prefix"]):
                    par._element.getparent().remove(par._element)
                    log.append(("删除", par.text.strip()[:40], "—"))
                    break

        # 标题与信息行
        for par in d.paragraphs:
            t = par.text.strip()
            if not t:
                continue
            # 标题（前 2 个非空段）
            if t.startswith("《") and ("课程标准" in t or t in c["old_names"]):
                if t in c["old_names"] and t != "《%s》" % c["name"]:
                    newt = "《%s》" % c["name"]
                    par.runs[0].text = newt
                    for r in par.runs[1:]:
                        r.text = ""
                    log.append(("课程名", t, newt))
                for r in par.runs:
                    if r.font.size and r.font.size.pt != 30:
                        log.append(("标题字号", "%.0fpt" % r.font.size.pt, "30pt"))
                    set_run(r, 30, "黑体", "Times New Roman", False)
                par.alignment = WD_ALIGN_PARAGRAPH.CENTER
                continue
            if t == "课程标准":
                for r in par.runs:
                    set_run(r, 30, "黑体", "Times New Roman", False)
                par.alignment = WD_ALIGN_PARAGRAPH.CENTER
                continue
            # 信息行（部门/制订/负责人/院长/时间）
            if any(t.startswith(k) for k in ("部    门", "制    订", "课程负责人", "二级学院院长", "制订时间")):
                for r in par.runs:
                    if r.font.name != "黑体" or (r.font.size and r.font.size.pt != 18):
                        log.append(("信息行字体", "%s/%.0fpt" % (r.font.name, r.font.size.pt if r.font.size else 0), "黑体18pt"))
                    set_run(r, 18, "黑体", "Times New Roman", None)

        for tag, old, new in log:
            print("  %-10s %-40s → %s" % (tag, old, new))
        print("  %s：%d 处%s" % (c["name"], len(log), "（已保存）" if apply else "（空跑）"))
        if apply:
            try:
                d.save(p)
            except PermissionError:
                print("  [占用] 保存失败，请关闭 WPS 后重试")


if __name__ == "__main__":
    main()
