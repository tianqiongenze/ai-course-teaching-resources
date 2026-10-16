# -*- coding: utf-8 -*-
"""82轮·01/02/03 教师版重建（附录方案）

背景：这三包的 教师参考/solutions.py 是**内联实现**（与学生 starter 不同构），
      无法像 05 那样自动按同名函数填充 TODO。
方案：教师版 = 学生版骨架（逐 cell 原样，保持结构对应）
      + 附录【教师参考答案】：solutions 对应工单函数的完整实现
      + 附录【TODO ↔ 参考实现 对照表】
用法: python build_appendix.py <包目录> <工单映射> [--apply]
"""
import ast
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def full_funcs(sol_path):
    """返回 {函数名: 完整源码}"""
    src = open(sol_path, encoding="utf-8").read()
    tree = ast.parse(src)
    out = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            seg = ast.get_source_segment(src, node)
            if seg:
                out[node.name] = seg
    return out


def to_lines(t):
    ls = t.rstrip("\n").split("\n")
    o = [l + "\n" for l in ls]
    if o:
        o[-1] = o[-1].rstrip("\n")
    return o


def md(t):
    return {"cell_type": "markdown", "metadata": {}, "source": to_lines(t)}


def code(t):
    return {"cell_type": "code", "metadata": {}, "source": to_lines(t),
            "execution_count": None, "outputs": []}


# 各包：学生版文件名前缀 → solutions 函数名
MAP_01 = {"m11": "m11", "m12": "m12", "m21": "m21", "m22": "m22",
          "m31": "m31", "m32": "m32", "m41": "m41", "m42": "m42"}
MAP_02 = {"w01": "w01", "w02": "w02", "w03": "w03", "w04": "w04", "w05": "w05",
          "w06": "w06", "w07": "w07", "w08": "w08", "w09": "w09", "w10": "w10",
          "w11": "w11", "w12": "w12"}
MAP_03 = {"p11": "p11", "p12": "p12", "p21": "p21", "p22": "p22",
          "p33": "p33", "p41": "p41", "p55": "p55", "p66": "p66"}


def main():
    pkg = sys.argv[1]
    apply = "--apply" in sys.argv
    root = os.path.join(pkg, "Jupyter实训")
    sol = full_funcs(os.path.join(pkg, "教师参考", "solutions.py"))
    if "01" in pkg:
        mp = MAP_01
    elif "02" in pkg:
        mp = MAP_02
    else:
        mp = MAP_03
    files = sorted(f for f in os.listdir(root)
                   if f.endswith("_学生版.ipynb") and "executed" not in f)
    for f in files:
        key = f.split("_")[0].lower()
        wk = mp.get(key)
        if not wk or wk not in sol:
            print("  [SKIP] %s (key=%s → %s)" % (f[:38], key, wk))
            continue
        snb = json.load(open(os.path.join(root, f), encoding="utf-8"))
        # TODO 清单
        todos = []
        for c in snb["cells"]:
            if c["cell_type"] != "code":
                continue
            s = "".join(c["source"])
            fn = re.match(r"\s*def\s+(\w+)", s)
            if fn and ("TODO" in s or "NotImplementedError" in s):
                todos.append(fn.group(1))
        # 追加附录
        snb["cells"].append(md(
            "---\n\n## 教师参考答案（来源：`教师参考/solutions.py` · `%s()`）\n\n"
            "> **发放纪律：本附录勿随学生版下发。** 课堂按层放提示（D层演示照做/C层只给思路行/A层直接做）。\n\n"
            "学生版 TODO 位置 → 下方参考实现的对应关系：\n\n"
            "| 学生版 TODO 函数 | 参考实现说明 |\n|---|---|\n%s\n"
            % (wk, "\n".join("| `%s()` | 见下方 `%s()` 内对应逻辑 |" % (t, wk) for t in todos))))
        snb["cells"].append(code(sol[wk]))
        snb["cells"].append(md(
            "## 运行与验证\n\n"
            "上方参考实现可**直接运行**（合成数据、CPU 离线、结果可复现）。\n"
            "教师可对照学生版逐 cell 讲解：学生填 TODO → 此处给出完成态。\n\n"
            "> 多解法对比见同目录《多解法手册.md》与 `教师参考/solutions_multi*.py`。"))
        t0 = "".join(snb["cells"][0]["source"])
        snb["cells"][0]["source"] = to_lines(t0.replace("学生版", "教师参考版（含参考答案附录）")
                                             .replace("学生实训版", "教师参考版"))
        out = f.replace("_学生版", "_教师版")
        if apply:
            json.dump(snb, open(os.path.join(root, out), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
        print("  %-40s → %-5s TODO:%d 附录+%s" % (out[:40], wk, len(todos), wk))
    if not apply:
        print("\n（空跑；加 --apply 生效）")


if __name__ == "__main__":
    main()
