# -*- coding: utf-8 -*-
"""101号轮 P1-3 v2：动态发现 >900 字高负荷页并按类型拆分。

类型1「工单实战·本次实跑结果」（四档实测页）：D+C 留原页，B/A+出处放克隆页。
类型2「工单完成效果图」：①实测输出留原页，②③④放克隆页（标题加「· 自检与提交续」）。
页码动态扫描（不受 99/101 轮插页影响）。幂等：已含「档续」标记即跳过该 deck。
"""
import glob
import os
import shutil
import sys

from pptx import Presentation

ROOT = "/Users/joelgong/PycharmProjects/ai-course-teaching-resources"
sys.path.insert(0, os.path.join(ROOT, "工具", "ppt97"))
sys.path.insert(0, os.path.join(ROOT, "工具", "ppt99"))
sys.path.insert(0, os.path.join(ROOT, "03-Python程序设计-项目实战", "工具"))
from inject99 import slide_title, clone_base, _reorder  # noqa: E402
from ppt_enrich import _renumber_slide_num, set_shape_text  # noqa: E402

BAK = "/tmp/backup_ppt101_split"
DIRS = ["01-AI应用基础/授课PPT",
        "02-程序设计基础/V2授课PPT",
        "03-Python程序设计-项目实战/V2授课PPT",
        "05-AI应用基础48课时版/V2授课PPT"]


def page_chars(sl):
    return sum(len(sh.text_frame.text) for sh in sl.shapes if sh.has_text_frame)


def find_cut(sl):
    """动态切点：B 档头（'B' 字母或以'优秀'开头的形状）top - 0.12；找不到退回 4.0。"""
    cut = 4.0
    for sh in sl.shapes:
        if not sh.has_text_frame:
            continue
        t = sh.text_frame.text.strip()
        if t == "B" or t.startswith("优秀") or t.startswith("超优"):
            top = (sh.top or 0) / 914400.0
            if top < cut:
                cut = top
    return max(1.6, cut - 0.12)


def band_run(top_in, cut):
    if top_in < 1.55:
        return "hdr"
    if top_in < cut:
        return "DC"
    if top_in < 5.95:
        return "BA"
    if top_in < 7.0:
        return "src"
    return "ftr"


def band_eff(top_in):
    if top_in < 2.0:
        return "hdr"
    if top_in < 4.7:
        return "b1"
    return "rest"


def split_deck(path):
    prs = Presentation(path)
    if any("档续" in slide_title(sl) for sl in prs.slides):
        return []
    done = []
    i = 0
    while i < len(prs.slides):
        sl = prs.slides[i]
        st = slide_title(sl)
        ch = page_chars(sl)
        if ch <= 900:
            i += 1
            continue
        bak = os.path.join(BAK, os.path.relpath(path, ROOT).replace(os.sep, "__"))
        os.makedirs(os.path.dirname(bak), exist_ok=True)
        if not os.path.exists(bak):
            shutil.copy2(path, bak)
        if "实跑结果" in st or "工单实战" in st:
            cut = find_cut(sl)
            cl = clone_base(prs, i)
            for sh in list(sl.shapes):
                if band_run((sh.top or 0) / 914400.0, cut) in ("BA", "src"):
                    sh._element.getparent().remove(sh._element)
            for sh in list(cl.shapes):
                if band_run((sh.top or 0) / 914400.0, cut) == "DC":
                    sh._element.getparent().remove(sh._element)
            for sh in cl.shapes:
                if sh.has_text_frame and "REAL RUN" in sh.text_frame.text:
                    set_shape_text(sh, "REAL RUN · B/A 档续",
                                   keep_size=True)
                    break
            _reorder(prs, 1, i)
            _renumber_slide_num(prs)
            done.append("p%d 四档拆分 D+C|B+A (cut=%.2f)" % (i + 1, cut))
            i += 2
        elif "工单完成效果图" in st:
            cl = clone_base(prs, i)
            for sh in list(sl.shapes):
                if band_eff((sh.top or 0) / 914400.0) == "rest":
                    sh._element.getparent().remove(sh._element)
            for sh in list(cl.shapes):
                if band_eff((sh.top or 0) / 914400.0) == "b1":
                    sh._element.getparent().remove(sh._element)
            tset = False
            for sh in cl.shapes:
                if sh.has_text_frame and sh.top is not None \
                        and sh.top / 914400.0 < 1.3 \
                        and "工单完成效果图" in sh.text_frame.text:
                    set_shape_text(sh, "工单完成效果图 · 自检与提交（承接上页实测输出）",
                                   keep_size=True)
                    tset = True
                    break
            if not tset:
                for sh in cl.shapes:
                    if sh.has_text_frame and "工单完成效果图" in sh.text_frame.text:
                        set_shape_text(sh, "工单完成效果图 · 自检与提交（承接上页实测输出）",
                                       keep_size=True)
                        break
            _reorder(prs, 1, i)
            _renumber_slide_num(prs)
            done.append("p%d 效果图拆分 ①|②③④" % (i + 1))
            i += 2
        else:
            done.append("p%d %d字 未拆（类型未识别：%s）" % (i + 1, ch, st[:16]))
            i += 1
    if done:
        prs.save(path)
    return done


def main():
    for d in DIRS:
        for f in sorted(glob.glob(os.path.join(ROOT, d, "*.pptx"))):
            for r in split_deck(f):
                print("%-44s %s" % (os.path.basename(f)[:42], r))


if __name__ == "__main__":
    main()
