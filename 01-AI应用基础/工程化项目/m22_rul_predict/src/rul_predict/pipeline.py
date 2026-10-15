# -*- coding: utf-8 -*-
"""合成退化轨迹 → 回归 → 指标 → 业务解读。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    import numpy as np
    x, rul, m = core.make_traj(int(cfg.raw.get("n_cycles", 3000)), seed=cfg.seed)
    idx = np.where(m)[0]
    X = x[idx, None]
    y = rul[idx]
    model, pred, metrics = core.fit(X, y)
    note = core.business_note(metrics["rmse"])
    result = {"n_points": int(len(X)), "metrics": metrics, "note": note,
              "sample": [{"x": round(float(a), 3), "rul": round(float(b), 4),
                          "pred": round(float(p), 4)}
                         for a, b, p in list(zip(X.ravel(), y, pred))[:5]]}
    sections = [("输入口径", ["全寿命轨迹 %d 点｜退化段 %d 点｜特征: 振动RMS｜目标: 剩余寿命(归一化)"
                % (len(x), len(X))]),
                ("回归指标", ["R² = %.4f　RMSE = %.5f　MAE = %.5f"
                 % (metrics["r2"], metrics["rmse"], metrics["mae"])]),
                ("样本对比", ["x=%.3f 真值=%.4f 预测=%.4f"
                          % (d["x"], d["rul"], d["pred"]) for d in result["sample"]]),
                ("业务解读", [note]),
                ("结论与建议", ["RUL 预测的价值不在分数，而在'误差→维护周期'的翻译；"
                 "预测误差在可接受区间内即可提前排程"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections
