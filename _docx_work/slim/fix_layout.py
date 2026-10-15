# -*- coding: utf-8 -*-
"""75号轮·布局审查与修复工具（高级美工视角）

逐页审查两类几何异常并修复：
  ① 注释框压卡片：如「每课时40分钟 · 共80分钟（六步法课堂化）」注释框（T6.63 H0.28）
     被最后一行卡片（T6.40 H0.74，底7.14）盖住 → 把注释框移到标题下方空带 T1.35。
  ② 元素越界：形状超出页面边界（右/下），记录待修。

用法：
  python _docx_work/slim/fix_layout.py --audit          # 只审查
  python _docx_work/slim/fix_layout.py                  # 审查+修复（默认只修①）
  python _docx_work/slim/fix_layout.py --backup DIR     # 修复前另存备份
"""
import argparse
import copy
import glob
import os
import sys

from pptx import Presentation
from pptx.util import Emu, Inches

ROOT = r"D:/Python编程实战/教学实施资料"
NOTE_KEY = "每课时40分钟"
NOTE_TOP_SAFE = 1.35      # 标题栏(T0~1.26)下方的空带
PAGE_W = 13.333
PAGE_H = 7.5


def emu_in(v):
    return Emu(v).inches


def audit_slide(s):
    """返回 (issues, note_shape) — issues: [(类型, 描述, shape)]"""
    issues = []
    note = None
    cards = []
    for sh in s.shapes:
        T, L = emu_in(sh.top), emu_in(sh.left)
        W, H = emu_in(sh.width), emu_in(sh.height)
        # ① 越界（豁免：页顶满幅标题栏 L0 W≈页宽）
        if (L + W > PAGE_W + 0.02 or T + H > PAGE_H + 0.02) and not (L < 0.05 and W > PAGE_W - 0.1):
            txt = sh.text_frame.text[:24].replace("\n", "/") if sh.has_text_frame else "(shape)"
            issues.append(("越界", "T%.2f L%.2f W%.2f H%.2f '%s'" % (T, L, W, H, txt), sh))
        if not sh.has_text_frame:
            continue
        if NOTE_KEY in sh.text_frame.text:
            note = sh
        elif W > 4 and 0.5 < H < 1.0 and T > 1.5:
            cards.append(sh)
    # ② 注释框压卡片：注释底 < 卡片底 且 注释顶 < 卡片底（相交）
    if note is not None and cards:
        nb = emu_in(note.top) + emu_in(note.height)
        cb = max(emu_in(c.top) + emu_in(c.height) for c in cards)
        # 注释顶在卡片区内且注释底不高于卡片底 → 视为被盖
        nt = emu_in(note.top)
        if nt < cb - 0.05 and nb > max(emu_in(c.top) for c in cards) + 0.05:
            issues.append(("注释压卡片",
                           "注释底%.2f < 卡片底%.2f（注释顶%.2f）" % (nb, cb, nt), note))
    return issues, note


def fix_slide(s, note):
    """把被压的注释框移到标题下方空带；返回 True 若有修改。"""
    nt = emu_in(note.top)
    target = Inches(NOTE_TOP_SAFE)
    if abs(nt - NOTE_TOP_SAFE) < 0.05:
        return False
    note.top = target
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true", help="只审查不修改")
    ap.add_argument("--backup", default=None, help="修复前把将改动的文件备份到该目录")
    a = ap.parse_args()

    files = sorted(f for f in glob.glob(os.path.join(ROOT, "**", "*.pptx"), recursive=True)
                   if "~$" not in f and "_docx_work" not in f)
    n_pages = n_bad = 0
    fixed = skipped_no_issue = 0
    backup_made = set()
    report = []

    for path in files:
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        try:
            prs = Presentation(path)
        except Exception:
            continue
        changed = False
        for s in prs.slides:
            n_pages += 1
            issues, note = audit_slide(s)
            overlaps = [x for x in issues if x[0] == "注释压卡片"]
            oob = [x for x in issues if x[0] == "越界"]
            if oob:
                n_bad += 1
                report.append((rel, "越界", oob[0][1]))
            if overlaps and not a.audit:
                if a.backup and rel not in backup_made:
                    os.makedirs(a.backup, exist_ok=True)
                    dst = os.path.join(a.backup, os.path.basename(path))
                    if not os.path.exists(dst):
                        import shutil
                        shutil.copy2(path, dst)
                    backup_made.add(rel)
                if fix_slide(s, note):
                    changed = True
                    fixed += 1
                    report.append((rel, "修复:注释移至T%.2f" % NOTE_TOP_SAFE, overlaps[0][1]))
            elif overlaps and a.audit:
                n_bad += 1
                report.append((rel, "注释压卡片", overlaps[0][1]))
        if changed:
            try:
                prs.save(path)
            except PermissionError:
                report.append((rel, "锁定跳过", "文件被外部程序打开"))
                continue

    print("=" * 76)
    print("布局审查%s —— 扫描 %d 册 / %d 页" % ("（只读）" if a.audit else "（已修复）", len(files), n_pages))
    print("=" * 76)
    kind_count = {}
    for _, kind, _ in report:
        kind_count[kind.split(":")[0]] = kind_count.get(kind.split(":")[0], 0) + 1
    for k, v in sorted(kind_count.items()):
        print("  %-14s %d 处" % (k, v))
    if report:
        print("-" * 76)
        for rel, kind, desc in report[:30]:
            print("  [%s] %s  %s" % (kind, rel[:54], desc[:44]))
        if len(report) > 30:
            print("  ... 共 %d 条" % len(report))
    print("=" * 76)
    if not a.audit:
        print("修复注释框挪位 %d 处" % fixed)


if __name__ == "__main__":
    main()


def fix_cover_title_height(prs, dry=True):
    """封面修复：单行大标题框(T2.0-3.4, H>1.6, 字号>=30pt) 高度收窄为 1.0in，
    消除与课时文案框(顶~4.1) 的框重叠。返回修复形状数。"""
    s = prs.slides[0]
    n = 0
    for sh in list(s.shapes):
        if not sh.has_text_frame:
            continue
        T, H = Emu(sh.top).inches, Emu(sh.height).inches
        if not (2.0 <= T < 3.4) or H <= 1.6:
            continue
        sizes = [r.font.size.pt for pa in sh.text_frame.paragraphs
                 for r in pa.runs if r.font.size]
        if not sizes or max(sizes) < 30:
            continue
        if not dry and abs(H - 1.0) > 0.05:
            sh.height = Inches(1.0)
        n += 1
    return n


def fix_all_covers(root, dry=True):
    """批处理全部封面的标题框高度。返回 (files, shapes)。"""
    import glob
    nf = ns = 0
    locked = []
    for p in sorted(glob.glob(os.path.join(root, "**", "*.pptx"), recursive=True)):
        if "~$" in p or "_docx_work" in p:
            continue
        try:
            prs = Presentation(p)
        except Exception:
            continue
        if fix_cover_title_height(prs, dry=True) == 0:
            continue
        if not dry:
            try:
                prs.save(p)
            except PermissionError:
                locked.append(os.path.basename(p)[:50])
                continue
        nf += 1
        ns += fix_cover_title_height(prs, dry=True)
    return nf, ns, locked
