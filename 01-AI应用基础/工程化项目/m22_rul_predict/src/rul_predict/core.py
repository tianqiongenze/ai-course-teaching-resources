# -*- coding: utf-8 -*-
"""轴承退化轨迹、RUL 回归与业务解读（纯函数）。"""
import numpy as np


def make_traj(n=3000, seed=7):
    """合成全寿命退化轨迹：平稳期 + 线性退化段；返回 (x, rul)。"""
    t = np.linspace(0, 1, n)
    onset = 0.7
    deg = np.zeros(n)
    m = t > onset
    deg[m] = (t[m] - onset) / (1.0 - onset)
    rng = np.random.RandomState(seed)
    x = 4.0 * (1 + 0.02 * np.sin(2 * np.pi * 30 * t)) + 2.0 * deg + rng.randn(n) * 0.05
    rul = np.where(m, (1.0 - t) / 0.3, np.nan)
    return x, rul, m


def fit(X, y, model=None):
    """训练回归并返回 (model, pred, r2)。"""
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    if model is None:
        from sklearn.linear_model import Ridge
        model = Ridge(alpha=1.0)
    model.fit(X, y)
    pred = model.predict(X)
    r2 = float(r2_score(y, pred))
    rmse = float(np.sqrt(mean_squared_error(y, pred)))
    mae = float(mean_absolute_error(y, pred))
    return model, pred, {"r2": round(r2, 4), "rmse": round(rmse, 5), "mae": round(mae, 5)}


def business_note(rmse, rul_span=1.0):
    """把 RMSE 归一化到退化区间长度，翻译成维护建议。"""
    ratio = rmse / max(rul_span, 1e-9)
    cycles = int(round(ratio * 20))
    return ("预测误差约占退化区间 %.1f%% → 约 %d 个维护周期；"
            "可提前 1-2 个周期安排换件。" % (ratio * 100, cycles))
