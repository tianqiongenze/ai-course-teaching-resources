# -*- coding: utf-8 -*-
"""90：①文件重命名（工业互联网专业→工业互联网应用专业）②02/03 课标首页下划线对齐 05。

下划线规则（对齐《AI技术应用基础》）：
- 信息行「标签：值」中，**标签无下划线，值区（名称/日期/填空）有下划线**
"""
import glob
import os
import re
import sys

from docx.oxml.ns import qn
from docx.shared import Pt

ROOT = r"D:/工业互联网应用2026~2027第一学期（前八周）"

LABELS = ("部    门", "制    订", "课程负责人", "二级学院院长", "制订时间")


def rename_all():
    ok, busy = [], []
    for root, _, files in os.walk(ROOT):
        for fn in files:
            if "工业互联网专业" in fn:
                try:
                    os.rename(os.path.join(root, fn),
                              os.path.join(root, fn.replace("工业互联网专业", "工业互联网应用专业")))
                    ok.append(os.path.join(root, fn.replace("工业互联网专业", "工业互联网应用专业")))
                except PermissionError:
                    busy.append(fn)
    return ok, busy


def set_run_font(run, underline=None):
    run.font.name = "黑体" if underline is None else "黑体"
    run.font.size = Pt(18)
    if run._element.rPr is None:
        run._element.get_or_add_rPr()
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")
    if underline is not None:
        run.font.underline = underline


def fix_underlines(path):
    """对课标首页信息行：标签无下划线、值区下划线。"""
    import docx
    d = docx.Document(path)
    n = 0
    for par in d.paragraphs[:14]:
        t = par.text
        if not any(t.startswith(x) for x in LABELS):
            continue
        m = re.match(r"^([^：:]+[：:])(.*)$", t)
        if not m or not par.runs:
            continue
        label, val = m.group(1), m.group(2)
        # 已符合规则则跳过
        runs = par.runs
        if val and all(r.font.underline for r in runs if r.text.strip() and r.text != label):
            continue
        # 清空除首个外的 run 并删除
        runs[0].text = label
        for r in list(runs[1:]):
            r._element.getparent().remove(r._element)
        set_run_font(runs[0], None)
        if val:
            vr = par.add_run(val)
            set_run_font(vr, True)
        n += 1
    return d, n


def main():
    apply = "--apply" in sys.argv

    # ① 重命名
    ok, busy = rename_all()
    print("重命名：成功 %d 个%s" % (len(ok), "（已处理）" if apply else ""))
    for p in ok:
        print("   ", os.path.basename(p))
    if busy:
        print("占用 %d 个（需关闭 WPS）：" % len(busy))
        for p in busy:
            print("   ", p)

    # ② 下划线（02/03）
    print("\n下划线：")
    for pat in ("2026级/《程序设计基础》/《程序设计基础》-课程标准/*.docx",
                "2025级/《Python程序设计》/《Python程序设计》-课程标准/*.docx"):
        fs = [f for f in glob.glob(os.path.join(ROOT, pat))
              if not os.path.basename(f).startswith("~$")]
        if not fs:
            print("   [未找到] %s" % pat[:40])
            continue
        d, n = fix_underlines(fs[0])
        if apply and n:
            try:
                d.save(fs[0])
                print("   %-30s %d 行已保存" % (os.path.basename(fs[0])[:14], n))
            except PermissionError:
                print("   %-30s 占用，保存失败" % os.path.basename(fs[0])[:14])
        else:
            print("   %-30s %d 行（空跑）" % (os.path.basename(fs[0])[:14], n))


if __name__ == "__main__":
    main()
