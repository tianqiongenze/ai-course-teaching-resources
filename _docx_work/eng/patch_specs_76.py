# -*- coding: utf-8 -*-
"""76号轮·specs 剩余缺陷修复（7 处 + E128 2 处）"""
import ast
import os

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)


def patch(fn, old, new, label):
    s = open(fn, encoding="utf-8").read()
    if old not in s:
        print("  [MISS]", fn, label)
        return False
    s = s.replace(old, new, 1)
    ast.parse(s)
    open(fn, "w", encoding="utf-8", newline="\n").write(s)
    print("  [OK]", fn, label)
    return True


# ① w04 测试：分号拆行（E702）
patch("specs_02.py",
      "    d.start(); d.stop()",
      "    d.start()" + chr(10) + "    d.stop()",
      "w04 分号拆行")

# ② w04 测试：未用变量 d（F841）
patch("specs_02.py",
      '    d = core.Device("DEV-1", "x", temp=96.0)' + chr(10)
      + '    assert "DANGER" in core.Device("DEV-2", "x", temp=96.0).patrol(80, 95)',
      '    assert "DANGER" in core.Device("DEV-2", "x", temp=96.0).patrol(80, 95)',
      "w04 去未用 d")

# ③ p41 嵌套 def 前空行（E306）
patch("specs_03.py",
      "    # transport：无 pymodbus 用确定性本地模拟（课堂可跑）" + chr(10)
      + "    def transport(src):",
      "    # transport：无 pymodbus 用确定性本地模拟（课堂可跑）" + chr(10) + chr(10)
      + "    def transport(src):",
      "p41 嵌套 def 空行")

# ④ m11a 测试：未用 numpy（F401）
patch("specs_05.py",
      "def test_make_dirty_has_all_defects():" + chr(10)
      + "    import numpy as np" + chr(10)
      + "    df = core.make_dirty(300, 7)",
      "def test_make_dirty_has_all_defects():" + chr(10)
      + "    df = core.make_dirty(300, 7)",
      "m11a 去未用 numpy")

# ⑤ p33 测试：歧义变量名 l（E741）
patch("specs_03.py",
      "assert len({core.w(l) for l in out}) == 1",
      "assert len({core.w(ln) for ln in out}) == 1",
      "p33 l→ln")

# ⑥ m31_transfer：lambda 赋值（E731）
patch("specs_05.py",
      "    label = lambda X: (X[:, 0] > 0).astype(int)" + chr(10)
      + "    return big, small, test, label(small), label(test)",
      "    def label(X):" + chr(10)
      + "        return (X[:, 0] > 0).astype(int)" + chr(10) + chr(10)
      + "    return big, small, test, label(small), label(test)",
      "m31_transfer lambda→def")

# ⑦ m51：未用变量 alarm（F841）
patch("specs_05.py",
      "        alarm = [i for i in range(N) if degrade[i] >= THRESH]" + chr(10),
      "",
      "m51 去未用 alarm")

print("完成")
