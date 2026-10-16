# -*- coding: utf-8 -*-
"""82轮·同构教师版 notebook 重建器

问题：原教师版把整套 solutions_multi*.py（含全部周次函数）塞进每个文件，
      且函数名/结构与学生版 starter 不对应 → 教师无法逐 cell 对照讲解。

方案：教师版 = 学生版骨架（同 cell 顺序、同 markdown、同函数名）
      + 含 TODO/NotImplementedError 的 code cell 用 solutions.py 对应完成态替换
      + `__main__` 驱动 cell 用 solutions 的验证段替换
      + 附录：答案对照表 + 执行验证

用法: python rebuild_teacher_nb.py <包目录> [--apply]
"""
import json
import os
import re
import shutil
import sys

# ══════════ solutions.py 解析 ══════════

def parse_solutions(sol_path):
    """解析 solutions.py → {工单函数名: {'inner': {函数名: 源码}, 'driver': 驱动源码}}"""
    src = open(sol_path, encoding="utf-8").read()
    # 找所有顶层 def 的位置
    hits = [(m.start(), m.group(1)) for m in re.finditer(r"^def\s+(\w+)\s*\(", src, re.M)]
    out = {}
    for i, (pos, name) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else len(src)
        body = src[pos:end]
        inner = {}
        # 提取 4 空格缩进的嵌套 def
        for m in re.finditer(r"^    def\s+(\w+)\s*\(", body, re.M):
            fname = m.group(1)
            fstart = m.start()
            # 函数体结束：下一个 4 空格 def 或 4 空格非缩进语句块结尾
            nxt = re.search(r"^    def\s+\w+\s*\(", body[fstart + 10:], re.M)
            fend = fstart + 10 + nxt.start() if nxt else len(body)
            chunk = body[fstart:fend]
            # 去掉末尾空行
            chunk = chunk.rstrip() + "\n"
            # 去掉一层 4 空格缩进
            lines = chunk.split("\n")
            ded = []
            for ln in lines:
                ded.append(ln[4:] if ln.startswith("    ") else ln)
            inner[fname] = "\n".join(ded).rstrip() + "\n"
        # 驱动段：去掉所有嵌套函数后的剩余（从最后一个嵌套函数结束到函数末尾）
        if inner:
            last_inner_end = 0
            for m in re.finditer(r"^    def\s+\w+\s*\(", body, re.M):
                last_inner_end = m.start()
            # 找最后一个嵌套函数的实际结束（用缩进判断）
            tail = body[last_inner_end:]
            # 跳过最后一个嵌套函数体
            lines = tail.split("\n")
            k = 0
            # 第一行是 def 行
            for j in range(1, len(lines)):
                if lines[j].strip() and not lines[j].startswith("    "):
                    k = j
                    break
                if lines[j].strip() and lines[j].startswith("    "):
                    k = j
            driver = "\n".join(lines[k:]) if k else ""
        else:
            # 无嵌套函数：取函数体（去掉 def 行）
            lines = body.split("\n")
            k = 1
            for j in range(1, len(lines)):
                if lines[j].strip() and not lines[j].startswith("    "):
                    k = j
                    break
                k = j + 1
            driver = "\n".join(lines[1:]).rstrip()
        out[name] = {"inner": inner, "driver": driver}
    return out


# ══════════ 学生版 → 教师版 ══════════

def has_todo(code):
    return ("TODO" in code) or ("NotImplementedError" in code) or ("你的代码" in code)


def func_name(code):
    m = re.match(r"^\s*def\s+(\w+)", code)
    return m.group(1) if m else None


def rebuild(student_nb, sol_map, week_key, title):
    """返回新的教师版 notebook dict"""
    nb = json.loads(json.dumps(student_nb))  # deep copy
    cells = nb["cells"]
    # 工单函数（如 m11a）——按周次定位
    sol = sol_map.get(week_key, {"inner": {}, "driver": ""})
    inner = sol["inner"]

    replaced = []
    for i, c in enumerate(cells):
        if c["cell_type"] != "code":
            continue
        code = "".join(c["source"])
        fn = func_name(code)
        if fn and fn in inner and has_todo(code):
            # 用 solutions 同名实现替换
            new = inner[fn]
            c["source"] = [l + "\n" for l in new.split("\n")]
            if c["source"]:
                c["source"][-1] = c["source"][-1].rstrip("\n")
            replaced.append(fn)
        elif "__main__" in code and sol["driver"].strip():
            # 驱动 cell → solutions 验证段
            drv = sol["driver"]
            c["source"] = [l + "\n" for l in drv.split("\n")]
            if c["source"]:
                c["source"][-1] = c["source"][-1].rstrip("\n")
            replaced.append("__main__")
    return nb, replaced


def main():
    pkg = sys.argv[1] if len(sys.argv) > 1 else "."
    apply = "--apply" in sys.argv
    root = os.path.join(pkg, "Jupyter实训")
    sol_path = os.path.join(pkg, "教师参考", "solutions.py")
    if not os.path.exists(sol_path):
        print("未找到 solutions.py:", sol_path)
        return
    sol_map = parse_solutions(sol_path)
    print("solutions.py 工单函数:", list(sol_map.keys()))
    # 工单号 → 周次 key 映射（学生版文件名含 M1-1a 等）
    files = sorted(f for f in os.listdir(root)
                   if f.endswith("_学生版.ipynb") and "executed" not in f)
    print("\n学生版文件: %d" % len(files))
    for f in files:
        snb = json.load(open(os.path.join(root, f), encoding="utf-8"))
        # 从标题提取工单号
        t0 = "".join(snb["cells"][0]["source"])
        m = re.search(r"工单\s*([A-Za-z0-9\-\.]+?)[》\s]", t0)
        ticket = m.group(1) if m else ""
        # 工单号 → solutions 函数名
        wk = None
        for k in sol_map:
            if k.lower().replace("-", "") in ticket.lower().replace("-", "").replace(".", ""):
                wk = k; break
        if wk is None:
            # 用 W 序号猜测
            print("  [SKIP] %s（工单号 %s 无法映射）" % (f, ticket))
            continue
        new_nb, rep = rebuild(snb, sol_map, wk, t0[:40])
        print("  %-42s → %-6s 替换: %s" % (f[:42], wk, rep))


if __name__ == "__main__":
    main()
