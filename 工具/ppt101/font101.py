# -*- coding: utf-8 -*-
"""101号轮 P2-4/P2-5：
F-A 精简 deck 正文区（1.5in<top<7.0in）<9pt 的 run 提升到 9pt；提升后逐 shape 溢出复核，超限则回退该 shape。
F-B 03 精简 deck 模板化冗余后缀压缩：「——应用：见工单starter与教师参考实现」→「（详见分层工单）」等。
输出统计，原件备份 /tmp/backup_ppt101_font。
"""
import glob
import os
import re
import shutil
import sys
import unicodedata

from pptx import Presentation
from pptx.util import Pt

ROOT = "/Users/joelgong/PycharmProjects/ai-course-teaching-resources"
BAK = "/tmp/backup_ppt101_font"
SLIM_DIRS = ["02-程序设计基础/V2授课PPT",
             "03-Python程序设计-项目实战/V2授课PPT",
             "05-AI应用基础48课时版/V2授课PPT"]
REDUNDANT = [
    (re.compile(r"——应用：见工单starter与教师参考实现"), "（详见分层工单）"),
    (re.compile(r"——应用：见工单starter"), "（详见分层工单）"),
]


def wu(s):
    return sum(1.0 if unicodedata.east_asian_width(c) in "WF" else 0.55 for c in s)


def need_height(sh, size_default=12.0):
    w_in = sh.width / 914400.0
    h_in = sh.height / 914400.0
    need = 0.0
    for p in sh.text_frame.paragraphs:
        txt = "".join(r.text for r in p.runs)
        sz = size_default
        for r in p.runs:
            if r.font.size:
                sz = r.font.size.pt
                break
        if w_in <= 0.2:
            return 1e9
        per = max(1.0, w_in / (sz / 72.0 * 0.98))
        lines = max(1, -(-int(wu(txt) + 0.999) // int(per)))
        need += lines * sz * 1.32 / 72.0
    return need - h_in


def bump_fonts(prs):
    bumped = reverted = trimmed = 0
    for sl in prs.slides:
        for sh in sl.shapes:
            if not sh.has_text_frame:
                continue
            top = (sh.top or 0) / 914400.0
            if not (1.5 < top < 7.0):
                continue
            # P2-5 冗余后缀
            t = sh.text_frame.text
            newt = t
            for pat, rep in REDUNDANT:
                newt = pat.sub(rep, newt)
            if newt != t:
                for p in sh.text_frame.paragraphs:
                    for r in p.runs:
                        for pat, rep in REDUNDANT:
                            if pat.search(r.text):
                                r.text = pat.sub(rep, r.text)
                                trimmed += 1
            # P2-4 字号
            small = [r for p in sh.text_frame.paragraphs for r in p.runs
                     if r.font.size and r.font.size.pt < 9.0]
            if not small:
                continue
            old_sizes = [(r, r.font.size.pt) for r in small]
            before = need_height(sh)
            for r, _ in old_sizes:
                r.font.size = Pt(9.0)
            grow = need_height(sh) - before
            if grow > 0.15 and before + grow > 0.1:  # 溢出加剧明显→回退
                for r, sz in old_sizes:
                    r.font.size = Pt(sz)
                reverted += 1
            else:
                bumped += len(old_sizes)
    return bumped, reverted, trimmed


def main():
    os.makedirs(BAK, exist_ok=True)
    tb = tr = tt = 0
    for d in SLIM_DIRS:
        for f in sorted(glob.glob(os.path.join(ROOT, d, "*.pptx"))):
            prs = Presentation(f)
            if len(prs.slides) > 30:
                continue
            bak = os.path.join(BAK, os.path.relpath(f, ROOT).replace(os.sep, "__"))
            if not os.path.exists(bak):
                shutil.copy2(f, bak)
            b, rv, t = bump_fonts(prs)
            if b or rv or t:
                prs.save(f)
            tb += b
            tr += rv
            tt += t
            if b or rv or t:
                print("%-44s 升号%d 回退%d 冗余裁剪%d" % (os.path.basename(f)[:42], b, rv, t))
    print("== 合计：升号 %d 个 run（回退 %d 个 shape），冗余裁剪 %d 处" % (tb, tr, tt))


if __name__ == "__main__":
    main()
