# -*- coding: utf-8 -*-
"""macOS 上的已知坑：sklearn 先于 torch 导入会触发 libomp 重复加载段错误。
这里在收集用例前把 torch 预加载，保证全量 pytest 稳定可跑。"""
try:
    import torch  # noqa: F401  （只为导入顺序，功能可用性由 core 探测）
except ImportError:
    pass
