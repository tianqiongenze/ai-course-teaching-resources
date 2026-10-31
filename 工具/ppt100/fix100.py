# -*- coding: utf-8 -*-
"""100号轮修复：
F1 05 课「工单完成效果图」页①实测输出块溢出（叠压②③块）——按框高截断重排（11.5pt），
   尾部注明「全文见 output/report.txt」；
F2 两处「关键代码」return 裸片段补函数上下文头（03 W01 p36 / 05 W17 p32）。
幂等：已带「全文逐字见」尾注或已带函数头即跳过。
"""
import copy
import os
import re
import sys
import unicodedata

from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor

ROOT = "/Users/joelgong/PycharmProjects/ai-course-teaching-resources"
BAK = "/tmp/backup_ppt100"
TAIL = "……（全文逐字见 工程化项目/output/report.txt）"


def wu(line):
    return sum(1.0 if unicodedata.east_asian_width(c) in "WF" else 0.55 for c in line)


def fit_paragraphs(text, size_pt, box_w_in, box_h_in):
    """按段落折行累计，超出框高的段落截掉；返回新文本（含尾注）。"""
    per_line = box_w_in / (size_pt / 72.0 * 0.98)
    max_lines = max(4, int(box_h_in * 72.0 / (size_pt * 1.32)))
    used, out = 0, []
    lines_all = text.split("\n")
    for i, p in enumerate(lines_all):
        n = max(1, -(-int(wu(p) + 0.999) // int(per_line)))
        if used + n > max_lines - 1 and i < len(lines_all) - 1:
            remain = len(lines_all) - i
            out.append(TAIL if remain == 1 else "……（后续 %d 行全文逐字见 工程化项目/output/report.txt）" % remain)
            return "\n".join(out), True
        used += n
        out.append(p)
    return "\n".join(out), used > max_lines


def set_text_keep_style(sh, new_text, size_pt):
    """重写文本：沿用首 run 颜色/加粗，统一字号 size_pt。"""
    tf = sh.text_frame
    first_color, first_bold = None, None
    for p in tf.paragraphs:
        for r in p.runs:
            try:
                if r.font.color and r.font.color.type is not None:
                    first_color = r.font.color.rgb
            except Exception:  # noqa: BLE001
                pass
            first_bold = r.font.bold
            break
        if first_color is not None or first_bold is not None:
            break
    tf.clear()
    for i, ln in enumerate(new_text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(size_pt)
        if first_bold is not None:
            r.font.bold = first_bold
        if first_color is not None:
            try:
                r.font.color.rgb = first_color
            except Exception:  # noqa: BLE001
                pass


def backup(path):
    rel = os.path.relpath(path, ROOT).replace(os.sep, "__")
    dst = os.path.join(BAK, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst):
        import shutil
        shutil.copy2(path, dst)


def fix_effect_page(path):
    """F1：① 实测输出块按框截断（05 课全部 deck）。"""
    prs = Presentation(path)
    changed = 0
    for sl in prs.slides:
        title = ""
        for sh in sl.shapes:
            if sh.has_text_frame and sh.text_frame.text.strip():
                title = sh.text_frame.text.strip().split("\n")[0]
                break
        if "工单完成效果图" not in title:
            continue
        for sh in sl.shapes:
            if sh.has_text_frame and "本次真跑实测输出" in sh.text_frame.text:
                if TAIL[:12] in sh.text_frame.text:
                    continue  # 幂等
                new, fitted = fit_paragraphs(sh.text_frame.text, 11.5,
                                            sh.width / 914400.0,
                                            sh.height / 914400.0)
                if fitted:
                    backup(path)
                    set_text_keep_style(sh, new, 11.5)
                else:
                    backup(path)
                    set_text_keep_style(sh, sh.text_frame.text, 11.5)
                changed += 1
    if changed:
        prs.save(path)
    return changed


def fix_code_fragment(path, page_no, head, body_indent_from):
    """F2：给关键代码片段补函数头；块内原有行整体缩进由调用方给定的原文处理。"""
    prs = Presentation(path)
    sl = prs.slides[page_no - 1]
    done = 0
    for sh in sl.shapes:
        if sh.has_text_frame and "return" in sh.text_frame.text \
                and "def " not in sh.text_frame.text:
            t = sh.text_frame.text
            new_lines = [head]
            for ln in t.split("\n"):
                new_lines.append(("    " + ln) if ln.strip() else ln)
            backup(path)
            set_text_keep_style(sh, "\n".join(new_lines), 12.0)
            done = 1
            break
    if done:
        prs.save(path)
    return done


def main():
    import glob
    n1 = 0
    for f in sorted(glob.glob(os.path.join(
            ROOT, "05-AI应用基础48课时版/V2授课PPT/*.pptx"))):
        c = fix_effect_page(f)
        n1 += c
        if c:
            print("F1 +%d  %s" % (c, os.path.basename(f)[:44]))
    print("F1 合计修复页：%d" % n1)
    f03 = os.path.join(ROOT, "03-Python程序设计-项目实战/V2授课PPT",
                       "W01-第1次课-带着C语言底子学Python.pptx")
    n2 = fix_code_fragment(f03, 36, "def read_file(path):", 0)
    print("F2 03 W01 p36 补函数头：", bool(n2))
    f05 = os.path.join(ROOT, "05-AI应用基础48课时版/V2授课PPT",
                       "W17-第17次课-LLM故障诊断（上）：基.pptx")
    n3 = fix_code_fragment(f05, 32, "def ask_with_retry(q):", 0)
    print("F2 05 W17 p32 补函数头：", bool(n3))


if __name__ == "__main__":
    main()
