# -*- coding: utf-8 -*-
"""76号轮·修正 m51 误插入 + m31_transfer 空行（E306）"""
import ast
import os

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

s = open("specs_05.py", encoding="utf-8").read()
n = 0

# ① m51：误插入的 rng 赋值（policy_random 已有 rng 形参）
old1 = ("def policy_random(state, rng):" + chr(10)
        + "    rng = np.random.RandomState(seed)" + chr(10)
        + "    return rng.randint(0, N)")
new1 = ("def policy_random(state, rng):" + chr(10)
        + "    return rng.randint(0, N)")
if old1 in s:
    s = s.replace(old1, new1, 1)
    n += 1
    print("  [OK] m51 移除误插入")

# ② m31_transfer：嵌套 def 前补空行
old2 = ("    test = np.vstack([c + rng.normal(0, 1, (25, n_dim)) for c in centers])" + chr(10)
        + "    def label(X):")
new2 = ("    test = np.vstack([c + rng.normal(0, 1, (25, n_dim)) for c in centers])" + chr(10) + chr(10)
        + "    def label(X):")
if old2 in s:
    s = s.replace(old2, new2, 1)
    n += 1
    print("  [OK] m31_transfer 补空行")

if n:
    ast.parse(s)
    open("specs_05.py", "w", encoding="utf-8", newline="\n").write(s)
print("完成，共 %d 处" % n)
