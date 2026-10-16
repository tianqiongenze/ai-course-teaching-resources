# -*- coding: utf-8 -*-
"""82轮·同构教师版 notebook 重建器 v3（完整版）

修复三点：
  ① TODO 函数 → solutions 同名完成态
  ② `__main__` 驱动 cell → solutions driver（含正确调用与验证输出）
  ③ `__file__`（notebook 不可用）→ os.getcwd() 兼容写法
  ④ 新增「教师版运行环境」cell（提供 np/PKG 等完成态依赖）
用法：python rebuild3.py <包目录> [--apply]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_solutions import parse_solutions  # noqa: E402


def ticket_to_func(t):
    t = t.strip().lower().replace("m", "").replace("-", "").replace(".", "")
    return "z" if t.startswith("z") else "m" + t


def has_todo(code):
    return ("TODO" in code) or ("NotImplementedError" in code) or ("你的代码" in code)


def func_name(code):
    m = re.match(r"^\s*def\s+(\w+)", code)
    return m.group(1) if m else None


def to_lines(text):
    ls = text.rstrip("\n").split("\n")
    out = [l + "\n" for l in ls]
    if out:
        out[-1] = out[-1].rstrip("\n")
    return out


# __file__ 兼容替换（notebook 中 __file__ 未定义；已 chdir 到包根）
FILE_FIX = [
    ('os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "工具")',
     'os.path.join(os.getcwd(), "工具")'),
    ('os.path.dirname(os.path.abspath(__file__))', 'os.getcwd()'),
    ('os.path.abspath(__file__)', 'os.getcwd()'),
]

ENV_CELL = """# --- 教师版运行环境（完成态依赖，勿改）---
import json, re, time          # solutions 完成态所需
import numpy as np
PKG = os.getcwd()              # 课程包根（学生版环境cell已chdir至此）
print("教师版运行环境就绪 · PKG =", PKG)
"""

# 别名映射：solutions 函数名 → 学生版函数名（命名差异课次）
ALIAS = {
    "m51": {"make_random_policy": "policy_random",
            "policy_safety_first": "policy_alarm_first",
            "run": "main"},
}
# 教师版附加函数（solutions 有、学生版无 → 作为进阶拓展插入 driver 前）
EXTRA = {
    "m51": ["policy_reward_greedy"],
}


def main():
    pkg = sys.argv[1]
    apply = "--apply" in sys.argv
    root = os.path.join(pkg, "Jupyter实训")
    sol_map = parse_solutions(os.path.join(pkg, "教师参考", "solutions.py"))
    files = sorted(f for f in os.listdir(root)
                   if f.endswith("_学生版.ipynb") and "executed" not in f)
    print("工单函数: %s\n学生版: %d\n" % (list(sol_map.keys()), len(files)))
    for f in files:
        snb = json.load(open(os.path.join(root, f), encoding="utf-8"))
        fm = re.match(r"W\d+_([^_]+)_", f)
        ticket = fm.group(1) if fm else ""
        wk = ticket_to_func(ticket)
        if wk not in sol_map:
            print("  [SKIP] %s → %s" % (f[:40], wk))
            continue
        sol = sol_map[wk]
        inner, driver = sol["inner"], sol["driver"]
        alias = ALIAS.get(wk, {})          # solutions名 → 学生版名
        rev = {v: k for k, v in alias.items()}   # 学生版名 → solutions名

        cells = snb["cells"]
        # 1) 定位环境准备 cell（第一个 code cell）
        env_idx = next(i for i, c in enumerate(cells) if c["cell_type"] == "code")
        new_cells = []
        did_env = did_drv = 0
        replaced = []
        for i, c in enumerate(cells):
            if c["cell_type"] == "code":
                code = "".join(c["source"])
                fn = func_name(code)
                # ② 驱动 cell → solutions driver（并把函数名映射回学生版名）
                if "__main__" in code and driver.strip():
                    d = driver
                    for sol_name, stu_name in alias.items():
                        d = re.sub(r"\b%s\b" % sol_name, stu_name, d)
                    # 附加函数 cell（教师版进阶拓展，学生版无）
                    for ex in EXTRA.get(wk, []):
                        if ex in inner:
                            new_cells.append({"cell_type": "markdown", "metadata": {},
                                              "source": ["### 【教师版附加】`def %s(...)` —— 进阶拓展（学生版无对应，A层可挑战）\n" % ex]})
                            new_cells.append({"cell_type": "code", "metadata": {},
                                              "source": to_lines(inner[ex]),
                                              "execution_count": None, "outputs": []})
                            replaced.append("附加:" + ex)
                    c = dict(c)
                    c["source"] = to_lines(d)
                    did_drv += 1
                # ① TODO 函数 → 完成态（支持别名：函数名保持学生版）
                elif fn and (fn in inner or fn in rev):
                    src = inner[fn] if fn in inner else inner[rev[fn]]
                    # 别名情形：把 solutions 函数名改回学生版名
                    if fn in rev:
                        src = re.sub(r"^def\s+%s\s*\(" % rev[fn], "def %s(" % fn, src, count=1)
                    c = dict(c)
                    c["source"] = to_lines(src)
                    replaced.append(fn)
                # ③ __file__ 兼容
                else:
                    s = code
                    for a, b in FILE_FIX:
                        s = s.replace(a, b)
                    if s != code:
                        c = dict(c)
                        c["source"] = to_lines(s)
                        replaced.append("__file__修复")
            new_cells.append(c)
            # ④ 环境 cell 后插入教师版运行环境
            if i == env_idx:
                new_cells.append({"cell_type": "code", "metadata": {},
                                  "source": to_lines(ENV_CELL), "execution_count": None,
                                  "outputs": []})
                did_env = 1
        snb["cells"] = new_cells
        t0 = "".join(snb["cells"][0]["source"])
        snb["cells"][0]["source"] = [t0.replace("学生实训版", "教师参考版（完成态·同构学生版）") + "\n"]
        out = f.replace("_学生版", "_教师版")
        if apply:
            json.dump(snb, open(os.path.join(root, out), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
        print("  %-40s → %-5s 环境+%d 驱动+%d 替换:%s" % (out[:40], wk, did_env, did_drv, replaced))
    if not apply:
        print("\n（空跑；加 --apply 生效）")


if __name__ == "__main__":
    main()
