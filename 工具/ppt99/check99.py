# -*- coding: utf-8 -*-
"""inject99 注入后体检：新页形状越界/压页脚 + 页码连续性 + 幂等。"""
import glob
import os
import sys

from pptx import Presentation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join("/Users/joelgong/PycharmProjects/"
                                "ai-course-teaching-resources", "工具", "ppt97"))
from inject99 import slide_title, COURSE_DIRS, ROOT  # noqa: E402

SLIDE_W, SLIDE_H = 13.3333, 7.5
FOOTER_TOP = 7.10
TOL = 0.02


def inches(v):
    return (v or 0) / 914400.0


def main():
    bad = 0
    total_new = 0
    for d in COURSE_DIRS:
        for f in sorted(glob.glob(os.path.join(ROOT, d, "*.pptx"))):
            prs = Presentation(f)
            n = len(prs.slides)
            new_pages = [i + 1 for i, sl in enumerate(prs.slides)
                         if "重难点地图" in slide_title(sl)
                         or "难点逐个击破" in slide_title(sl)
                         or "动手前避坑清单" in slide_title(sl)]
            total_new += len(new_pages)
            errs = []
            if not new_pages:
                errs.append("缺新页")
            for i, sl in enumerate(prs.slides):
                for sh in sl.shapes:
                    if sh.left is None:
                        continue
                    l, t = inches(sh.left), inches(sh.top)
                    r, b = l + inches(sh.width), t + inches(sh.height)
                    if r > SLIDE_W + TOL or b > SLIDE_H + TOL or l < -TOL or t < -TOL:
                        errs.append("p%d 形状越界 (%.2f,%.2f)-(%.2f,%.2f)"
                                    % (i + 1, l, t, r, b))
                    elif 1.5 <= t <= 7.0 and b > FOOTER_TOP + TOL \
                            and inches(sh.height) < 1.0 \
                            and (i + 1) in new_pages:
                        errs.append("p%d 压页脚 b=%.2f" % (i + 1, b))
                # 页码一致性（抽新页）
                if (i + 1) in new_pages:
                    for sh in sl.shapes:
                        if sh.has_text_frame and "/" in sh.text_frame.text:
                            t = sh.text_frame.text.strip()
                            if t.count("/") == 1 and t.split("/")[0].strip().isdigit():
                                if t != "%d / %d" % (i + 1, n):
                                    errs.append("p%d 页码错: %r 应为 %r"
                                                % (i + 1, t, "%d / %d" % (i + 1, n)))
                                break
            tag = os.path.join(d.split("/")[0], os.path.basename(f))
            if errs:
                bad += 1
                print("✗ %s pages=%d new=%s | %s" % (tag, n, new_pages, "; ".join(errs[:3])))
            else:
                print("✓ %s pages=%d 新页=%s" % (tag, n, new_pages))
    print("== 体检完成：异常 deck=%d，共注入新页 %d" % (bad, total_new))


if __name__ == "__main__":
    main()
