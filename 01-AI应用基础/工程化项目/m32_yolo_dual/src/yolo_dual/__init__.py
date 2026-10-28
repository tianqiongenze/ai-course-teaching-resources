# -*- coding: utf-8 -*-
"""YOLO实时缺陷检测（双路线对照） —— 工程化实现包。

分层：config（配置）/ core（纯逻辑）/ io_utils（IO）/ report（报告）/ pipeline（编排）
      / tiers（工单四档实测判定）/ stylecheck（PEP 8 规范率实测）
      / cli（控制台入口，与 run.py 同源）。
"""
__version__ = "1.0.0"
__all__ = ["cli", "config", "core", "io_utils", "pipeline", "report",
           "stylecheck", "tiers"]
