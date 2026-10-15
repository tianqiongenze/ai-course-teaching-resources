# -*- coding: utf-8 -*-
"""76号轮·续行缩进修复器 v4（pycodestyle 进程内，快速）

对 E126/E127/E128/E131 行枚举候选缩进，用 pycodestyle 进程内校验，
取第一个使该行告警消失的缩进。只改行首空白。
"""
import glob
import os
import sys

import pycodestyle

ROOT = r"D:/Python编程实战/教学实施资料"
CODES = {"E126", "E127", "E128", "E131"}
MAXLEN = 120


class Cap:
    """最小 report：只收集目标 code 的行号。"""

    def __init__(self, options=None):
        self.rows = []

    def init_file(self, filename, lines, expected, line_offset):
        self.rows = []

    def error(self, line_number, offset, text, check):
        code = text.split()[0]
        if code in CODES:
            self.rows.append((line_number, code))
        return 0

    def get_count(self):
        return len(self.rows)

    def get_file_results(self):
        return 1 if self.rows else 0

    def increment_logical_line(self, *a, **k):
        pass

    def start(self):
        pass

    def stop(self):
        pass


def check(path):
    """返回 [(lineno, code)]"""
    rep = Cap()
    ck = pycodestyle.Checker(path, report=rep, max_line_length=MAXLEN,
                             select=list(CODES))
    ck.check_all()
    return rep.rows


def candidates(lines, ln):
    cur = len(lines[ln - 1]) - len(lines[ln - 1].lstrip())
    prev = lines[ln - 2] if ln - 2 >= 0 else ""
    pind = len(prev) - len(prev.lstrip())
    cands = {pind + 4}
    for j, ch in enumerate(prev):
        if ch in "([{":
            cands.add(j + 1)
    for d in (-4, -2, 2, 4, 8, 12):
        if cur + d >= 0:
            cands.add(cur + d)
    return sorted(c for c in cands if c >= 0)


def fix_file(path):
    changed = 0
    for _ in range(3):
        errs = check(path)
        if not errs:
            break
        lines = open(path, encoding="utf-8").read().splitlines()
        progressed = False
        for ln, _code in sorted(set(errs)):
            if ln - 1 >= len(lines):
                continue
            st = lines[ln - 1].lstrip()
            if not st:
                continue
            orig = lines[ln - 1]
            ok = False
            for c in candidates(lines, ln):
                lines[ln - 1] = " " * c + st
                open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
                if ln not in [x[0] for x in check(path)]:
                    changed += 1
                    ok = progressed = True
                    break
            if not ok:
                lines[ln - 1] = orig
                open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
        if not progressed:
            break
    return changed


def main():
    files = [f for f in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True)
             if "_docx_work" not in f and "__pycache__" not in f
             and "site-packages" not in f]
    bad = [f for f in files if check(f)]
    print("含 E12x 的文件: %d" % len(bad))
    total = nf = 0
    for f in bad:
        c = fix_file(f)
        if c:
            nf += 1
            total += c
    print("修复 %d 文件 / %d 行" % (nf, total))
    left = [(f, check(f)) for f in files if check(f)]
    print("剩余 E12x: %d" % sum(len(v) for _, v in left))
    for f, v in left[:8]:
        print("   %s %s" % (os.path.relpath(f, ROOT)[:62], v[:2]))


if __name__ == "__main__":
    main()