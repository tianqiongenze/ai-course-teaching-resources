# -*- coding: utf-8 -*-
"""83轮·01/02/03 代码文件命名与课件周次同步

统一规范（与课件一致）：W{周次}_{描述}
  01: m11→W04 m12→W05 m21→W06 m22→W07 m31→W08 m32→W09 m41→W10 m42→W11
  02: w01→W01 w02→W02 … w12→W12
  03: p11→W01 p12→W02 p21→W03 p22→W04 p33→W05 p41→W06 p55→W07 p66→W08
用法: python rename_code_week2.py <包目录> [--apply]
"""
import glob
import os
import re
import sys

ROOT = r"D:/Python编程实战/教学实施资料"

MAP = {
    "01-AI应用基础": {
        "m11": "W04", "m12": "W05", "m21": "W06", "m22": "W07",
        "m31": "W08", "m32": "W09", "m41": "W10", "m42": "W11"},
    "02-程序设计基础": dict(("w%02d" % k, "W%02d" % k) for k in range(1, 13)),
    "03-Python程序设计-项目实战": {
        "p11": "W01", "p12": "W02", "p21": "W03", "p22": "W04",
        "p33": "W05", "p41": "W06", "p55": "W07", "p66": "W08"},
}
DIRS = ["Jupyter实训", "学生代码框架"]


def main():
    pkg = sys.argv[1]
    apply = "--apply" in sys.argv
    os.chdir(os.path.join(ROOT, pkg))
    mp = MAP[pkg]
    plan = []
    for d in DIRS:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.startswith("~$"):
                continue
            m = re.match(r"^([a-zA-Z]\d{1,2})_", f)
            if m and m.group(1) in mp:
                plan.append((os.path.join(d, f), os.path.join(d, mp[m.group(1)] + "_" + f[m.end():])))
    print("%s 待重命名: %d 个" % (pkg, len(plan)))
    if apply:
        tmp = []
        for old, new in plan:
            t = old + ".__tmp__"
            os.rename(old, t)
            tmp.append((t, new))
        for t, new in tmp:
            os.rename(t, new)
    for old, new in plan:
        print("  %s → %s" % (os.path.basename(old), os.path.basename(new)))
    if apply:
        # 引用更新
        n = 0
        files = []
        for ext in ("md", "py", "ipynb", "txt", "yaml", "json"):
            files += glob.glob("**/*." + ext, recursive=True)
        for f in files:
            if "__pycache__" in f or ".tmp" in f or "_backup" in f:
                continue
            try:
                s = open(f, encoding="utf-8").read()
            except Exception:
                continue
            o = s
            for old_k, new_k in mp.items():
                s = re.sub(r"(?<![A-Za-z0-9])%s_" % old_k, new_k + "_", s)
            if s != o:
                open(f, "w", encoding="utf-8", newline="\n").write(s)
                n += 1
        print("引用更新: %d 个文件" % n)
    if not apply:
        print("\n（空跑；加 --apply 生效）")


if __name__ == "__main__":
    main()
