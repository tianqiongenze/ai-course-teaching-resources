# -*- coding: utf-8 -*-
"""85e：目标目录课程名统一为「AI技术应用基础」（与课标/授课计划/教学方案一致）。

覆盖：24 册 PPT（封面 + 全页页脚）、12 个任务单页眉。
仅改目标目录副本，不动 05 源包。
"""
import glob
import os
import sys

import docx
from pptx import Presentation

TGT = r"D:/工业互联网应用2026~2027第一学期（前八周）/2026级/《AI技术应用基础》"
PPT_DIR = os.path.join(TGT, "《AI技术应用基础》-教学PPT")
DOC_DIR = os.path.join(TGT, "《AI技术应用基础》-任务单")

PAIRS = [
    ("AI应用基础（48课时版）", "AI技术应用基础（48课时版）"),
    ("AI应用基础48课时版", "AI技术应用基础48课时版"),
]


def fix_paragraph_runs(par):
    """段落级替换：单 run 命中优先，否则合并到首 run。"""
    n = 0
    for old, new in PAIRS:
        # ① 单 run
        done = False
        for r in par.runs:
            if old in r.text:
                r.text = r.text.replace(old, new)
                n += 1
                done = True
        if done:
            continue
        # ② 跨 run：合并
        if old in par.text and par.runs:
            newtxt = par.text.replace(old, new)
            par.runs[0].text = newtxt
            for r in par.runs[1:]:
                r.text = ""
            n += 1
    return n


def main():
    apply = "--apply" in sys.argv
    total = 0

    # ① PPT
    fs = sorted(f for f in glob.glob(os.path.join(PPT_DIR, "*.pptx"))
                if not os.path.basename(f).startswith("~$"))
    print("### PPT %d 册" % len(fs))
    for f in fs:
        prs = Presentation(f)
        n = 0
        for s in prs.slides:
            for sh in s.shapes:
                if not sh.has_text_frame:
                    continue
                for par in sh.text_frame.paragraphs:
                    n += fix_paragraph_runs(par)
        if n and apply:
            prs.save(f)
        total += n
        print("  %-44s %d 处" % (os.path.basename(f)[:44], n))

    # ② 任务单
    fs = sorted(f for f in glob.glob(os.path.join(DOC_DIR, "*.docx"))
                if not os.path.basename(f).startswith("~$"))
    print("\n### 任务单 %d 个" % len(fs))
    for f in fs:
        d = docx.Document(f)
        n = 0
        for par in d.paragraphs:
            n += fix_paragraph_runs(par)
        for t in d.tables:
            for row in t.rows:
                for c in row.cells:
                    for par in c.paragraphs:
                        n += fix_paragraph_runs(par)
        if n and apply:
            d.save(f)
        total += n
        print("  %-44s %d 处" % (os.path.basename(f)[:44], n))

    print("\n合计 %d 处；%s" % (total, "已写入" if apply else "空跑"))


if __name__ == "__main__":
    main()
