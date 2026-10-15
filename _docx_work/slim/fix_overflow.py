# -*- coding: utf-8 -*-
"""75号轮·越界修复：决策矩阵表与分层架构底板

两类越界（审查工具 fix_layout.py --audit 发现）：
  A 决策矩阵表（12 页）：5 列 [0.87, 4.59, 7.22, 9.84, 12.47]，末列右缘 15.09 越界 1.76in。
     修复：等比压缩列宽与列距 → 首列 3.72→3.40、数据列 2.62→2.20、列距 2.63→2.24，
     右缘 = 0.87+3.40+3*2.24+2.20 = 13.19 ✔（页宽 13.33）
  B 分层架构底板（7 页）：右侧装饰底板 L9.19 W5.56（右缘 14.75）与文字框 L9.23 W5.47（右缘 14.70）。
     修复：把第 2 列（底板+文字框）左移，使右缘 = 13.05 → L_bottom = 13.05-5.56 = 7.49；
     但会与第 1 列（L3.50 W5.56，右缘 9.06）重叠 → 改为压缩宽度：W 5.56→4.30、文字框 W 5.47→4.24，
     L 9.19→8.75、文字 L 9.23→8.79 → 右缘 = 8.75+4.30 = 13.05 ✔ 且不与第 1 列（右缘 9.06）重叠。

幂等：修复前检查目标位置，已修复则跳过。
用法：python _docx_work/slim/fix_overflow.py [--dry]
"""
import argparse
import glob
import os

from pptx import Presentation
from pptx.util import Emu, Inches

ROOT = r"D:/Python编程实战/教学实施资料"
TOL = 0.06

# ── 方案A：决策矩阵 ──
MTX_OLD = [0.87, 4.59, 7.22, 9.84, 12.47]
MTX_W_FIRST_OLD, MTX_W_OLD = 3.72, 2.62
MTX_STEP_OLD = 2.63
MTX_W_FIRST_NEW, MTX_W_NEW = 3.40, 2.20
MTX_STEP_NEW = 2.24
MTX_MAX_L = 12.0          # 判定特征：存在 L≈12.47 的矩阵列


def close(a, b, tol=TOL):
    return abs(a - b) < tol


def fix_matrix(slide):
    """把本页所有矩阵形状按列重排到新几何。返回修改数。"""
    moved = 0
    for sh in slide.shapes:
        L = Emu(sh.left).inches
        W = Emu(sh.width).inches
        # 第一列
        if close(L, MTX_OLD[0]) and close(W, MTX_W_FIRST_OLD):
            sh.left = Inches(MTX_OLD[0])
            sh.width = Inches(MTX_W_FIRST_NEW)
            moved += 1
            continue
        # 数据列 1..3（L=4.59/7.22/9.84，宽 2.62）
        hit = False
        for i, old_l in enumerate(MTX_OLD[1:4], 1):
            if close(L, old_l) and close(W, MTX_W_OLD):
                sh.left = Inches(MTX_OLD[0] + MTX_W_FIRST_NEW + i * MTX_STEP_NEW)
                sh.width = Inches(MTX_W_NEW)
                moved += 1
                hit = True
                break
        # 最右越界列（L=12.47）
        if not hit and close(L, MTX_OLD[4]) and close(W, MTX_W_OLD):
            sh.left = Inches(MTX_OLD[0] + MTX_W_FIRST_NEW + 3 * MTX_STEP_NEW)
            sh.width = Inches(MTX_W_NEW)
            moved += 1
    return moved


# ── 方案B：分层架构底板 ──
ARCH_OLD_L, ARCH_OLD_W = 9.19, 5.56
ARCH_TXT_D = 0.04         # 文字框相对底板的偏移
ARCH_NEW_L, ARCH_NEW_W = 8.75, 4.30


def fix_arch(slide):
    moved = 0
    for sh in slide.shapes:
        L, W = Emu(sh.left).inches, Emu(sh.width).inches
        if close(L, ARCH_OLD_L) and close(W, ARCH_OLD_W):
            sh.left = Inches(ARCH_NEW_L)
            sh.width = Inches(ARCH_NEW_W)
            moved += 1
        elif close(L, ARCH_OLD_L + ARCH_TXT_D) and close(W, ARCH_OLD_W - 2 * ARCH_TXT_D):
            sh.left = Inches(ARCH_NEW_L + ARCH_TXT_D)
            sh.width = Inches(ARCH_NEW_W - 2 * ARCH_TXT_D)
            moved += 1
    return moved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    files = sorted(f for f in glob.glob(os.path.join(ROOT, "**", "*.pptx"), recursive=True)
                   if "~$" not in f and "_docx_work" not in f)
    n_mtx = n_arch = 0
    files_changed = set()
    locked = []
    for path in files:
        rel = os.path.relpath(path, ROOT)
        try:
            prs = Presentation(path)
        except Exception:
            continue
        changed = 0
        for s in prs.slides:
            ls = [Emu(sh.left).inches for sh in s.shapes]
            if any(close(l, MTX_OLD[4]) for l in ls):
                changed += fix_matrix(s)
            if any(close(l, ARCH_OLD_L) for l in ls):
                changed += fix_arch(s)
        if changed and not a.dry:
            try:
                prs.save(path)
            except PermissionError:
                print("  [锁定跳过] %s（文件被外部程序打开）" % rel[:64])
                locked.append(rel)
                continue
            files_changed.add(rel)
            n_mtx += changed
        elif changed:
            n_mtx += changed
    print("=" * 70)
    print("%s：修改形状 %d 个 / 涉及 %d 册"
          % ("[空跑]" if a.dry else "[已修复]", n_mtx, len(files_changed) if not a.dry else -1))
    if locked:
        print("锁定跳过 %d 册（请关闭外部程序后重跑）:" % len(locked))
        for f in locked:
            print("  ", f[:70])
    if not a.dry:
        for f in sorted(files_changed):
            print("  ", f[:70])
    print("=" * 70)


if __name__ == "__main__":
    main()
