# -*- coding: utf-8 -*-
"""83轮·代码文件命名与课件周次同步

统一规范（参考课件 W07/W10-W20）：
  05 包 Jupyter实训  W{教学周}_ → W{新周}_
  05 包 学生代码框架  w{教学周}_ → W{新周}_
  并同步更新各文件内对这些文件名的引用。

教学周 k → 新周：k=1→W07；k≥2→W(k+8)
用法: python rename_code_week.py <包目录> [--apply]
"""
import glob
import os
import re
import sys

ROOT = r"D:/Python编程实战/教学实施资料"


def new_week(k):
    k = int(k)
    return "W07" if k == 1 else "W%02d" % (k + 8)


def build_map():
    """返回 {旧前缀: 新前缀}，旧前缀含 W1..W12 / w1..w12"""
    m = {}
    for k in range(1, 13):
        nw = new_week(k)
        m["W%d" % k] = nw
        m["w%d" % k] = nw
    return m


def main():
    pkg = sys.argv[1]
    apply = "--apply" in sys.argv
    os.chdir(os.path.join(ROOT, pkg))
    wmap = build_map()
    dirs = ["Jupyter实训", "学生代码框架"]
    # ① 重命名（两步防冲突）
    plan = []
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.startswith("~$") or f.endswith(".tmp"):
                continue
            m = re.match(r"^([Ww]\d{1,2})_", f)
            if m and m.group(1) in wmap:
                plan.append((os.path.join(d, f),
                             os.path.join(d, wmap[m.group(1)] + "_" + f[m.end():])))
    print("待重命名: %d 个" % len(plan))
    if apply:
        # 第一步：临时名
        tmp = []
        for old, new in plan:
            t = old + ".__tmp__"
            os.rename(old, t)
            tmp.append((t, new))
        # 第二步：目标名
        for t, new in tmp:
            os.rename(t, new)
    for old, new in plan:
        print("  %s → %s" % (os.path.basename(old), os.path.basename(new)))
    # ② 更新内容引用（全包扫描）
    if apply:
        n = 0
        files = []
        for ext in ("md", "py", "ipynb", "txt", "yaml", "json"):
            files += glob.glob("**/*." + ext, recursive=True)
        for f in files:
            if "__pycache__" in f or ".tmp" in f:
                continue
            try:
                s = open(f, encoding="utf-8").read()
            except Exception:
                continue
            o = s
            for old_k, new_k in wmap.items():
                # 引用形态：w1_clean_starter.py / W1_M1-1a / w10_rag_starter
                s = re.sub(r"(?<![A-Za-z0-9])%s_" % old_k, new_k + "_", s)
            if s != o:
                open(f, "w", encoding="utf-8", newline="\n").write(s)
                n += 1
                print("  [引用更新] %s" % f[:64])
        print("引用更新: %d 个文件" % n)
    if not apply:
        print("\n（空跑；加 --apply 生效）")


if __name__ == "__main__":
    main()
