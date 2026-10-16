# -*- coding: utf-8 -*-
"""82轮·notebook 执行并保存输出（生成 _executed 版本）

用法: python exec_save.py <notebook> <工作目录>
输出: 同目录 <name>_executed.ipynb
"""
import contextlib
import io
import json
import os
import sys
import traceback


def run_and_save(path, workdir):
    nb = json.load(open(path, encoding="utf-8"))
    os.chdir(workdir)
    g = {"__name__": "__main__"}
    err = None
    for c in nb["cells"]:
        if c["cell_type"] != "code":
            continue
        src = "".join(c["source"])
        if not src.strip():
            c["outputs"] = []
            c["execution_count"] = None
            continue
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                exec(compile(src, "<cell>", "exec"), g)
            out = buf.getvalue()
            c["outputs"] = [{"output_type": "stream", "name": "stdout",
                             "text": [l + "\n" for l in out.rstrip("\n").split("\n")]}] if out.strip() else []
            c["execution_count"] = 1
        except Exception as e:
            out = buf.getvalue()
            c["outputs"] = [{"output_type": "stream", "name": "stdout",
                             "text": [l + "\n" for l in out.split("\n")]}]
            c["outputs"].append({
                "output_type": "error", "ename": type(e).__name__, "evalue": str(e),
                "traceback": traceback.format_exc().split("\n")})
            err = "%s: %s" % (type(e).__name__, e)
            break
    base = path[:-6] if path.endswith(".ipynb") else path
    outp = base + "_executed.ipynb"
    json.dump(nb, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return outp, err


if __name__ == "__main__":
    p, wd = sys.argv[1], sys.argv[2]
    outp, err = run_and_save(p, wd)
    print("  %s %s" % ("OK" if not err else "ERR(" + err + ")", os.path.basename(outp)))
