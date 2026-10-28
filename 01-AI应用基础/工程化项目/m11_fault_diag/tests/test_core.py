# -*- coding: utf-8 -*-
"""core 单元测试：真实数据加载、分层划分、手写指标、决策矩阵、兜底降级。"""
import os

import numpy as np
import pytest

from fault_diag import core, io_utils


# ---------------------------------------------------------------- 真实数据
def test_load_real_csv_if_present():
    path = io_utils.course_data("pump_fault.csv")
    if path is None:
        pytest.skip("课程数据目录不可用（兜底路径由 test_fallback 覆盖）")
    X, y, meta = core.load_labeled_csv(path)
    assert X.shape[1] == 5 and X.shape[0] == meta["n_used"] == 450
    assert set(y) <= set(core.CLASSES)
    assert sum(meta["class_counts"].values()) == 450        # 三类均衡 150/150/150


def test_load_missing_column_raises(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("rpm,temp_c,label\n1,2,0\n", encoding="utf-8")
    with pytest.raises(ValueError):
        core.load_labeled_csv(str(p))


def test_load_empty_file_raises(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("", encoding="utf-8")
    with pytest.raises(Exception):
        core.load_labeled_csv(str(p))


# ---------------------------------------------------------------- 划分
def test_stratified_split_keeps_class_ratio():
    rng = np.random.RandomState(0)
    y = np.array(["A"] * 100 + ["B"] * 60 + ["C"] * 40, dtype=object)
    X = rng.normal(size=(200, 3))
    Xtr, Xte, ytr, yte = core.stratified_split(X, y, 0.25, seed=42)
    assert len(Xtr) + len(Xte) == 200
    assert (yte == "A").sum() == 25 and (yte == "B").sum() == 15
    assert (yte == "C").sum() == 10


def test_make_data_shape_and_labels():
    X, y = core.make_data(300, 7)
    assert X.shape == (300, 4)
    assert set(y) == {"正常", "轴承磨损", "叶轮堵塞"}


# ---------------------------------------------------------------- 指标
def test_confusion_diagonal_is_correct():
    cm = core.confusion(["a", "a", "b"], ["a", "b", "b"], ["a", "b"])
    assert cm["a"]["a"] == 1 and cm["a"]["b"] == 1 and cm["b"]["b"] == 1


def test_metrics_match_sklearn_on_known_case():
    """手写指标须与 sklearn 宏平均口径一致（ADR-001 要求的比对验证）。"""
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.metrics import precision_score, recall_score
    y_true = ["正常", "轴承磨损", "叶轮堵塞", "正常", "轴承磨损", "叶轮堵塞",
              "正常", "叶轮堵塞", "正常"]
    y_pred = ["正常", "轴承磨损", "轴承磨损", "正常", "叶轮堵塞",
              "叶轮堵塞", "正常", "叶轮堵塞", "叶轮堵塞"]
    cm = core.confusion(y_true, y_pred, ["正常", "轴承磨损", "叶轮堵塞"])
    mt = core.metrics_from_confusion(cm, ["正常", "轴承磨损", "叶轮堵塞"])
    # 手写实现先按类保留 4 位再取宏平均，允许 5e-4 的舍入差
    tol = 5e-4
    assert abs(mt["acc"] - accuracy_score(y_true, y_pred)) <= tol
    assert abs(mt["macro"]["precision"] - precision_score(
        y_true, y_pred, average="macro", zero_division=0)) <= tol
    assert abs(mt["macro"]["recall"] - recall_score(
        y_true, y_pred, average="macro", zero_division=0)) <= tol
    assert abs(mt["macro"]["f1"] - f1_score(
        y_true, y_pred, average="macro", zero_division=0)) <= tol


def test_evaluate_returns_four_metrics():
    from sklearn.tree import DecisionTreeClassifier
    X, y = core.make_data(120, 3)
    r = core.evaluate(DecisionTreeClassifier(max_depth=3, random_state=0),
                      X[:90], y[:90], X[90:], y[90:], core.CLASSES)
    for k in ("acc", "precision_macro", "recall_macro", "f1_macro", "fit_seconds"):
        assert k in r
    assert 0.0 <= r["acc"] <= 1.0 and set(r["missed"]) == set(core.CLASSES)


# ---------------------------------------------------------------- 决策矩阵 / 档位
def test_score_band_and_matrix():
    rows = [{"model": "M1", "acc": 0.90, "f1_macro": 0.90, "fit_seconds": 0.1},
            {"model": "M2", "acc": 0.95, "f1_macro": 0.95, "fit_seconds": 5.0}]
    bands = {"acc": [(0.95, 5), (0.90, 4)], "fit_seconds": [(0.0, 5), (3.0, 2)]}
    table, winner = core.decision_matrix(rows, {"acc": 3, "speed": 1, "interp": 2},
                                         bands, {"M1": 5, "M2": 2})
    assert core.score_band(0.95, bands["acc"]) == 5
    assert core.score_band(0.10, bands["acc"]) == 0
    assert len(table) == 2 and table[0]["决策"] == "交付"
    assert winner == table[0]["model"]


def test_tier_of_gates():
    g = {"d": 0.75, "c": 0.80, "b": 0.85, "a": 0.85}
    assert core.tier_of(0.76, g) == "D" and core.tier_of(0.81, g) == "C"
    assert core.tier_of(0.90, g) == "A" and core.tier_of(0.50, g) == "未达标"


# ---------------------------------------------------------------- 工单档位断言（M1.1 四档）
def test_workorder_m11_tier_gates():
    """工单 M1.1 验收：D 准确率≥0.75、C≥0.80、B≥0.85（真实数据、分层、固定种子）。"""
    path = io_utils.course_data("pump_fault.csv")
    if path is None:
        pytest.skip("课程数据不可用")
    X, y, _ = core.load_labeled_csv(path)
    Xtr, Xte, ytr, yte = core.stratified_split(X, y, 0.25, seed=7)
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    from sklearn.tree import DecisionTreeClassifier
    accs = []
    for m in (make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000,
                                                                 random_state=7)),
              DecisionTreeClassifier(max_depth=6, random_state=7),
              RandomForestClassifier(n_estimators=300, min_samples_leaf=2,
                                     random_state=7, n_jobs=1)):
        r = core.evaluate(m, Xtr, ytr, Xte, yte, core.CLASSES)
        accs.append(r["acc"])
        assert r["f1_macro"] >= 0.70                        # 宏 F1 底线（答辩可解释）
    assert max(accs) >= 0.85                                # B 档：三模型对比取最优
    assert min(accs) >= 0.75                                # D 档：三者都过硬门槛
