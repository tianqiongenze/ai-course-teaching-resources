# -*- coding: utf-8 -*-
"""pytest 会话前置：先加载 torch，规避 macOS 上 sklearn(OpenMP) 与 torch 的 libomp 冲突。

为什么：本机实测"先 import sklearn 再 import torch"会在共存时 segfault；
先加载 torch 即可稳定并存。这是环境适配（"环境也是选型维度"），不改任何
断言逻辑；无 torch 的机器上本文件静默跳过，测试走兜底路径照常收集。
"""
try:
    import torch  # noqa: F401  （仅为预加载，非业务依赖声明）
except ImportError:
    pass
