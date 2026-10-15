# -*- coding: utf-8 -*-
"""easyslides 门禁驱动修复：CONTROL-TEXT-VERTICAL-MISALIGN

把"实心色块容器内部的短标签文字框(≤8字)"垂直居中(MSO_ANCHOR.MIDDLE)。
结构：容器色块(无文本,有fill) + 内部文字框(anchor=TOP)。只设居中，不改内容。
与 easyslides 判定一致：文字中心 vs 容器中心差 >0.05in。
"""
from pptx import Presentation
from pptx.util import Emu
from pptx.enum.text import MSO_ANCHOR
import glob, os

ROOT = r"D:/Python编程实战/教学实施资料"


def rect(sh):
    l, t, w, h = (Emu(sh.left).inches, Emu(sh.top).inches,
                  Emu(sh.width).inches, Emu(sh.height).inches)
    return l, t, w, h


def is_solid_plate(sh):
    try:
        return sh.fill.type == 1  # solid
    except Exception:
        return False


def inside(txt_rect, plate_rect, pad=0.0):
    tl, tt, tw, th = txt_rect
    pl, pt, pw, ph = plate_rect
    return (pl - pad <= tl and pt - pad <= tt and
            tl + tw <= pl + pw + pad and tt + th <= pt + ph + pad)


def fix_file(path, dry=True):
    prs = Presentation(path)
    n = 0
    for s in prs.slides:
        shapes = list(s.shapes)
        text_shapes = [(i, sh) for i, sh in enumerate(shapes) if sh.has_text_frame]
        for i, sh in text_shapes:
            tf = sh.text_frame
            txt = tf.text.strip()
            if not txt or tf.vertical_anchor == MSO_ANCHOR.MIDDLE:
                continue
            if len(txt) > 8:          # 只处理短 label
                continue
            tr = rect(sh)
            H = tr[3]
            if not (0.15 < H < 1.5):  # label 高度
                continue
            # 找包含它的实心色块
            for j, plate in enumerate(shapes):
                if i == j or not is_solid_plate(plate):
                    continue
                pr_ = rect(plate)
                if inside(tr, pr_, pad=0.02) and pr_[2] >= 0.4 and pr_[3] >= 0.4:
                    if abs((tr[1] + H / 2) - (pr_[1] + pr_[3] / 2)) > 0.04:
                        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
                        n += 1
                    break
    if not dry and n:
        prs.save(path)
    return n


if __name__ == "__main__":
    import sys
    dry = "--apply" not in sys.argv
    files = sorted(f for f in glob.glob(os.path.join(ROOT, "**", "*.pptx"), recursive=True)
                   if "~$" not in f and "_docx_work" not in f)
    nf = ns = 0
    locked = []
    for p in files:
        try:
            c = fix_file(p, dry=dry)
        except PermissionError:
            locked.append(os.path.basename(p)[:48])
            continue
        if c:
            nf += 1
            ns += c
    print("%s：%d 册 / %d 个短标签设为垂直居中" % ("空跑" if dry else "已修复", nf, ns))
    if locked:
        print("锁定跳过:", locked[:5])