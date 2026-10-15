# -*- coding: utf-8 -*-
"""泵站故障诊断：合成数据、双模型、手写混淆矩阵（纯函数）。"""
import numpy as np


def make_data(n=300, seed=7):
    """三态合成数据：正常/轴承磨损（振动均值抬升）/叶轮堵塞（压力下沉）。"""
    rng = np.random.RandomState(seed)
    X = rng.normal(0, 1, (n, 4))
    y = np.array(["正常"] * n, dtype=object)
    y[n // 3:n // 3 * 2] = "轴承磨损"
    y[n // 3 * 2:] = "叶轮堵塞"
    X[y == "轴承磨损", 0] += 1.5
    X[y == "叶轮堵塞", 1] -= 1.4
    X[y == "叶轮堵塞", 2] += 1.0
    return X, y


def confusion(y_true, y_pred, labels):
    """手写混淆矩阵：行=真实，列=预测。"""
    cm = {a: {b: 0 for b in labels} for a in labels}
    for t, p in zip(y_true, y_pred):
        cm[t][p] += 1
    return cm


def evaluate(model, Xtr, ytr, Xte, yte, labels):
    """训练并评估：acc / macro-F1 / 混淆矩阵 / 漏报统计。"""
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    acc = float((pred == yte).mean())
    cm = confusion(yte, pred, labels)
    miss = {a: sum(cm[a][b] for b in labels if b != a) for a in labels}
    return {"acc": round(acc, 4), "confusion": cm, "missed": miss, "pred": list(pred)}
