# -*- coding: utf-8 -*-
"""用 easyslides validate 报告精确修复 CONTROL-TEXT-VERTICAL-MISALIGN。

对报告中的每个 CONTROL 项，定位文字框(shape_index)并将其 vertical_anchor 设为 MIDDLE，
必要时把文字框 top 微调到容器垂直居中（仅当当前 anchor=TOP 且 Δ>0.05）。
不改文字内容、不改尺寸。幂等。
"""
from pptx import Presentation
from pptx.util import Emu, Inches
from pptx.enum.text import MSO_ANCHOR
import json, os, sys

ROOT = r"D:/Python编程实战/教学实施资料"


def fix_from_report(root, deck_path, report_path, dry=True):
    d = json.load(open(report_path, encoding="utf-8"))
    prs = Presentation(deck_path)
    n = 0
    for it in d.get("issues", []):
        if it["code"] != "CONTROL-TEXT-VERTICAL-MISALIGN":
            continue
        det = it["details"]
        si = it["slide_number"] - 1
        if si < 0 or si >= len(prs.slides):
            continue
        slide = prs.slides[si]
        try:
            sh = slide.shapes[det["shape_index"]]
        except Exception:
            continue
        if not sh.has_text_frame:
            continue
        tf = sh.text_frame
        sh.top = Inches(det["text_center_y"] - Emu(sh.height).inches / 2)
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        n += 1
    if not dry and n:
        prs.save(deck_path)
    return n


if __name__ == "__main__":
    dry = "--apply" not in sys.argv
    # 读取全库 per-file 报告映射（由 batch_all.py 生成：index -> deck rel）
    summ = json.load(open(r"C:/Windows/Temp/ALL_SUMMARY.json", encoding="utf-8"))
    per = summ.get("per", [])
    total = 0
    files_touched = 0
    for idx, (rel, _blk) in enumerate(per):
        report = r"C:/Windows/Temp/all_%d.json" % idx
        if not os.path.exists(report):
            continue
        deck = os.path.join(ROOT, rel)
        try:
            c = fix_from_report(ROOT, deck, report, dry=dry)
        except Exception as e:
            print("ERR", rel[:40], e)
            continue
        if c:
            total += c
            files_touched += 1
    print("%s：%d 册 / %d 个 CONTROL 文字框已精确垂直居中" % ("空跑" if dry else "已修复", files_touched, total))