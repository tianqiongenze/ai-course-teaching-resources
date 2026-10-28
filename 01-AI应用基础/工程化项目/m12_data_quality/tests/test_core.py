# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import pytest

from data_quality import core, io_utils


# ---------------------------------------------------------------- 既有：脏数据画像
def test_make_dirty_has_all_three_defects():
    df = core.make_dirty(300, 7)
    d = core.diagnose(df)
    assert d["missing"] > 0 and d["over_limit"] > 0 and d["negative"] > 0


def test_make_dirty_deterministic():
    assert core.make_dirty(50, 3).equals(core.make_dirty(50, 3))


def test_clean_removes_all_defects():
    df = core.make_dirty(300, 7)
    c = core.clean(df)
    d = core.diagnose(c)
    assert d["missing"] == 0 and d["negative"] == 0 and d["out_of_range"] == 0
    assert len(c) < len(df)


def test_quality_between_zero_and_one():
    df = core.make_dirty(300, 7)
    q = core.quality(core.clean(df))
    assert 0.0 <= q <= 1.0


def test_quality_empty_frame_zero():
    assert core.quality(pd.DataFrame({"vib": [], "temp": []})) == 0.0


def test_quality_all_good_is_one():
    df = pd.DataFrame({"vib": [4.0, 5.0], "temp": [50.0, 60.0]})
    assert core.quality(df) == 1.0


# ---------------------------------------------------------------- 数据加载 / 划分
def test_load_real_csv_or_skip():
    path = io_utils.course_data("pump_fault.csv")
    if path is None:
        pytest.skip("课程数据目录不可用")
    X, y, meta = core.load_pump_csv(path)
    assert X.shape == (450, 5) and meta["class_counts"]["正常"] == 150
    assert y.dtype == object and set(y) == set(core.LABEL_NAMES.values())


def test_load_bad_columns_raise(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        core.load_pump_csv(str(p))


def test_load_empty_csv_raises(tmp_path):
    """空文件必须报错而不是返回空数组——否则消融表会拿 0 行去 fit 并把 NaN 写进报告。"""
    p = tmp_path / "empty.csv"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        core.load_pump_csv(str(p))


def test_stratified_split_balanced():
    y = np.array(["A"] * 100 + ["B"] * 100, dtype=object)
    X = np.zeros((200, 2))
    _, _, ytr, yte = core.stratified_split(X, y, 0.25, seed=7)
    assert (yte == "A").sum() == 25 and (yte == "B").sum() == 25


# ---------------------------------------------------------------- 现场视图 / 派生特征
def test_field_view_is_reproducible_and_injects_defects():
    X = np.random.RandomState(0).uniform(1, 5, (200, 5))
    A, metaA = core.field_view(X, seed=7)
    B, metaB = core.field_view(X, seed=7)
    assert np.array_equal(A, B) and metaA == metaB
    assert metaA["hole_cells"] > 0 and (A == 0.0).any()
    assert metaA["n_spike"] > 0


def test_field_view_zero_rate_reaches_config():
    X = np.random.RandomState(0).uniform(1, 5, (400, 5))
    D, meta = core.field_view(X, seed=3, miss_rate=0.15)
    rate = (D == 0.0).mean()
    assert 0.10 < rate < 0.20                          # 与配置量级一致


def test_derive_features_adds_two_columns():
    X = np.random.RandomState(1).uniform(0.5, 5, (30, 5))
    Z, names = core.derive_features(X)
    assert Z.shape == (30, 7) and names[-2:] == core.DERIVED
    assert np.isfinite(Z).all()
    i_vib, i_cur = core.FEATURES.index("vibration_mm_s"), core.FEATURES.index("current_a")
    assert np.allclose(Z[:, 5], X[:, i_vib] / (X[:, i_cur] + 1e-9))


def test_derive_transformer_matches_function():
    X = np.random.RandomState(2).uniform(0.5, 5, (10, 5))
    assert np.allclose(core.DeriveTransformer().transform(X), core.derive_features(X)[0])


def test_violation_report_counts_zero_and_range():
    X = np.array([[1500, 135.0, 0.0, 3.0, 12.0], [1500, 55.0, 0.4, 0.0, 10.0]])
    rep = core.violation_report(X)
    assert rep["temp_c"]["out_of_range"] == 1
    assert rep["pressure_mpa"]["below_zero_or_missing"] == 1
    assert rep["vibration_mm_s"]["below_zero_or_missing"] == 1


# ---------------------------------------------------------------- 流水线装配 / 泄漏防护
def test_pipeline_steps_toggle():
    p0 = core.build_steps(impute=False, derive=False, scaler="none")
    p4 = core.build_steps(impute=True, derive=True, scaler="standard")
    assert [n for n, _ in p0.steps] == ["model"]
    assert [n for n, _ in p4.steps] == ["impute", "derive", "scale", "model"]


def test_imputer_fits_on_train_only_no_leak():
    """填补统计量只能来自训练折：测试列被改脏后，训练折 fit 的中位数不变；
    而把测试行一起 fit 就会被 0 缺失污染——反证"泄漏有害"，不是空断言。"""
    rng = np.random.RandomState(0)
    Xtr = rng.uniform(1, 5, (100, 5))
    ytr = np.array(["A"] * 50 + ["B"] * 50, dtype=object)
    Xte = rng.uniform(1, 5, (20, 5))
    Xte_dirty = Xte.copy()
    Xte_dirty[:10, 0] = 0.0                     # 现场掉线：0 = 传感器离线值

    p_train = core.build_steps(impute=True, derive=False, scaler="none")
    p_train.fit(Xtr, ytr)
    med_train = p_train.named_steps["impute"].statistics_
    ref = np.median(Xtr, axis=0)

    y_all = np.concatenate([ytr, np.array(["A"] * 10 + ["B"] * 10, dtype=object)])
    p_leak = core.build_steps(impute=True, derive=False, scaler="none")
    p_leak.fit(np.vstack([Xtr, Xte_dirty]), y_all)
    med_leaked = p_leak.named_steps["impute"].statistics_

    assert med_train == pytest.approx(ref)                     # 只看训练折
    assert not np.allclose(med_leaked, med_train)              # 混入测试行 → 统计量漂移


def test_grid_search_uses_only_train_rows():
    """GridSearchCV 只收到训练集：折数在训练行内部切分，网格行数=参数点数，测试集从不进 fit。"""
    rng = np.random.RandomState(3)
    X = rng.uniform(1, 5, (120, 5))
    y = (X[:, 0] > 3).astype(int)
    gs = core.grid_search(X, y, {"model__C": [0.1, 1.0]}, folds=5, seed=7)
    assert len(gs.cv_results_["mean_test_score"]) == 2
    assert set(gs.cv_results_["param_model__C"]) == {0.1, 1.0}
    assert gs.n_splits_ == 5
    assert len(gs.classes_) == 2 and gs.score(X, y) > 0.5      # 120 行=训练集本体


# ---------------------------------------------------------------- 评估与稳定性
def test_score_returns_acc_f1_recall():
    rng = np.random.RandomState(4)
    X = rng.uniform(1, 5, (120, 5))
    y = np.array(["A"] * 60 + ["B"] * 60, dtype=object)
    X[:, :2][y == "A"] -= 3.0
    s = core.score(core.build_steps(), X[:90], y[:90], X[90:], y[90:])
    assert 0 <= s["acc"] <= 1 and 0 <= s["f1_macro"] <= 1
    assert set(s["recall"]) == {"A", "B"}


def test_cv_stability_reports_mean_std_folds():
    rng = np.random.RandomState(5)
    X = rng.uniform(1, 5, (100, 5))
    y = np.array(["A"] * 50 + ["B"] * 50, dtype=object)
    X[:, 0][y == "A"] += 3.0
    cv = core.cv_stability(core.build_steps(), X, y, folds=5, seed=7)
    assert len(cv["folds"]) == 5 and 0 <= cv["mean"] <= 1
    assert cv["std"] >= 0


def test_scaler_insensitivity_table_tree_rows_identical():
    """工单"对树模型做归一化无收益"→ 随机森林三档缩放的准确率必须逐档相等。"""
    rng = np.random.RandomState(6)
    X = rng.uniform(1, 5, (150, 5))
    y = np.array(["A"] * 75 + ["B"] * 75, dtype=object)
    X[:, 0][y == "A"] += 2.0
    rows = core.scaler_insensitivity(X[:110], y[:110], X[110:], y[110:], seed=7)
    rf = [r["acc"] for r in rows if "对照" in r["模型"]]
    lr = [r["acc"] for r in rows if "主算法" in r["模型"]]
    assert len(rf) == 3 and len(set(rf)) == 1           # 树模型：缩放不变
    assert len(lr) == 3
    assert {"none", "standard", "minmax"} == {r["缩放方式"] for r in rows}


# ---------------------------------------------------------------- 档位判定（工单 M1.2）
def test_gain_tier_boundaries():
    g = {"d": 5.0, "c": 7.0, "b": 10.0, "f1_b": 0.80, "n_methods_a": 3}
    assert core.gain_tier(4.9, 0.9, 4, "x", g)["tier"] == "未达标"
    assert core.gain_tier(5.0, 0.9, 4, "x", g)["tier"] == "D"
    assert core.gain_tier(7.5, 0.9, 4, "x", g)["tier"] == "C"
    assert core.gain_tier(10.0, 0.79, 4, "x", g)["tier"] == "C"      # F1 未达 0.80 → 不到 B
    assert core.gain_tier(10.0, 0.80, 4, "", g)["tier"] == "B"       # F1 恰达门槛，但无因果解释 → 停在 B
    assert core.gain_tier(10.0, 0.85, 2, "x", g)["tier"] == "B"      # 方法数不足 → 不到 A
    assert core.gain_tier(10.0, 0.85, 3, "因果", g)["tier"] == "A"


def test_workorder_m12_tier_gates_real_data():
    """工单 M1.2：D 提升≥5pp、C≥7pp、B≥10pp 且 macro-F1≥0.80（真实数据 + 现场口径）。"""
    path = io_utils.course_data("pump_fault.csv")
    if path is None:
        pytest.skip("课程数据不可用")
    X, y, _ = core.load_pump_csv(path)
    Xtr, Xte, ytr, yte = core.stratified_split(X, y, 0.25, seed=7)
    Xtr_d, _ = core.field_view(Xtr, seed=7)
    Xte_d, _ = core.field_view(Xte, seed=8)
    mc = {"max_iter": 2000, "seed": 7}
    base = core.score(core.build_steps(impute=False, derive=False, scaler="none",
                                       model_cfg=mc), Xtr_d, ytr, Xte_d, yte)
    gs = core.grid_search(Xtr_d, ytr, {"model__C": [0.01, 0.1, 1.0, 10.0]}, seed=7)
    fin = core.score(gs.best_estimator_, Xtr_d, ytr, Xte_d, yte)
    gain = (fin["acc"] - base["acc"]) * 100
    assert gain >= 10.0                                 # 优秀(B)：提升≥10pp
    assert fin["f1_macro"] >= 0.80                      # 优秀(B)：F1≥0.80
    assert fin["acc"] > base["acc"]
