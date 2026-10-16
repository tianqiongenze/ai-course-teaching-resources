# -*- coding: utf-8 -*-
"""82轮·教师版 TODO 填充 + 参考答案附录（01/02/03 通用）

用法: python fill_answers.py <包目录> <answers模块名> [--apply]
"""
import ast
import importlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def head_name(code):
    m = re.match(r"\s*(?:def|class)\s+(\w+)", code)
    return m.group(1) if m else None


def to_lines(t):
    ls = t.rstrip("\n").split("\n")
    o = [l + "\n" for l in ls]
    if o:
        o[-1] = o[-1].rstrip("\n")
    return o


def main():
    pkg = sys.argv[1]
    mod = sys.argv[2]
    apply = "--apply" in sys.argv
    m = importlib.import_module(mod)
    ans = next(v for k, v in vars(m).items()
               if k.isupper() and isinstance(v, dict))
    root = os.path.join(pkg, "Jupyter实训")
    sol_src = open(os.path.join(pkg, "教师参考", "solutions.py"), encoding="utf-8").read()
    sol_funcs = {}
    for nd in ast.parse(sol_src).body:
        if isinstance(nd, ast.FunctionDef):
            seg = ast.get_source_segment(sol_src, nd)
            if seg:
                sol_funcs[nd.name] = seg

    files = sorted(f for f in os.listdir(root)
                   if f.endswith("_学生版.ipynb") and "executed" not in f)
    for f in files:
        key = f.split("_")[0].lower()
        nb = json.load(open(os.path.join(root, f), encoding="utf-8"))
        fills = []
        # ① 填充 TODO
        if key in ans:
            for c in nb["cells"]:
                if c["cell_type"] != "code":
                    continue
                nm = head_name("".join(c["source"]))
                if nm and nm in ans[key]:
                    c["source"] = to_lines(ans[key][nm])
                    fills.append(nm)
        # ② 参考答案附录
        if key in sol_funcs:
            todos = []
            for c in nb["cells"]:
                if c["cell_type"] != "code":
                    continue
                s = "".join(c["source"])
                nm = head_name(s)
                if nm and ("TODO" in s or "NotImplementedError" in s):
                    todos.append(nm)
            rows = "\n".join("| `%s()` | 见下方 `%s()` 内对应逻辑 |" % (t, key)
                             for t in todos) or "| — | 本课无 TODO |"
            app_md = (
                "---\n\n## 教师参考答案（来源：`教师参考/solutions.py` · `%s()`）\n\n"
                "> **发放纪律：本附录勿随学生版下发。**\n\n"
                "上方学生版 TODO 与下方参考实现的对应关系：\n\n"
                "| 学生版函数 | 说明 |\n|---|---|\n%s\n" % (key, rows))
            nb["cells"].append({"cell_type": "markdown", "metadata": {},
                                "source": to_lines(app_md)})
            nb["cells"].append({"cell_type": "code", "metadata": {},
                                "source": to_lines(sol_funcs[key]),
                                "execution_count": None, "outputs": []})
            nb["cells"].append({"cell_type": "markdown", "metadata": {},
                                "source": to_lines(
                                    "## 运行与验证\n\n上方参考实现可直接运行"
                                    "（合成数据、CPU 离线、结果可复现）。\n"
                                    "多解法对比见《多解法手册.md》。")})
        t0 = "".join(nb["cells"][0]["source"])
        nb["cells"][0]["source"] = to_lines(
            t0.replace("学生版", "教师参考版（完成态）").replace("学生实训版", "教师参考版"))
        out = f.replace("_学生版", "_教师版")
        if apply:
            json.dump(nb, open(os.path.join(root, out), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
        print("  %-40s 填充:%s 附录+%s" % (out[:40], fills, key if key in sol_funcs else "无"))
    if not apply:
        print("\n（空跑；加 --apply 生效）")


if __name__ == "__main__":
    main()
