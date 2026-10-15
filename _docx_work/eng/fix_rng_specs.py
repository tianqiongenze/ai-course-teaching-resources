# -*- coding: utf-8 -*-
"""76号轮·修正 rng 误删（F821 回归）

规则：对每个 spec 的 core_py 片段，若出现 `rng.` 但缺少
`rng = np.random.RandomState(seed)`，则在**首个使用 rng 的函数**的
docstring 之后（或函数体首行）插入赋值语句。
"""
import ast
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

ASSIGN = "    rng = np.random.RandomState(seed)"
PAT = re.compile(r"core_py='''(.*?)'''", re.S)


def fix_spec(fn):
    s = open(fn, encoding="utf-8").read()
    changed = 0

    def repl(m):
        nonlocal changed
        body = m.group(1)
        if "rng." not in body:
            return m.group(0)
        if "rng = np.random.RandomState(seed)" in body:
            return m.group(0)
        # 找首个含 rng. 的 def 段，在 docstring 后插入赋值
        lines = body.split("\n")
        idx = next((i for i, l in enumerate(lines) if "rng." in l), None)
        if idx is None:
            return m.group(0)
        # 向上找最近的 def 行
        d = idx
        while d >= 0 and not lines[d].lstrip().startswith("def "):
            d -= 1
        if d < 0:
            return m.group(0)
        # 跳过 def 行；若下一行是 docstring（含 """），跳过其结束
        ins = d + 1
        if ins < len(lines) and lines[ins].strip().startswith(('"""', "'''")):
            quote = lines[ins].strip()[:3]
            if lines[ins].strip().count(quote) >= 2 and len(lines[ins].strip()) > 3:
                ins += 1
            else:
                ins += 1
                while ins < len(lines) and quote not in lines[ins]:
                    ins += 1
                ins += 1
        lines.insert(ins, ASSIGN)
        changed += 1
        return "core_py='''" + "\n".join(lines) + "'''"

    out = PAT.sub(repl, s)
    if changed:
        ast.parse(out)
        open(fn, "w", encoding="utf-8", newline="\n").write(out)
    print("%s: 补回 rng 赋值 %d 处" % (fn, changed))


for fn in ("specs_01.py", "specs_02.py", "specs_03.py", "specs_05.py"):
    fix_spec(fn)
print("完成")
