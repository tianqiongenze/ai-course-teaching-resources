# -*- coding: utf-8 -*-
"""82轮·同构教师版 notebook 重建器（正式版）

原则：教师版 = 学生版骨架（同 cell 顺序/markdown/函数名）+ TODO 填入完成态
数据源：教师参考/solutions.py（与学生 starter 同构的完成态）
用法：python rebuild2.py <包目录> [--apply]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_solutions import parse_solutions  # noqa: E402

TICKET2FUNC = None


def ticket_to_func(ticket):
    """M1-1a → m11a ; M2-2 → m22 ; Z → z"""
    t = ticket.strip().lower().replace("m", "").replace("-", "").replace(".", "")
    return "m" + t if not t.startswith("z") else "z"


def has_todo(code):
    return ("TODO" in code) or ("NotImplementedError" in code) or ("你的代码" in code)


def func_name(code):
    m = re.match(r"^\s*def\s+(\w+)", code)
    return m.group(1) if m else None


def to_src_lines(text):
    lines = text.rstrip("\n").split("\n")
    out = [l + "\n" for l in lines]
    if out:
        out[-1] = out[-1].rstrip("\n")
    return out


def main():
    pkg = sys.argv[1]
    apply = "--apply" in sys.argv
    root = os.path.join(pkg, "Jupyter实训")
    sol_map = parse_solutions(os.path.join(pkg, "教师参考", "solutions.py"))
    files = sorted(f for f in os.listdir(root)
                   if f.endswith("_学生版.ipynb") and "executed" not in f)
    print("工单函数: %s\n学生版: %d 个\n" % (list(sol_map.keys()), len(files)))
    stat = []
    for f in files:
        sp = os.path.join(root, f)
        snb = json.load(open(sp, encoding="utf-8"))
        # 从文件名提取工单号：W1_M1-1a_描述_学生版.ipynb → M1-1a
        fm = re.match(r"W\d+_([^_]+)_", f)
        ticket = fm.group(1) if fm else ""
        wk = ticket_to_func(ticket)
        if wk not in sol_map:
            # 兜底：从标题提取
            title = "".join(snb["cells"][0]["source"])
            tm = re.search(r"工单\s*([A-Za-z0-9\-\.]+)", title)
            ticket = tm.group(1) if tm else ticket
            wk = ticket_to_func(ticket)
        if wk not in sol_map:
            print("  [SKIP] %-40s 工单=%s → %s 未找到" % (f[:40], ticket, wk))
            continue
        sol = sol_map[wk]
        inner = sol["inner"]
        # 重建
        tcell = snb["cells"]
        replaced, kept = [], []
        for c in tcell:
            if c["cell_type"] != "code":
                continue
            code = "".join(c["source"])
            fn = func_name(code)
            if fn and fn in inner and has_todo(code):
                c["source"] = to_src_lines(inner[fn])
                replaced.append(fn)
            elif fn and fn in inner and not has_todo(code):
                # 已完整但 solutions 有同名 → 统一为完成态（保持一致）
                c["source"] = to_src_lines(inner[fn])
                kept.append(fn)
        # 标题改为教师版
        t0 = "".join(snb["cells"][0]["source"])
        snb["cells"][0]["source"] = [t0.replace("学生实训版", "教师参考版（完成态·同构学生版）")
                                     .replace("— 学生版", "— 教师版") + "\n"]
        out_name = f.replace("_学生版", "_教师版")
        if apply:
            json.dump(snb, open(os.path.join(root, out_name), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
        stat.append((out_name, wk, replaced, kept))
        print("  %-42s → %-5s 填TODO:%s 统一:%s" % (out_name[:42], wk, replaced, kept))
    print("\n共处理 %d 个" % len(stat))
    if not apply:
        print("（空跑，未写入；加 --apply 生效）")


if __name__ == "__main__":
    main()
