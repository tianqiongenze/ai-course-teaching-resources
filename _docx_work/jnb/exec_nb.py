# -*- coding: utf-8 -*-
"""82轮·notebook 执行验证器（依次 exec 各 code cell，捕获错误）

用法: python exec_nb.py <notebook路径> [工作目录]
"""
import json
import os
import sys
import traceback


def run_nb(path, workdir=None):
    nb = json.load(open(path, encoding="utf-8"))
    if workdir:
        os.chdir(workdir)
    g = {"__name__": "__main__"}
    n_ok = 0
    for i, c in enumerate(nb["cells"]):
        if c["cell_type"] != "code":
            continue
        src = "".join(c["source"])
        if not src.strip():
            continue
        try:
            exec(compile(src, "<cell%d>" % i, "exec"), g)
            n_ok += 1
        except Exception as e:
            print("  [FAIL] cell %d: %s: %s" % (i, type(e).__name__, e))
            tb = traceback.format_exc().strip().split("\n")
            print("         " + tb[-3].strip() if len(tb) >= 3 else "")
            return False, n_ok
    return True, n_ok


if __name__ == "__main__":
    p = sys.argv[1]
    wd = sys.argv[2] if len(sys.argv) > 2 else None
    ok, n = run_nb(p, wd)
    print("  %s  （%d 个 code cell 执行成功）" % ("PASS ✔" if ok else "FAIL", n))
