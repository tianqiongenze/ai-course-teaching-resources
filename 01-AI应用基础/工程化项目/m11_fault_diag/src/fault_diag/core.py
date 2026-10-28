# -*- coding: utf-8 -*-
"""泵站故障诊断：真实 CSV 加载、NumPy 分层划分、三模型评估、指标与决策矩阵（纯函数）。

工单 M1.1 口径：
  ① 用 NumPy 完成 CSV 加载与训练/测试集划分（test_size=0.25，分层抽样）；
  ② 逻辑回归 / 决策树 / 随机森林 三个分类器都训；
  ③ 四项指标：准确率、精确率、召回率、F1（宏平均）；
  ④ 决策矩阵打分 → 选定交付模型。

工程红线：指标全部手写（见 docs/07 ADR-001），零 IO，可单测。
"""
import time

import numpy as np

LABEL_NAMES = {0: "正常", 1: "轴承磨损", 2: "叶轮堵塞"}
FEATURES = ["rpm", "temp_c", "pressure_mpa", "vibration_mm_s", "current_a"]
CLASSES = ["正常", "轴承磨损", "叶轮堵塞"]


# ---------------------------------------------------------------- 数据加载
def load_labeled_csv(path, features=None, label_names=None):
    """真实 CSV → (X, y, meta)：列名与标签编码全部来自文件，不硬编码数值。

    参数: path 数据文件；features 期望列名列表；label_names 编码→名称映射。
    返回: X float64 (N,F)、y 字符串标签 (N,)、meta {列名, 各类计数, 非法值计数}。
    """
    from . import io_utils

    features = list(features or FEATURES)
    label_names = dict(label_names or LABEL_NAMES)
    rows = io_utils.read_csv_rows(path)
    if not rows:
        raise ValueError("数据文件为空（0 条记录）: %s" % path)
    missing = [c for c in features + ["label"] if c not in rows[0]]
    if missing:
        raise ValueError("数据文件缺少列 %s，实际列=%s" % (missing, list(rows[0])))
    X, y, bad = [], [], 0
    for r in rows:
        try:
            vals = [float(r[c]) for c in features]
            code = int(float(r["label"]))          # 标签非数值同样算脏行，不崩流水线
        except (TypeError, ValueError):
            bad += 1
            continue
        if code not in label_names:
            bad += 1
            continue
        X.append(vals)
        y.append(label_names[code])
    counts = {}
    for name in label_names.values():
        counts[name] = int(sum(1 for v in y if v == name))
    return np.asarray(X, dtype=float), np.asarray(y, dtype=object), {
        "n_rows": len(rows), "n_used": len(y), "n_dropped": bad,
        "features": features, "class_counts": counts}


def make_data(n=300, seed=7):
    """【兜底】三态合成数据：仅在真实 CSV 缺失时使用（环境/数据也是选型维度）。"""
    rng = np.random.RandomState(seed)
    X = rng.normal(0, 1, (n, 4))
    y = np.array(["正常"] * n, dtype=object)
    y[n // 3:n // 3 * 2] = "轴承磨损"
    y[n // 3 * 2:] = "叶轮堵塞"
    X[y == "轴承磨损", 0] += 1.5
    X[y == "叶轮堵塞", 1] -= 1.4
    X[y == "叶轮堵塞", 2] += 1.0
    return X, y


# ---------------------------------------------------------------- NumPy 分层划分
def stratified_split(X, y, test_size=0.25, seed=42):
    """纯 NumPy 分层抽样划分：每类按 test_size 独立取整数样本进测试集。

    对应工单常见错误①：不分层 → 测试集类别失衡、指标抖动。
    保底：某类样本过少导致 test 取 0 个时，至少放 1 个进测试集。
    """
    rng = np.random.RandomState(seed)
    te_idx, tr_idx = [], []
    for cls in np.unique(y):
        idx = np.where(y == cls)[0]
        rng.shuffle(idx)
        k = int(round(len(idx) * test_size))
        k = max(1, min(k, len(idx) - 1)) if len(idx) >= 2 else 0
        te_idx += list(idx[:k])
        tr_idx += list(idx[k:])
    te_idx = np.array(sorted(te_idx), dtype=int)
    tr_idx = np.array(sorted(tr_idx), dtype=int)
    return X[tr_idx], X[te_idx], y[tr_idx], y[te_idx]


def split_balance_report(y_tr, y_te, labels):
    """划分后各类计数（可复现证据：训练/测试类别分布）。"""
    return {c: {"train": int((y_tr == c).sum()), "test": int((y_te == c).sum())}
            for c in labels}


# ---------------------------------------------------------------- 指标（手写）
def confusion(y_true, y_pred, labels):
    """手写混淆矩阵：行=真实，列=预测。"""
    cm = {a: {b: 0 for b in labels} for a in labels}
    for t, p in zip(y_true, y_pred):
        cm[t][p] += 1
    return cm


def metrics_from_confusion(cm, labels):
    """由混淆矩阵推四项指标：acc / 各类 P-R-F1 / 宏平均（脚注②：每类权重相同）。

    精确率 P=TP/(TP+FP)（报出来的里面多少是真的）；
    召回率 R=TP/(TP+FN)（真的故障里报出来多少，漏报即 1-R）；
    F1=2PR/(P+R)；宏平均=各类 F1 的算术平均（小类不缺席）。
    """
    acc_num = sum(cm[c][c] for c in labels)
    total = sum(sum(cm[a][b] for b in labels) for a in labels)
    per = {}
    for c in labels:
        tp = cm[c][c]
        fp = sum(cm[o][c] for o in labels) - tp
        fn = sum(cm[c][o] for o in labels) - tp
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        per[c] = {"precision": round(prec, 4), "recall": round(rec, 4),
                  "f1": round(f1, 4), "support": int(tp + fn)}
    macro = {"precision": round(sum(v["precision"] for v in per.values()) / len(labels), 4),
             "recall": round(sum(v["recall"] for v in per.values()) / len(labels), 4),
             "f1": round(sum(v["f1"] for v in per.values()) / len(labels), 4)}
    return {"acc": round(acc_num / total, 4) if total else 0.0,
            "per_class": per, "macro": macro}


def evaluate(model, Xtr, ytr, Xte, yte, labels):
    """训练并评估：计时 + acc/精确率/召回率/F1（宏）+ 混淆矩阵 + 漏报统计。"""
    t0 = time.perf_counter()
    model.fit(Xtr, ytr)
    fit_s = time.perf_counter() - t0
    t1 = time.perf_counter()
    pred = model.predict(Xte)
    pred_s = time.perf_counter() - t1
    cm = confusion(list(yte), list(pred), labels)
    mt = metrics_from_confusion(cm, labels)
    miss = {a: sum(cm[a][b] for b in labels if b != a) for a in labels}
    return {"acc": mt["acc"], "precision_macro": mt["macro"]["precision"],
            "recall_macro": mt["macro"]["recall"], "f1_macro": mt["macro"]["f1"],
            "per_class": mt["per_class"], "confusion": cm, "missed": miss,
            "fit_seconds": round(fit_s, 4), "predict_seconds": round(pred_s, 4),
            "pred": list(pred)}


# ---------------------------------------------------------------- 决策矩阵
def score_band(value, bands):
    """把实测数值按 (阈值, 分值) 降序档位映射为 0-5 分（档位写在 rules.yaml）。"""
    for lo, pts in bands:
        if value >= lo:
            return pts
    return 0


def decision_matrix(rows, weights, bands, interp_scores):
    """构建真实决策矩阵表：精度=实测 acc 换算、速度=实测耗时换算、可解释性=登记档位。

    rows: [{model, acc, fit_seconds, ...}]；weights: {"acc":w1,"speed":w2,"interp":w3}；
    bands: 分档表；interp_scores: 模型→可解释性登记分（0-5，答辩需能口述理由）。
    返回: (表格行 list[dict], 选定模型名)
    """
    table = []
    for r in rows:
        acc_pts = score_band(r["acc"], bands["acc"])
        fit_pts = score_band(r["fit_seconds"], bands["fit_seconds"])
        interp_pts = int(interp_scores.get(r["model"], 0))
        total = (acc_pts * float(weights["acc"]) + fit_pts * float(weights["speed"])
                 + interp_pts * float(weights["interp"]))
        table.append({"model": r["model"], "acc": r["acc"],
                      "f1_macro": r.get("f1_macro"),
                      "fit_seconds": r["fit_seconds"],
                      "精度预期": acc_pts, "训练速度": fit_pts,
                      "可解释性": interp_pts, "综合": round(total, 2)})
    table.sort(key=lambda d: -d["综合"])
    for i, row in enumerate(table):
        row["决策"] = "交付" if i == 0 else "备选" if i == 1 else "不交付"
    return table, table[0]["model"]


def tier_of(acc, gates):
    """按工单四档给出达标等级（D/C/B/A 门槛来自 rules.yaml，非硬编码）。"""
    if acc >= gates.get("a", 9):
        return "A"
    if acc >= gates.get("b", 9):
        return "B"
    if acc >= gates.get("c", 9):
        return "C"
    if acc >= gates.get("d", 9):
        return "D"
    return "未达标"
