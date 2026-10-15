# -*- coding: utf-8 -*-
"""四门课 × 每个周次的工程化项目规格（共 40 项）。

每个 spec 生成一个完整工程化项目（23 个文件）：
  多文件结构 + 配置外置 + pytest + 8 份过程文档（GB/T 9385/15532/8567 + TOGAF 四域）。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from specs_01 import SPECS as S01
from specs_02 import SPECS as S02
from specs_03 import SPECS as S03
from specs_05 import SPECS as S05

SPECS = S01 + S02 + S03 + S05


def by_id(pid):
    for s in SPECS:
        if s["id"] == pid:
            return s
    raise KeyError(pid)


if __name__ == "__main__":
    print("共 %d 个工程化项目规格" % len(SPECS))
    for s in SPECS:
        print("  %-8s %-38s %s" % (s["id"], s["course"], s["slug"]))
