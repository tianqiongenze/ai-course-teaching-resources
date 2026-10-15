# -*- coding: utf-8 -*-
"""40 个工程化项目终验：pytest + run.py。"""
import glob
import os
import subprocess

ROOT = r"D:/Python编程实战/教学实施资料"
PY = r"C:/Users/Lenovo/AppData/Local/Temp/audit/env314/Scripts/python.exe"

dirs = sorted(d for d in glob.glob(os.path.join(ROOT, "*", "工程化项目", "*")) if os.path.isdir(d))
pt_ok, pt_bad, run_ok, run_bad, files = 0, [], 0, [], 0
for d in dirs:
    rel = os.path.relpath(d, ROOT).replace("\\", "/")
    files += sum(len(f) for _1, _2, f in os.walk(d))
    r = subprocess.run([PY, "-m", "pytest", "-q"], cwd=d, capture_output=True, timeout=300)
    out = (r.stdout or b"").decode("utf-8", "ignore")
    if r.returncode == 0 and "100%" in out:
        pt_ok += 1
    else:
        last = out.strip().splitlines()[-1] if out.strip() else "exit %s" % r.returncode
        pt_bad.append((rel, last[:130]))
    r2 = subprocess.run([PY, "run.py", "--quiet"], cwd=d, capture_output=True, timeout=300)
    rep = os.path.join(d, "output", "report.txt")
    if os.path.exists(rep) and os.path.getsize(rep) > 0:
        run_ok += 1
    else:
        err = (r2.stderr or b"").decode("utf-8", "ignore").strip().splitlines()
        run_bad.append((rel, err[-1][:130] if err else "no report.txt"))

print()
print("=" * 68)
print("工程化项目总数         : %d" % len(dirs))
print("pytest 通过            : %d / %d" % (pt_ok, len(dirs)))
print("run.py 生成 report.txt : %d / %d" % (run_ok, len(dirs)))
print("生成文件总数           : %d" % files)
if pt_bad or run_bad:
    print()
    print("失败明细:")
    for a, b in pt_bad:
        print("  [pytest] %s :: %s" % (a, b))
    for a, b in run_bad:
        print("  [run.py] %s :: %s" % (a, b))
print("=" * 68)
